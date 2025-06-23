# converter_tools/gui_main_window.py

import sys
import os
import traceback
import time
import json
import multiprocessing
import threading
import concurrent.futures
# import html # No longer needed here, moved to utils.py
from multiprocessing import Manager

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QComboBox, QLabel, QTextEdit, QSizePolicy, QSpacerItem, QMenuBar,
        QFileDialog, QMessageBox, QStatusBar, QDialog, QDialogButtonBox,
        QLineEdit, QSpinBox, QGroupBox, QMenu, QProgressBar, QGridLayout
    )
    from PySide6.QtGui import (QAction, QKeySequence, QColor, QPalette,
                               QCloseEvent, QIcon, QDropEvent, QTextCharFormat)
    from PySide6.QtCore import Qt, Slot, Signal, QPoint, QMimeData, QEvent, QTimer
    from PySide6.QtUiTools import QUiLoader
except ImportError as e:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app_exists = QApplication.instance()
        if not app_exists:
            temp_app = QApplication([])
        QMessageBox.critical(
            None, "Fatal Error", f"PySide6 is not installed or found for gui_main_window.py: {e}")
    except Exception:
        print(f"FATAL ERROR (gui_main_window.py): PySide6 not found, and QMessageBox fallback failed. {e}")
    sys.exit(1)

# Core application modules
from src.converter_tools import config
from src.converter_tools.config import save_app_settings
from src.converter_tools import utils
from src.converter_tools import conversions
from src.converter_tools import menu_definitions

# GUI components from other files in this package
from src.converter_tools.gui_settings import SettingsDialog
from src.converter_tools.gui_m3u_creator import M3UCreatorWindow


# Number of distinct stages reported by utils.process_file for progress tracking.
N_STAGES_PER_FILE = 3

# Constants
COL_CHECK = 0
COL_PATH = 1
COL_TYPE = 2
TABLE_HEADINGS = ['✓', 'File Path', 'Type']

APP_NAME = "Retro Converter Tool"
APP_VERSION = "1.1.0"
APP_COPYRIGHT = "(c) 2023-2024 ozGarius"
GITHUB_URL = "https://github.com/ozGarius/retro_converter_tool"

# UI file paths
MAIN_UI_PATH = os.path.join(os.path.dirname(__file__), "assets", "qt", "main_window.ui")
ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "icons", "app_icon.ico")

# Thread timeouts
THREAD_STOP_TIMEOUT = 3000  # milliseconds
QUIT_THREAD_TIMEOUT = 2000  # milliseconds


# --- Worker Process Task ---
# This function will be run by each process in the ProcessPoolExecutor
def process_worker_task(job_queue, results_queue):
    # Minimal re-initialization of config for the process if needed
    # For now, assume settings are passed per job or are simple enough not to need full re-init
    # config.initialize_config_for_process() # Hypothetical function

    while True:
        try:
            job_payload = job_queue.get()
            if job_payload is None:  # Sentinel value to stop the worker
                break

            job_id = job_payload["job_id"]
            original_file_path = job_payload["file_path"] # Renamed for clarity
            conversion_func_name = job_payload["conversion_func_name"]
            output_folder_path_final_dest = job_payload["output_folder_path"] # Renamed for clarity
            overwrite_files = job_payload["overwrite_files"]
            selected_primary_output_ext = job_payload["selected_primary_output_ext"]
            selected_secondary_output_ext = job_payload["selected_secondary_output_ext"]
            is_multi_file_job_type = job_payload.get("is_multi_file_job_type", False)

            job_temp_dir = None # Initialize

            try:
                # Restore settings in the worker process's global config.settings object
                shared_settings_dict = job_payload.get("config_settings_dict", {})
                config.settings.restore_from_shared(shared_settings_dict)
            except Exception as e:
                results_queue.put({"job_id": job_id, "type": "error_update", "data": {"message": f"Worker process failed to eval settings: {e}"}})
                results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": False, "message": "Settings failure"}})
                continue

            current_file_name = os.path.basename(original_file_path)
            results_queue.put({"job_id": job_id, "type": "job_started", "data": {"filename": current_file_name, "total_stages": N_STAGES_PER_FILE}})

            # --- Signal Wrappers for results_queue ---
            def send_output_update_worker(message): # Renamed to avoid conflict if this file also has send_output_update
                results_queue.put({"job_id": job_id, "type": "output_update", "data": {"message": message}})

            def send_error_update_worker(message, is_error=True):
                results_queue.put({"job_id": job_id, "type": "error_update", "data": {"message": message}})

            # Create job-specific temp directory
            # utils.create_temp_dir needs the base name of the input file for its prefix logic.
            job_temp_dir = utils.create_temp_dir(original_file_path, output_signal=send_output_update_worker, error_signal=send_error_update_worker)
            if not job_temp_dir:
                send_error_update_worker(f"Failed to create temp directory for job {job_id}.")
                results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": False, "message": "Temp dir creation failed"}})
                continue

            # Stage files into the job_temp_dir
            path_to_process_in_temp = utils.stage_job_files(
                original_file_path,
                job_temp_dir,
                is_multi_file_job_type,
                config.settings.COPY_LOCALLY, # Use restored setting
                output_signal=send_output_update_worker,
                error_signal=send_error_update_worker
            )

            if not path_to_process_in_temp:
                send_error_update_worker(f"Failed to stage files for job {job_id} ({current_file_name}).")
                results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": False, "message": "File staging failed"}})
                if job_temp_dir: utils.cleanup(job_temp_dir, output_signal=send_output_update_worker, error_signal=send_error_update_worker)
                continue

            cumulative_stages_done_for_file = 0
            def stage_reporter_for_process_file(stage_description):
                nonlocal cumulative_stages_done_for_file
                cumulative_stages_done_for_file +=1
                results_queue.put({
                    "job_id": job_id, "type": "status_update", # This was overall progress, now it's per-job stage
                    "data": {
                        "description": stage_description,
                        "current_step": cumulative_stages_done_for_file,
                        "total_steps": N_STAGES_PER_FILE
                    }
                })
                # Simple percentage for individual file progress bar
                file_percentage = int((cumulative_stages_done_for_file / N_STAGES_PER_FILE) * 100)
                results_queue.put({
                    "job_id": job_id, "type": "file_progress_update",
                    "data": {"percentage": file_percentage}
                })


            # --- Get the actual conversion function ---
            conv_func = getattr(conversions, conversion_func_name, None) if conversion_func_name else None
            if not callable(conv_func):
                error_msg = f"Conversion function '{conversion_func_name}' not found in worker."
                send_error_update(error_msg)
                results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": False, "message": error_msg}})
                continue

            # --- Call utils.process_file ---
            # Note: utils.process_file and its dependencies (like utils.run_command)
            # must be safe to run in a separate process. They should not rely on GUI elements
            # or shared state that isn't process-safe.
            # The `output_signal` and `error_signal` are now wrappers.

            # Critical: File dependency handling needs to be done here or within process_file
            # For now, assuming process_file or the conversion routines handle it based on the main file_path

            success = utils.process_file(
                staged_primary_file_path=path_to_process_in_temp, # Path to the file that should be processed by the tool
                job_temp_dir=job_temp_dir, # The temp dir where the tool writes output
                original_file_path_for_naming_and_delete=original_file_path, # Used for output naming and optional deletion
                conversion_func=conv_func,
                format_out=selected_primary_output_ext, # Primary output extension expected
                format_out2=selected_secondary_output_ext, # Secondary output extension, if any
                output_signal=send_output_update_worker,
                error_signal=send_error_update_worker,
                explicit_output_dir=output_folder_path_final_dest, # Final destination for processed files
                allow_overwrite=overwrite_files,
                target_format_from_worker=selected_primary_output_ext, # Hint for some conversion functions
                stage_reporter=stage_reporter_for_process_file
            )

            # Ensure final progress update if not already sent by stage_reporter
            if cumulative_stages_done_for_file < N_STAGES_PER_FILE: # Should typically be N_STAGES_PER_FILE - 1 before this
                 final_stage_desc = "Completed" if success else "Failed"
                 # This will push it to N_STAGES_PER_FILE
                 stage_reporter_for_process_file(final_stage_desc)

            results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": success}})

            # Handle deletion of original file if successful and configured
            if success and config.settings.DELETE_SOURCE_ON_SUCCESS:
                send_output_update_worker(f"Job successful, deleting source: {original_file_path}")
                # utils.cleanup takes care of original file deletion if path is provided
                # However, the main job_temp_dir cleanup is done by process_file.
                # We need a separate call for the original source files.
                # Let's make a small helper or call send2trash directly.
                try:
                    # For CUE/GDI, delete dependencies as well
                    files_to_delete_source = [original_file_path]
                    if is_multi_file_job_type:
                        if original_file_path.lower().endswith('.cue'):
                            files_to_delete_source.extend(utils._get_cue_dependencies(original_file_path))
                        elif original_file_path.lower().endswith('.gdi'):
                            files_to_delete_source.extend(utils._get_gdi_dependencies(original_file_path))

                    for f_path_to_del in set(files_to_delete_source): # Use set to avoid duplicates
                        if os.path.exists(f_path_to_del):
                            if send2trash:
                                send2trash.send2trash(f_path_to_del)
                                send_output_update_worker(f"Sent to trash: {f_path_to_del}")
                            else:
                                os.remove(f_path_to_del) # Fallback to permanent delete
                                send_output_update_worker(f"Permanently deleted: {f_path_to_del} (send2trash not available)")
                except Exception as del_e:
                    send_error_update_worker(f"Error deleting source file {original_file_path} or its dependencies: {del_e}")

        except Exception as e:
            tb_str = traceback.format_exc()
            # Try to inform the main thread about the error
            try:
                job_id_error = job_payload.get("job_id", "unknown") if 'job_payload' in locals() else "unknown"
                results_queue.put({
                    "job_id": job_id_error, "type": "error_update",
                    "data": {"message": f"Unhandled error in worker process: {e}\n{tb_str}"}
                })
                results_queue.put({"job_id": job_id_error, "type": "job_completed", "data": {"success": False, "message": str(e)}})
            except Exception as queue_e:
                # If we can't even put to queue, print to stderr (might be visible in console)
                print(f"WORKER ERROR (job: {job_id_error if 'job_id_error' in locals() else 'unknown'}): {e}\n{tb_str}", file=sys.stderr)
                print(f"WORKER ERROR: Could not put error to results_queue: {queue_e}", file=sys.stderr)
            if job_payload is None: # If error happened while getting None (sentinel)
                break # Exit loop
            # Continue to next job if possible, or break if error is too severe (e.g. sentinel processing)
            continue # Try to process next job
    # Worker process is finishing
    print(f"Worker process {os.getpid()} exiting.")


# Hardcoded content (avoiding README parsing)
TOOLS_USED_TEXT = (
    "- Python 3.x<br>"
    "- PySide6 (for the GUI)<br>"
    "- send2trash (for safe deletion)<br>"
    "- 7-Zip (as 7za.exe, for archive handling)<br>"
    "- DolphinTool.exe (for Nintendo Wii/GC formats)<br>"
    "- chdman.exe (for MAME CHDs)<br>"
    "- maxcso.exe (for CSO compression)"
)

LICENSES_TEXT = (
    "- PySide6: LGPL v3<br>"
    "- send2trash: BSD License<br>"
    "- 7-Zip (7za.exe): GNU LGPL + unRAR restriction<br>"
    "- DolphinTool.exe: GPLv2+<br>"
    "- chdman.exe: GPL-2.0+ (MAME specifics)<br>"
    "- maxcso.exe: MIT License"
)


class ConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize application
        self._setup_application()
        
        # Load UI
        self._load_main_ui()
        
        # Find and validate UI elements
        self._find_ui_elements()
        
        # Setup drag and drop
        self._setup_drag_drop()
        
        # Initialize UI states
        self._initialize_ui_states()
        
        # Connect signals
        self._connect_signals()
        
        # Initialize member variables
        self._initialize_variables()
        
        # Final setup
        self._finalize_initialization()

    def _setup_application(self):
        """Initialize QApplication and set up basic application properties."""
        app_instance = QApplication.instance()
        if not app_instance:
            print("Warning: QApplication instance not found during ConverterWindow init. Creating one.")
            app_instance = QApplication(sys.argv)

        if app_instance:
            app_instance.setQuitOnLastWindowClosed(True)
            app_instance.aboutToQuit.connect(self._on_about_to_quit)

    def _load_main_ui(self):
        """Load the main UI file."""
        if not os.path.exists(MAIN_UI_PATH):
            self._show_fatal_error(f"Main UI file not found: {MAIN_UI_PATH}")
            return

        loader = QUiLoader()
        self.ui = loader.load(MAIN_UI_PATH, self)
        if not self.ui:
            self._show_fatal_error(f"Could not load main_window.ui: {loader.errorString()}")
            return

        self.ui.setAttribute(Qt.WA_DeleteOnClose, True)

    def _find_ui_elements(self):
        """Find all UI elements and validate critical ones."""
        # Widget mapping for cleaner code
        widget_mappings = [
            ('job_type_combo', QComboBox),
            ('media_type_combo', QComboBox),
            ('add_files_button', QPushButton),
            ('add_folder_button', QPushButton),
            ('recursive_checkbox', QCheckBox),
            ('input_file_types_label', QLabel),
            ('select_input_types_button', QPushButton),
            ('file_table', QTableWidget),
            ('output_folder_group_box', QGroupBox),
            ('select_output_folder_button', QPushButton),
            ('output_folder_path_display', QLineEdit),
            ('output_file_types_label', QLabel),
            ('select_output_type_button', QPushButton),
            ('overwrite_files_checkbox', QCheckBox),
            ('delete_input_checkbox', QCheckBox),
            ('output_same_folder_checkbox', QCheckBox),
            ('main_action_button', QPushButton),
            ('toggle_log_button', QPushButton),
            ('clear_log_button', QPushButton),
            ('log_output_text', QTextEdit),
            ('actionSettings', QAction),
            ('actionExit', QAction),
            ('progress_group_box', QGroupBox),
            ('overall_label', QLabel),
            ('overall_progress_bar', QProgressBar),
            ('overall_cancel_button', QPushButton),
            ('file_label', QLabel), # Will be hidden if dynamic rows replace it
            ('file_progress_bar', QProgressBar), # Will be hidden
            ('file_cancel_button', QPushButton), # Will be hidden
        ]

        # Find all widgets
        for attr_name, widget_type in widget_mappings:
            setattr(self, attr_name, self.ui.findChild(widget_type, attr_name))

        # Create a dedicated layout for dynamic progress bars
        if self.progress_group_box:
            if not self.progress_group_box.layout():
                # If progress_group_box has no layout, create one (e.g., QVBoxLayout)
                # This might indicate an issue with the .ui file or assumptions
                initial_layout = QVBoxLayout(self.progress_group_box)
                self.progress_group_box.setLayout(initial_layout)

            # Assuming the existing elements (overall progress) are already in the layout.
            # We add a new QGridLayout for the dynamic job rows.
            self.dynamic_progress_layout = QGridLayout()
            # Add some spacing or a separator if needed before this new layout
            # Example: self.progress_group_box.layout().addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
            self.progress_group_box.layout().addLayout(self.dynamic_progress_layout)
        else:
            # This would be a problem, as we need a parent for dynamic rows
            self.dynamic_progress_layout = None
            self._log_warning("progress_group_box not found, dynamic UI rows for jobs cannot be created.")


        # Setup status bar
        self.statusbar = self.ui.statusBar() if hasattr(self.ui, 'statusBar') and self.ui.statusBar() else QStatusBar(self.ui)
        if not (hasattr(self.ui, 'statusBar') and self.ui.statusBar()):
            if isinstance(self.ui.layout(), QVBoxLayout):
                self.ui.layout().addWidget(self.statusbar)

        # Validate critical widgets
        critical_widgets = [
            "job_type_combo", "media_type_combo", "add_files_button", "file_table",
            "output_folder_group_box", "main_action_button", "log_output_text",
            "actionSettings", "actionExit", "progress_group_box", "overall_label", 
            "overall_progress_bar", "overall_cancel_button", "file_label", 
            "file_progress_bar", "file_cancel_button"
        ]
        
        missing_widgets = [name for name in critical_widgets if getattr(self, name, None) is None]
        if missing_widgets:
            self._show_fatal_error(f"Critical UI elements not found: {', '.join(missing_widgets)}")

        # Attempt to make the log output text area vertically expandable
        if self.log_output_text:
            size_policy = self.log_output_text.sizePolicy()
            size_policy.setVerticalStretch(1) # Give it a stretch factor greater than 0
            size_policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
            self.log_output_text.setSizePolicy(size_policy)
            # As a test, you could also set a minimum height, though Expanding should be key
            # self.log_output_text.setMinimumHeight(100)

    def _setup_drag_drop(self):
        """Configure drag and drop functionality."""
        # Disable drag/drop for everything first
        for widget in [self, self.ui, self.centralWidget()]:
            if widget and hasattr(widget, 'setAcceptDrops'):
                widget.setAcceptDrops(False)

        # Enable specifically for file table
        if self.file_table:
            self.file_table.setAcceptDrops(True)
            self.file_table.installEventFilter(self)

    def _initialize_ui_states(self):
        """Set initial UI states."""
        # Progress UI
        if self.progress_group_box:
            self.progress_group_box.setVisible(False) # Initially hide the whole group
        
        if self.overall_progress_bar: # Overall progress bar is still used
            self.overall_progress_bar.setValue(0)
        if self.overall_label:
            self.overall_label.setText("Overall Progress:")

        # Hide the old single file progress elements as dynamic rows will be used
        if self.file_label:
            self.file_label.setVisible(False)
        if self.file_progress_bar:
            self.file_progress_bar.setVisible(False)
        if self.file_cancel_button:
            self.file_cancel_button.setVisible(False)

        # File table setup
        if self.file_table:
            self._setup_file_table()

    def _setup_file_table(self):
        """Configure the file table."""
        self.file_table.setHorizontalHeaderLabels(TABLE_HEADINGS)
        header = self.file_table.horizontalHeader()
        
        # Set resize modes
        resize_modes = [
            (COL_CHECK, QHeaderView.ResizeMode.ResizeToContents),
            (COL_PATH, QHeaderView.ResizeMode.Stretch),
            (COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        ]
        
        for col, mode in resize_modes:
            header.setSectionResizeMode(col, mode)
        
        header.setStyleSheet("QHeaderView::section { padding-left: 4px; padding-right: 4px; }")
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._show_file_table_context_menu)
        self.file_table.cellClicked.connect(self.handle_cell_click)

    def _connect_signals(self):
        """Connect all UI signals to their slots."""
        signal_connections = [
            (self.job_type_combo, 'currentTextChanged', self._on_job_type_changed),
            (self.media_type_combo, 'currentTextChanged', self._on_media_type_changed),
            (self.add_files_button, 'clicked', self.add_files),
            (self.add_folder_button, 'clicked', self.add_folder),
            (self.select_input_types_button, 'clicked', self._on_select_input_types_clicked),
            (self.select_output_folder_button, 'clicked', self._on_select_output_folder_clicked),
            (self.select_output_type_button, 'clicked', self._on_select_output_type_clicked),
            (self.output_same_folder_checkbox, 'toggled', self._on_output_same_folder_toggled),
            (self.delete_input_checkbox, 'toggled', self._on_delete_input_toggled),
            (self.main_action_button, 'clicked', self.start_conversion),
            (self.toggle_log_button, 'toggled', self.toggle_log_visibility),
            (self.clear_log_button, 'clicked', self.clear_log),
            (self.actionSettings, 'triggered', self.open_settings),
            (self.actionExit, 'triggered', self.close_application),
            (self.overall_cancel_button, 'clicked', self._request_conversion_stop),
            (self.file_cancel_button, 'clicked', self._request_conversion_stop),
        ]

        for widget, signal_name, slot in signal_connections:
            if widget:
                getattr(widget, signal_name).connect(slot)

    def _initialize_variables(self):
        """Initialize member variables."""
        self.table_data = []
        self.selected_job_details = None
        self.selected_media_type_details = None
        self.active_input_filters = set()
        self.selected_output_filter = None

        # For multi-processing
        self._process_pool_executor = None # Will be initialized later
        self._job_queue = Manager().Queue()
        self._results_queue = Manager().Queue()
        self._active_jobs = {} # To track UI elements for each job
        self._job_id_counter = 0

        # Timer to check for results from worker processes
        self._results_timer = QTimer(self)
        self._results_timer.timeout.connect(self._process_results_queue)
        # Interval can be adjusted, e.g., 100ms
        self._results_timer.setInterval(100)


    def _finalize_initialization(self):
        """Complete the initialization process."""
        self._populate_job_types()
        
        if self.delete_input_checkbox:
            self.delete_input_checkbox.setChecked(config.settings.DELETE_SOURCE_ON_SUCCESS)
        
        if self.output_same_folder_checkbox:
            self._on_output_same_folder_toggled(self.output_same_folder_checkbox.isChecked())

        self.update_ui_for_job_selection()
        
        if self.statusbar:
            self.statusbar.showMessage(
                f"Ready. Max Concurrent Jobs: {config.settings.CONCURRENT_JOBS}. Select a job type to begin."
            )

        self._setup_menu_system()
        self.ui.setWindowTitle(APP_NAME)

    def _show_fatal_error(self, message):
        """Show a fatal error and exit the application."""
        QMessageBox.critical(self, "Fatal Error", message)
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.quit()
        else:
            sys.exit(-1)

    def _setup_menu_system(self):
        """Initialize all menus and menu items."""
        menubar = self._get_or_create_menubar()
        self._setup_jobs_menu(menubar)
        self._setup_m3u_creator_menu(menubar)
        self._setup_help_menu(menubar)

    def _get_or_create_menubar(self):
        """Get existing menubar or create a new one."""
        menubar = self.ui.menuBar()
        if not menubar:
            menubar = QMenuBar(self.ui)
            if isinstance(self.ui, QMainWindow):
                self.ui.setMenuBar(menubar)
            elif hasattr(self, 'setMenuBar'):
                self.setMenuBar(menubar)
        return menubar

    def _find_menu_by_title(self, menubar, title):
        """Find an existing menu by its title."""
        for action in menubar.actions():
            menu = action.menu()
            if menu and menu.title() == title:
                return menu
        return None

    def _setup_m3u_creator_menu(self, menubar):
        """Set up the M3U Creator menu item."""
        if not (hasattr(self, 'ui') and self.ui and hasattr(self.ui, 'menuBar')):
            self._log_warning("Could not find menuBar on self.ui to add Tools menu for M3U Creator.")
            return

        tools_menu = self._find_menu_by_title(menubar, "&Tools")
        if not tools_menu:
            tools_menu = menubar.addMenu("&Tools")

        self.actionM3UPlaylistCreator = QAction("M3U Playlist Creator...", self.ui)
        self.actionM3UPlaylistCreator.setObjectName("actionM3UPlaylistCreator")
        self.actionM3UPlaylistCreator.triggered.connect(self._open_m3u_creator)
        tools_menu.addAction(self.actionM3UPlaylistCreator)

    def _setup_jobs_menu(self, menubar):
        """Set up the Jobs menu with concurrent jobs submenu."""
        self.jobs_menu = QMenu("&Jobs", self.ui)
        self.concurrent_job_actions = []
        
        concurrent_jobs_menu = QMenu("Concurrent Jobs", self.ui)
        max_jobs_options = self._get_max_jobs_range()
        
        for job_count in max_jobs_options:
            action = QAction(
                f"{job_count} Job{'s' if job_count > 1 else ''}", 
                concurrent_jobs_menu, 
                checkable=True
            )
            action.setData(job_count)
            action.triggered.connect(self._handle_concurrent_jobs_changed)
            concurrent_jobs_menu.addAction(action)
            self.concurrent_job_actions.append(action)
            
            if job_count == config.settings.CONCURRENT_JOBS:
                action.setChecked(True)

        self.jobs_menu.addMenu(concurrent_jobs_menu)
        
        help_menu_action = self._find_menu_action_by_title(menubar, "&Help")
        if help_menu_action:
            menubar.insertMenu(help_menu_action, self.jobs_menu)
        else:
            menubar.addMenu(self.jobs_menu)

    def _setup_help_menu(self, menubar):
        """Set up the Help menu."""
        self.help_menu = QMenu("&Help", self.ui)
        self.actionAbout = QAction("&About", self.ui)
        self.actionAbout.triggered.connect(self.show_about_dialog)
        self.help_menu.addAction(self.actionAbout)
        menubar.addMenu(self.help_menu)

    def _get_max_jobs_range(self):
        """Get the range of available concurrent job options."""
        cpu_count = os.cpu_count() or 4
        max_jobs = min(cpu_count + 1, 11)
        return range(1, max_jobs)

    def _find_menu_action_by_title(self, menubar, title):
        """Find a menu action by its menu title."""
        for action in menubar.actions():
            menu = action.menu()
            if menu and menu.title() == title:
                return action
        return None

    def _log_warning(self, message):
        """Log a warning message using available logging mechanism."""
        if hasattr(self, 'log_output_text') and self.log_output_text:
            self.log_output_text.append(f"<font color='orange'>Warning: {message}</font>")
        else:
            print(f"DEBUG: {message}", file=sys.stderr)

    def _emit_or_print(self, message, fallback_color_code=None, is_error=False):
        """
        Wrapper to call the consolidated utils.emit_or_print, directing output
        to this window's log_output_text widget.
        """
        if self.log_output_text:
            utils.emit_or_print(
                message,
                signal=self.log_output_text,
                fallback_color_code=fallback_color_code,
                is_error=is_error
            )
        else:
            # Fallback if log_output_text somehow doesn't exist, though it should.
            utils.emit_or_print(
                message,
                signal=None, # Ensures console output
                fallback_color_code=fallback_color_code,
                is_error=is_error
            )

    # Dialog methods
    @Slot()
    def _open_m3u_creator(self):
        """Open the M3U Creator dialog."""
        parent_widget = self.ui if hasattr(self, 'ui') and self.ui is not None else self
        try:
            dialog = M3UCreatorWindow(parent=parent_widget)
            dialog.exec()
        except Exception as e:
            error_message = f"Could not open M3U Playlist Creator: {e}"
            self._log_warning(error_message)
            
            parent_for_msgbox = self.ui if (hasattr(self, 'ui') and self.ui is not None 
                                          and isinstance(self.ui, QWidget)) else self
            if not isinstance(parent_for_msgbox, QWidget):
                parent_for_msgbox = None
            QMessageBox.critical(parent_for_msgbox, "M3U Creator Error", error_message)

    @Slot()
    def show_about_dialog(self):
        """Show the About dialog."""
        about_text = self._build_about_text()
        
        msg_box = QMessageBox(self.ui if self.ui else self)
        msg_box.setWindowTitle(f"About {APP_NAME}")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(about_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        msg_box.exec()

    def _build_about_text(self):
        """Build the about dialog text."""
        return (
            f"<h2>{APP_NAME}</h2>"
            f"<p><b>Version:</b> {APP_VERSION}</p>"
            f"<p><b>Copyright:</b> {APP_COPYRIGHT}</p>"
            f"<p>A tool for converting and managing media files.</p>"
            f"<hr>"
            f"<p><b>Python Version:</b><br>{sys.version.split()[0]}</p>"
            f"<hr>"
            f"<p><b>Tools and Libraries Used:</b><br>{TOOLS_USED_TEXT}</p>"
            f"<hr>"
            f"<p><b>Third-Party Licenses:</b><br>{LICENSES_TEXT}</p>"
            f"<hr>"
            f"<p><b>GitHub Repository:</b> <a href='{GITHUB_URL}'>retro_converter_tool on GitHub</a></p>"
        )

    # Threading and conversion methods
    def _ensure_thread_stopped(self):
        """Ensures the conversion thread is properly stopped."""
        # This method is now largely obsolete due to ProcessPoolExecutor.
        # Kept for structure if any old single-threaded path remained, but should be empty.
        pass

    def _shutdown_executor(self):
        """Shuts down the process pool executor."""
        if self._process_pool_executor:
            self._emit_or_print("Shutting down worker processes...", fallback_color_code="cyan")
            # Signal workers to stop (if they check for a sentinel or queue status)
            # For now, rely on executor shutdown. Will need a more graceful stop for workers.
            # Potentially add sentinel values to the job queue for each worker.
            for _ in range(config.settings.CONCURRENT_JOBS): # Send sentinel for each potential worker
                try:
                    self._job_queue.put(None, timeout=0.1) # Sentinel value
                except Exception: # Queue might be full or other issues
                    pass
            self._process_pool_executor.shutdown(wait=True)
            self._process_pool_executor = None
            self._emit_or_print("Worker processes shut down.", fallback_color_code="green")

    @Slot()
    def _on_about_to_quit(self):
        """Handle application quit signal."""
        print("DEBUG: QApplication.aboutToQuit signal received in ConverterWindow.")
        self._request_conversion_stop() # Request ongoing jobs to stop
        self._shutdown_executor()
        if self._results_timer.isActive():
            self._results_timer.stop()
        print("DEBUG: Exiting _on_about_to_quit in ConverterWindow.")

    @Slot()
    def _request_conversion_stop(self):
        """Request conversion to stop."""
        # This needs to be adapted for ProcessPoolExecutor.
        # For now, it might involve setting a flag that workers check,
        # or clearing the job queue and relying on executor shutdown.
        # A more robust solution would involve sending a stop signal to specific PIDs
        # or having workers periodically check a shared stop flag.
        self._emit_or_print("Overall cancellation requested. Active jobs should stop after their current task.", fallback_color_code="yellow")
        # Clear pending jobs from the queue
        while not self._job_queue.empty():
            try:
                self._job_queue.get_nowait()
            except Exception:
                break

        # For running jobs, they need to cooperatively stop.
        # This is a placeholder; true cancellation of running subprocesses is complex.
        # The current `utils.run_command` doesn't have a non-blocking way to terminate its process from here.
        # For now, we'll rely on the fact that new jobs won't be picked up.
        # Full cancellation of individual running jobs is a future task as per requirements.

        # The old QThread based cancellation logic is removed.
        # For overall cancel, disabling the buttons is handled by set_ui_enabled_for_conversion(False)
        # when starting, and they are re-enabled when all jobs complete or UI is reset.
        # Individual cancel buttons on dynamic rows would need separate logic if they were functional.
        if self.overall_cancel_button:
             self.overall_cancel_button.setEnabled(False) # Disable during cancellation process
        if self.statusbar:
            self.statusbar.showMessage("Overall cancellation requested. Pending jobs cleared.")


    # Settings and job management
    @Slot()
    def _handle_concurrent_jobs_changed(self):
        """Handle concurrent jobs setting change."""
        triggered_action = self.sender()
        if not isinstance(triggered_action, QAction):
            if utils.APP_LOGGER:
                utils.APP_LOGGER.warning(f"_handle_concurrent_jobs_changed called by non-QAction sender: {type(triggered_action)}")
            return

        num_jobs = triggered_action.data()
        if isinstance(num_jobs, int) and num_jobs > 0:
            config.settings.CONCURRENT_JOBS = num_jobs
            save_app_settings()
            
            if self.statusbar:
                self.statusbar.showMessage(f"Max concurrent jobs set to {num_jobs}. Restart jobs for change to take full effect if already running.")

            # Update action states
            for action in self.concurrent_job_actions:
                action.setChecked(action is triggered_action)

            # If an executor exists, shut it down. It will be recreated with the new
            # max_workers value when the next conversion starts.
            if self._process_pool_executor:
                self._emit_or_print("INFO: Concurrent jobs setting changed. Shutting down existing worker pool. It will restart on next job.", fallback_color_code="cyan")
                self._shutdown_executor() # This sets self._process_pool_executor to None
        else:
            if utils.APP_LOGGER:
                utils.APP_LOGGER.error(f"Invalid data for concurrent jobs action: {triggered_action.data() if triggered_action else 'Unknown'}")

    def _populate_job_types(self):
        """Populate the job type combo box."""
        if not self.job_type_combo:
            return
        
        self.job_type_combo.blockSignals(True)
        self.job_type_combo.clear()
        self.job_type_combo.addItem("(Select Job Type)")
        
        for job in menu_definitions.JOB_DEFINITIONS:
            self.job_type_combo.addItem(job["job_name"])
        
        self.job_type_combo.blockSignals(False)
        self.job_type_combo.setCurrentIndex(0)

    # Event handlers for UI state changes
    @Slot(bool)
    def _on_output_same_folder_toggled(self, checked):
        """Handle output same folder checkbox toggle."""
        show_custom_output_widgets = not checked
        
        for widget in [self.select_output_folder_button, self.output_folder_path_display]:
            if widget:
                widget.setVisible(show_custom_output_widgets)

        if checked and self.output_folder_path_display:
            self.output_folder_path_display.clear()
        
        self.update_convert_button_state()

    @Slot(bool)
    def _on_delete_input_toggled(self, checked):
        """Handle delete input checkbox toggle."""
        config.settings.DELETE_SOURCE_ON_SUCCESS = checked
        if self.statusbar:
            self.statusbar.showMessage(
                f"Delete input files on success: {'Enabled' if checked else 'Disabled'}")

    @Slot(str)
    def _on_job_type_changed(self, selected_job_name):
        """Handle job type selection change."""
        if not self.media_type_combo:
            return
        
        self._reset_job_selection()
        
        if selected_job_name and selected_job_name != "(Select Job Type)":
            self._populate_media_types(selected_job_name)

        self.media_type_combo.setCurrentIndex(0)
        self.update_ui_for_job_selection()
        
        if self.statusbar:
            self.statusbar.showMessage(f"Job type '{selected_job_name}' selected. Now select a media type.")

    def _reset_job_selection(self):
        """Reset job-related selections."""
        self.media_type_combo.blockSignals(True)
        self.media_type_combo.clear()
        self.media_type_combo.addItem("(Select Media Type)")
        self.media_type_combo.blockSignals(False)
        
        self.selected_job_details = None
        self.selected_media_type_details = None
        self.active_input_filters.clear()
        self.selected_output_filter = None

    def _populate_media_types(self, job_name):
        """Populate media types for the selected job."""
        for job_def in menu_definitions.JOB_DEFINITIONS:
            if job_def["job_name"] == job_name:
                self.selected_job_details = job_def
                for media_type in job_def.get("media_types", []):
                    self.media_type_combo.addItem(media_type["media_name"])
                break

    @Slot(str)
    def _on_media_type_changed(self, selected_media_name):
        """Handle media type selection change."""
        self._reset_media_selection()
        
        if self.selected_job_details and selected_media_name and selected_media_name != "(Select Media Type)":
            self._setup_media_type_details(selected_media_name)

        self.update_ui_for_media_selection()

    def _reset_media_selection(self):
        """Reset media type-related selections."""
        self.selected_media_type_details = None
        self.active_input_filters.clear()
        self.selected_output_filter = None

    def _setup_media_type_details(self, media_name):
        """Setup details for the selected media type."""
        for media_def in self.selected_job_details.get("media_types", []):
            if media_def["media_name"] == media_name:
                self.selected_media_type_details = media_def
                self.active_input_filters = set(self.selected_media_type_details.get("input_ext", []))
                
                # Auto-select output if only one option
                output_exts = self.selected_media_type_details.get("output_ext", [])
                if output_exts:
                    if isinstance(output_exts, list) and len(output_exts) == 1 and output_exts[0]:
                        self.selected_output_filter = output_exts[0]
                    elif isinstance(output_exts, str):
                        self.selected_output_filter = output_exts
                break

    # UI update methods with better organization
    def update_ui_for_job_selection(self):
        """Update UI elements based on job selection."""
        job_is_selected = bool(self.selected_job_details)
        
        if self.media_type_combo:
            self.media_type_combo.setEnabled(job_is_selected)

        if not job_is_selected:
            self._reset_media_selection()

        self.update_ui_for_media_selection()

    def update_ui_for_media_selection(self):
        """Update UI elements based on media type selection."""
        media_is_selected = bool(self.selected_media_type_details)
        
        # Get display strings
        action_text, input_ext_str, output_ext_str = self._get_display_strings()
        
        # Update labels and buttons
        self._update_ui_labels(action_text, input_ext_str, output_ext_str)
        
        # Update button states
        self._update_button_states(media_is_selected)
        
        # Update output folder visibility
        self._update_output_folder_ui()
        
        # Apply filters and update state
        self._apply_filter_to_table()
        self.update_convert_button_state()

    def _get_display_strings(self):
        """Get the display strings for UI elements."""
        action_text = "START JOB"
        input_ext_str = "N/A"
        output_ext_str = "N/A"

        if self.selected_job_details:
            action_text = self.selected_job_details.get("action_text", "START JOB").upper()

        if self.selected_media_type_details:
            action_text = self.selected_media_type_details.get("action_text", action_text).upper()
            input_ext_str = self._get_input_extensions_string()
            output_ext_str = self._get_output_extensions_string()

        return action_text, input_ext_str, output_ext_str

    def _get_input_extensions_string(self):
        """Get formatted input extensions string."""
        current_display_input_exts = self.active_input_filters or set(
            self.selected_media_type_details.get("input_ext", []))
        
        return (", ".join([f".{ext}" for ext in sorted(list(current_display_input_exts))]) 
                if current_display_input_exts else "Any")

    def _get_output_extensions_string(self):
        """Get formatted output extensions string."""
        possible_output_exts = self.selected_media_type_details.get("output_ext", [])
        
        if self.selected_output_filter:
            return f".{self.selected_output_filter}"
        elif not possible_output_exts:
            return ("N/A (Folder/Info)" if not self.selected_media_type_details.get("requires_output_folder", False) 
                   else "Folder")
        elif possible_output_exts and not self.selected_output_filter:
            return "(Select Output)"
        
        return "N/A"

    def _update_ui_labels(self, action_text, input_ext_str, output_ext_str):
        """Update UI labels with new text."""
        label_updates = [
            (self.main_action_button, action_text),
            (self.input_file_types_label, f"Input: {input_ext_str}"),
            (self.output_file_types_label, f"Output: {output_ext_str}")
        ]
        
        for widget, text in label_updates:
            if widget:
                widget.setText(text)

    def _update_button_states(self, media_is_selected):
        """Update button enabled states."""
        can_select_input_types = (media_is_selected and 
                                 bool(self.selected_media_type_details.get("input_ext") 
                                     if self.selected_media_type_details else False))
        
        possible_output_exts = (self.selected_media_type_details.get("output_ext", []) 
                               if self.selected_media_type_details else [])
        can_select_output_type = (isinstance(possible_output_exts, list) and 
                                 len(possible_output_exts) > 1)

        if self.select_input_types_button:
            self.select_input_types_button.setEnabled(can_select_input_types)
        
        if self.select_output_type_button:
            self.select_output_type_button.setEnabled(can_select_output_type)

    def _update_output_folder_ui(self):
        """Update output folder UI visibility and state."""
        requires_output_folder = (self.selected_media_type_details.get("requires_output_folder", False) 
                                 if self.selected_media_type_details else False)
        
        if self.output_folder_group_box:
            self.output_folder_group_box.setEnabled(requires_output_folder)

        output_in_same_folder = (self.output_same_folder_checkbox.isChecked() 
                               if self.output_same_folder_checkbox else True)
        show_custom_output_widgets = requires_output_folder and not output_in_same_folder

        for widget in [self.select_output_folder_button, self.output_folder_path_display]:
            if widget:
                widget.setVisible(show_custom_output_widgets)

        if not requires_output_folder or output_in_same_folder:
            if self.output_folder_path_display:
                self.output_folder_path_display.clear()

    # File and folder handling methods
    @Slot()
    def add_files(self):
        """Add files through file dialog."""
        dialog_filter_name, current_input_exts = self._get_file_dialog_filter()
        
        patterns = [f"*.{ext}" for ext in sorted(list(current_input_exts))]
        dialog_filter_string = f"{dialog_filter_name} ({' '.join(patterns)});;All Files (*.*)"

        files, _ = QFileDialog.getOpenFileNames(self.ui, "Select Files", "", dialog_filter_string)
        if files:
            self.process_added_paths(files, from_add_files_dialog=True, 
                                   dialog_filter_exts=current_input_exts)

    def _get_file_dialog_filter(self):
        """Get file dialog filter based on current selection."""
        dialog_filter_name = "All Supported Files"
        current_input_exts = set(menu_definitions.ALL_VALID_INPUT_EXTENSIONS)

        if self.selected_media_type_details:
            media_specific_exts = self.selected_media_type_details.get("input_ext", [])
            if media_specific_exts:
                current_input_exts = set(media_specific_exts)
                media_name = self.selected_media_type_details.get("media_name", "Current Job")
                dialog_filter_name = f"{media_name} Files"

        return dialog_filter_name, current_input_exts

    @Slot()
    def add_folder(self):
        """Add folder through folder dialog."""
        folder = QFileDialog.getExistingDirectory(self.ui, "Select Folder")
        if folder:
            self.process_added_paths([folder])

    @Slot()
    def clear_input_list(self):
        """Clear the input file list."""
        self.table_data = []
        self.update_table_widget()
        if self.statusbar:
            self.statusbar.showMessage("Input list cleared.")
        self.update_convert_button_state()

    def process_added_paths(self, paths, from_add_files_dialog=False, dialog_filter_exts=None):
        """Process added file/folder paths."""
        is_recursive = self.recursive_checkbox.isChecked() if self.recursive_checkbox else False
        newly_added_count = 0
        current_paths_in_table = {row_data[COL_PATH] for row_data in self.table_data}

        valid_exts_for_adding = self._get_valid_extensions_for_adding(
            from_add_files_dialog, dialog_filter_exts)
        
        ignored_files_log = []

        for item_path_raw in paths:
            item_path = os.path.normpath(item_path_raw)
            if not item_path or not os.path.exists(item_path):
                continue

            if os.path.isfile(item_path):
                newly_added_count += self._process_single_file(
                    item_path, valid_exts_for_adding, current_paths_in_table, ignored_files_log)
            elif os.path.isdir(item_path):
                newly_added_count += self._process_folder(
                    item_path, is_recursive, valid_exts_for_adding, current_paths_in_table)

        self._finalize_path_processing(newly_added_count, ignored_files_log)

    def _get_valid_extensions_for_adding(self, from_add_files_dialog, dialog_filter_exts):
        """Get valid extensions for adding files."""
        if from_add_files_dialog and dialog_filter_exts:
            return dialog_filter_exts
        elif self.active_input_filters:
            return self.active_input_filters
        elif self.selected_media_type_details:
            return set(self.selected_media_type_details.get("input_ext", []))
        else:
            return set(menu_definitions.ALL_VALID_INPUT_EXTENSIONS)

    def _process_single_file(self, file_path, valid_exts, current_paths, ignored_files):
        """Process a single file for adding to the list."""
        file_ext_lower = os.path.splitext(file_path)[1].lower().lstrip('.')
        
        if ((not valid_exts or file_ext_lower in valid_exts) and 
            file_path not in current_paths):
            self.table_data.append([True, file_path, file_ext_lower.upper()])
            return 1
        elif file_path not in current_paths:
            ignored_files.append(
                os.path.basename(file_path) + f" (type '.{file_ext_lower}' not in current add filter)")
        
        return 0

    def _process_folder(self, folder_path, is_recursive, valid_exts, current_paths):
        """Process a folder for adding files to the list."""
        count = 0
        for f_path in self._scan_folder(folder_path, is_recursive, valid_exts):
            if f_path not in current_paths:
                file_ext_lower = os.path.splitext(f_path)[1].lower().lstrip('.')
                self.table_data.append([True, f_path, file_ext_lower.upper()])
                count += 1
        return count

    def _finalize_path_processing(self, newly_added_count, ignored_files_log):
        """Finalize the path processing operation."""
        if ignored_files_log and self.log_output_text:
            self.log_output_text.append(
                f"<font color='orange'>WARNING: Files ignored during add (type mismatch or duplicate): "
                f"{', '.join(ignored_files_log)}</font>")

        if newly_added_count > 0:
            self.table_data.sort(key=lambda x: x[COL_PATH])
            self.update_table_widget()

        if self.statusbar:
            self.statusbar.showMessage(f"{len(self.table_data)} file(s) in list. ({newly_added_count} added).")
        
        self.update_convert_button_state()

    def _scan_folder(self, folder_path, recursive, valid_extensions_for_scan):
        """Scan folder for valid files."""
        found = []
        norm_folder = os.path.normpath(folder_path)
        if not os.path.isdir(norm_folder):
            return found

        norm_temp_main_dir = os.path.normpath(config.settings.MAIN_TEMP_DIR)
        if norm_folder.startswith(norm_temp_main_dir):
            if self.log_output_text:
                self.log_output_text.append(
                    f"<font color='orange'>Skipping scan of temp directory: {norm_folder}</font>")
            return found

        for r, dirs, fs in os.walk(norm_folder):
            norm_r = os.path.normpath(r)
            if '_processing_temps_' in norm_r or norm_r.startswith(norm_temp_main_dir):
                dirs[:] = []
                continue

            for f_item in fs:
                fp = os.path.join(norm_r, f_item)
                if os.path.isfile(fp):
                    ext_lower = os.path.splitext(f_item)[1].lower().lstrip('.')
                    if not valid_extensions_for_scan or ext_lower in valid_extensions_for_scan:
                        found.append(os.path.normpath(fp))
            
            if not recursive:
                break
        return found

    # Table and UI interaction methods
    def update_table_widget(self):
        """Update the table widget with current data."""
        if not self.file_table:
            return

        self.file_table.setRowCount(0)
        self.file_table.setRowCount(len(self.table_data))

        for r_idx, (checked, path, file_type) in enumerate(self.table_data):
            # Checkbox item
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.file_table.setItem(r_idx, COL_CHECK, chk_item)

            # Path item
            self.file_table.setItem(r_idx, COL_PATH, QTableWidgetItem(path))

            # Type item
            type_item = QTableWidgetItem(file_type)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.file_table.setItem(r_idx, COL_TYPE, type_item)

        self._apply_filter_to_table()

    @Slot(int, int)
    def handle_cell_click(self, row, column):
        """Handle clicks on table cells."""
        if (not self.file_table or column != COL_CHECK or 
            not (0 <= row < len(self.table_data))):
            return

        item = self.file_table.item(row, column)
        if not item:
            return

        if item.flags() & Qt.ItemFlag.ItemIsEnabled:
            self.table_data[row][COL_CHECK] = not self.table_data[row][COL_CHECK]
            item.setCheckState(
                Qt.CheckState.Checked if self.table_data[row][COL_CHECK] else Qt.CheckState.Unchecked)
            self.update_convert_button_state()
        else:
            if self.statusbar:
                self.statusbar.showMessage(
                    "This file type is currently filtered out. Adjust input filters to select.", 3000)

    def set_row_enabled_state(self, r_idx, enabled):
        """Set the enabled state for a table row."""
        if not self.file_table or not (0 <= r_idx < self.file_table.rowCount()):
            return

        palette = self.palette()
        color = (palette.color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText) if enabled 
                else palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText))

        for c_idx in range(self.file_table.columnCount()):
            item = self.file_table.item(r_idx, c_idx)
            if item:
                flags = item.flags()
                item.setFlags(flags | Qt.ItemFlag.ItemIsEnabled if enabled 
                             else flags & ~Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(color)

    def _apply_filter_to_table(self):
        """Apply current filters to the table."""
        if not self.file_table:
            return

        visible_exts = self.active_input_filters or (
            set(self.selected_media_type_details.get("input_ext", [])) 
            if self.selected_media_type_details else set())

        for i in range(self.file_table.rowCount()):
            row_data_type_str = self.table_data[i][COL_TYPE].lower()
            
            is_enabled = (not self.selected_media_type_details or 
                         not visible_exts or 
                         row_data_type_str in visible_exts)

            self.set_row_enabled_state(i, is_enabled)

            if not is_enabled and self.table_data[i][COL_CHECK]:
                self.table_data[i][COL_CHECK] = False
                item = self.file_table.item(i, COL_CHECK)
                if item:
                    item.setCheckState(Qt.CheckState.Unchecked)

        self.update_convert_button_state()

    # Context menu and table operations
    @Slot(QPoint)
    def _show_file_table_context_menu(self, position: QPoint):
        """Show context menu for the file table."""
        if not self.file_table:
            return
        
        menu = QMenu(self)
        actions = [
            ("Select all (visible/active)", self._on_table_select_all),
            ("Clear selection in rows", self._on_table_clear_selection),
            ("Remove selected rows", self._on_table_remove_selected),
            (None, None),  # Separator
            ("Clear all items from list", self.clear_input_list)
        ]

        for text, slot in actions:
            if text is None:
                menu.addSeparator()
            else:
                action = menu.addAction(text)
                action.triggered.connect(slot)

        menu.exec(self.file_table.mapToGlobal(position))

    @Slot()
    def _on_table_select_all(self):
        """Select all enabled items in the table."""
        if not self.file_table:
            return
        
        for i in range(len(self.table_data)):
            item = self.file_table.item(i, COL_CHECK)
            if item and item.flags() & Qt.ItemFlag.ItemIsEnabled:
                self.table_data[i][COL_CHECK] = True
                item.setCheckState(Qt.CheckState.Checked)
        
        self.update_convert_button_state()

    @Slot()
    def _on_table_clear_selection(self):
        """Clear selection for all items in the table."""
        if not self.file_table:
            return
        
        for i in range(len(self.table_data)):
            self.table_data[i][COL_CHECK] = False
            item = self.file_table.item(i, COL_CHECK)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        
        self.update_convert_button_state()

    @Slot()
    def _on_table_remove_selected(self):
        """Remove selected items from the table."""
        removed_count = 0
        for i in range(len(self.table_data) - 1, -1, -1):
            if self.table_data[i][COL_CHECK]:
                del self.table_data[i]
                removed_count += 1

        if removed_count > 0:
            self.update_table_widget()
            if self.statusbar:
                self.statusbar.showMessage(f"{removed_count} item(s) removed. {len(self.table_data)} remaining.")
        
        self.update_convert_button_state()

    # Input/Output type selection methods
    @Slot()
    def _on_select_input_types_clicked(self):
        """Show input type selection menu."""
        if not self.selected_media_type_details:
            if self.statusbar:
                self.statusbar.showMessage("Please select a job and media type first.", 3000)
            return

        possible_input_exts = self.selected_media_type_details.get("input_ext", [])
        if not possible_input_exts:
            if self.statusbar:
                self.statusbar.showMessage("No specific input types to filter for this selection.", 3000)
            return

        menu = QMenu(self)
        for ext in sorted(possible_input_exts):
            action = QAction(f".{ext}", self)
            action.setCheckable(True)
            action.setChecked(ext in self.active_input_filters)
            action.toggled.connect(
                lambda checked, current_ext=ext: self._on_input_filter_type_toggled(checked, current_ext))
            menu.addAction(action)

        if self.select_input_types_button:
            button_pos = self.select_input_types_button.mapToGlobal(
                QPoint(0, self.select_input_types_button.height()))
            menu.exec(button_pos)

    @Slot(bool, str)
    def _on_input_filter_type_toggled(self, checked, extension):
        """Handle input filter type toggle."""
        if checked:
            self.active_input_filters.add(extension)
        else:
            self.active_input_filters.discard(extension)

        self._update_input_filter_display()
        self._apply_filter_to_table()
        self.update_convert_button_state()

    def _update_input_filter_display(self):
        """Update the input filter display label."""
        active_filter_list = sorted(list(self.active_input_filters))
        
        if self.input_file_types_label:
            if active_filter_list:
                display_text = f"Input: {', '.join(['.' + ext for ext in active_filter_list])}"
            elif self.selected_media_type_details:
                all_media_exts = self.selected_media_type_details.get("input_ext", [])
                display_text = f"Input: {', '.join(['.' + ext for ext in all_media_exts]) if all_media_exts else 'Any'}"
            else:
                display_text = "Input: N/A"
            
            self.input_file_types_label.setText(display_text)

        if self.statusbar:
            filter_text = ', '.join(active_filter_list) if active_filter_list else 'None (showing all for media type)'
            self.statusbar.showMessage(f"Input filter updated. Active: {filter_text}", 3000)

    @Slot()
    def _on_select_output_type_clicked(self):
        """Show output type selection menu."""
        if not self.selected_media_type_details:
            if self.statusbar:
                self.statusbar.showMessage("Please select a media type first.", 3000)
            return

        possible_output_exts = self.selected_media_type_details.get("output_ext", [])
        if not isinstance(possible_output_exts, list) or not possible_output_exts:
            if self.statusbar:
                self.statusbar.showMessage("No selectable output types for this media.", 3000)
            return

        menu = QMenu(self)
        for ext_string in possible_output_exts:
            if not ext_string:
                continue
            action = QAction(f".{ext_string}", self)
            action.setCheckable(True)
            action.setChecked(ext_string == self.selected_output_filter)
            action.triggered.connect(
                lambda checked=False, bound_ext=ext_string: self._on_output_filter_type_selected(bound_ext))
            menu.addAction(action)

        if self.select_output_type_button:
            button_pos = self.select_output_type_button.mapToGlobal(
                QPoint(0, self.select_output_type_button.height()))
            menu.exec(button_pos)

    @Slot(str)
    def _on_output_filter_type_selected(self, extension):
        """Handle output filter type selection."""
        self.selected_output_filter = extension
        if self.output_file_types_label:
            self.output_file_types_label.setText(f"Output: .{extension}")
        if self.statusbar:
            self.statusbar.showMessage(f"Output type set to: .{extension}", 3000)
        self.update_convert_button_state()

    @Slot()
    def _on_select_output_folder_clicked(self):
        """Handle output folder selection."""
        if not self.output_folder_path_display:
            return
        
        current_path = self.output_folder_path_display.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self.ui, "Select Output Folder", current_path)
        
        if folder:
            self.output_folder_path_display.setText(os.path.normpath(folder))
        
        self.update_convert_button_state()

    @Slot()
    def update_convert_button_state(self):
        """Update the convert button enabled state."""
        if not self.main_action_button:
            return

        conditions = [
            self._check_job_and_media_selected(),
            self._check_output_type_ok(),
            self._check_files_checked_and_active(),
            self._check_output_folder_ok()
        ]

        self.main_action_button.setEnabled(all(conditions))

    def _check_job_and_media_selected(self):
        """Check if job and media type are selected."""
        return bool(self.selected_media_type_details)

    def _check_output_type_ok(self):
        """Check if output type selection is valid."""
        if not self.selected_media_type_details:
            return True
        
        defined_output_exts = self.selected_media_type_details.get("output_ext", [])
        return not defined_output_exts or bool(self.selected_output_filter)

    def _check_files_checked_and_active(self):
        """Check if there are checked and active files."""
        if not self.file_table:
            return False

        current_filter_set = self.active_input_filters or (
            set(self.selected_media_type_details.get("input_ext", [])) 
            if self.selected_media_type_details else set())

        for row_data in self.table_data:
            if row_data[COL_CHECK]:
                item_type = row_data[COL_TYPE].lower()
                if (not self.selected_media_type_details or 
                    not current_filter_set or 
                    item_type in current_filter_set):
                    return True
        
        return False

    def _check_output_folder_ok(self):
        """Check if output folder configuration is valid."""
        if not (self.selected_media_type_details and 
                self.selected_media_type_details.get("requires_output_folder", False)):
            return True

        if (self.output_same_folder_checkbox and 
            not self.output_same_folder_checkbox.isChecked()):
            return bool(self.output_folder_path_display and 
                       self.output_folder_path_display.text())
        
        return True

    # Conversion methods (continuing in next part due to length)
    @Slot()
    def start_conversion(self):
        """Start the conversion process."""
        # The check for an existing conversion_thread.isRunning() has been removed
        # as ProcessPoolExecutor manages concurrency. UI state should prevent re-entry.

        if not self._validate_conversion_setup():
            return

        selected_files_data = self._get_selected_files_for_conversion()
        if not selected_files_data:
            QMessageBox.warning(self, "No Files", 
                              "No files selected for conversion (or none match current input filters).")
            return

        output_folder = self._validate_and_prepare_output_folder()
        if output_folder is False:  # Explicit False means validation failed
            return

        self._start_conversion_processes(selected_files_data, output_folder)

    @Slot()
    def _process_results_queue(self):
        """Process messages from the results queue sent by worker processes."""
        while not self._results_queue.empty():
            try:
                message = self._results_queue.get_nowait()
                job_id = message.get("job_id", -1)
                message_type = message.get("type")
                data = message.get("data")

                if message_type == "status_update": # This is per-job stage update
                    description = data.get('description', '')
                    # current_step = data.get('current_step', 0) # This is stage number 1,2,3
                    # total_steps = data.get('total_steps', N_STAGES_PER_FILE) # This is N_STAGES_PER_FILE
                    # We can use this to update the job's label if needed, e.g. with stage_description
                    if job_id in self._active_jobs and self._active_jobs[job_id].get('label'):
                         self._active_jobs[job_id]['label'].setText(f"{self._active_jobs[job_id]['filename']} [{description}]")
                    self._emit_or_print(f"Job {job_id} Stage: {description}", fallback_color_code="cyan")

                elif message_type == "file_progress_update": # This is percentage for the job's file
                    percentage = data.get('percentage', 0)
                    self._update_job_progress(job_id, percentage)
                    # self._emit_or_print(f"Job {job_id} File Progress: {percentage}%", fallback_color_code="blue") # Log less
                elif message_type == "output_update":
                    self._emit_or_print(f"Job {job_id} Log: {data['message']}") # No color, default
                elif message_type == "error_update":
                    self._emit_or_print(f"Job {job_id} Error: {data['message']}", is_error=True) # Use is_error flag
                elif message_type == "job_started":
                    # TODO: Create UI elements for this job_id
                    filename = data.get("filename", "Unknown file")
                    self._emit_or_print(f"Job {job_id} Started: {filename}", fallback_color_code="green")
                    self._add_job_progress_row(job_id, filename)
                elif message_type == "job_completed":
                    success = data.get("success", False)
                    job_filename = self._active_jobs.get(job_id, {}).get('filename', 'Unknown job') # Get filename from stored active jobs

                    if success:
                        self._emit_or_print(f"Job {job_id} ({job_filename}) Completed Successfully.", fallback_color_code="green")
                    else:
                        self._emit_or_print(f"Job {job_id} ({job_filename}) Failed. Check logs for details: {data.get('message', '')}", is_error=True) # Use is_error flag

                    self._finalize_job_progress_row(job_id, success) # This updates UI and overall progress bar

                    if job_id in self._active_jobs:
                        self._active_jobs[job_id]['status'] = 'completed' # Mark as completed
                    self._check_all_jobs_complete() # Check if all jobs are done


                # Add more message types as needed (e.g., for dynamic UI creation)

            except Exception as e: # Was queue.Empty, but Manager().Queue() might raise different
                # self._emit_or_print(f"Error processing results queue: {e}", is_error=True)
                break # No more items or an error occurred

    def _check_all_jobs_complete(self):
        # This function will be called after a job completes to see if all jobs are done.
        # For now, it's a placeholder.
        all_done = True
        if not self._job_queue.empty(): # Check if there are still jobs to be processed
            all_done = False
        else: # If job queue is empty, check if all active jobs are 'completed'
            for job_id, job_info in self._active_jobs.items():
                if job_info.get('status') != 'completed':
                    all_done = False
                    break

        if all_done:
            self._emit_or_print("All conversion jobs finished.", fallback_color_code="green")
            if self.statusbar:
                self.statusbar.showMessage("All jobs finished.")
            self.set_ui_enabled_for_conversion(True) # Re-enable UI
            if self._results_timer.isActive():
                self._results_timer.stop()
            # self._shutdown_executor() # Optionally shutdown executor if no more jobs are expected soon

    def _add_job_progress_row(self, job_id, filename):
        """Adds a new row of progress widgets for a given job."""
        if not self.dynamic_progress_layout:
            self._log_warning(f"Cannot add progress row for job {job_id}: dynamic_progress_layout is None.")
            return

        if job_id in self._active_jobs and self._active_jobs[job_id].get('label') is not None:
            # Row might already exist if job_started is re-sent or handled multiple times
            self._log_warning(f"Job row for job_id {job_id} already exists. Updating filename.")
            self._active_jobs[job_id]['label'].setText(filename)
            return

        row_index = self.dynamic_progress_layout.rowCount()

        # Filename Label
        label = QLabel(f"{filename}")
        label.setToolTip(filename) # Show full path on hover potentially
        self.dynamic_progress_layout.addWidget(label, row_index, 0) # Column 0

        # Progress Bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        self.dynamic_progress_layout.addWidget(progress_bar, row_index, 1) # Column 1

        # Cancel Button (visual only for now)
        cancel_button = QPushButton("Cancel")
        cancel_button.setToolTip(f"Cancel job {job_id}")
        # cancel_button.clicked.connect(lambda: self._request_specific_job_cancel(job_id)) # For future
        cancel_button.setEnabled(True) # Initially enabled
        self.dynamic_progress_layout.addWidget(cancel_button, row_index, 2) # Column 2

        # Store widgets in _active_jobs
        if job_id not in self._active_jobs: # Should have been created in _start_conversion_processes
             self._active_jobs[job_id] = {'filename': filename, 'status': 'running'} # Ensure it exists

        self._active_jobs[job_id]['label'] = label
        self._active_jobs[job_id]['progress_bar'] = progress_bar
        self._active_jobs[job_id]['cancel_button'] = cancel_button
        self._active_jobs[job_id]['row_index'] = row_index

        # Make sure the progress group box is visible if it's the first job row added
        if self.progress_group_box and not self.progress_group_box.isVisible():
            self.progress_group_box.setVisible(True)


    def _update_job_progress(self, job_id, percentage):
        if job_id in self._active_jobs and self._active_jobs[job_id].get('progress_bar'):
            self._active_jobs[job_id]['progress_bar'].setValue(percentage)
        else:
            self._log_warning(f"Could not update progress for job {job_id}: UI elements not found.")

    def _finalize_job_progress_row(self, job_id, success):
        if job_id in self._active_jobs:
            job_info = self._active_jobs[job_id]
            if job_info.get('label'):
                current_text = job_info['label'].text()
                status_prefix = "DONE: " if success else "FAILED: "
                job_info['label'].setText(f"{status_prefix}{current_text}")
                # Optionally change color
                # palette = job_info['label'].palette()
                # color = QColor("green") if success else QColor("red")
                # palette.setColor(job_info['label'].foregroundRole(), color)
                # job_info['label'].setPalette(palette)

            if job_info.get('progress_bar'):
                job_info['progress_bar'].setValue(100)

            if job_info.get('cancel_button'):
                job_info['cancel_button'].setEnabled(False)
                job_info['cancel_button'].setText("Finished")

            # Update overall progress bar
            if self.overall_progress_bar:
                self.overall_progress_bar.setValue(self.overall_progress_bar.value() + 1)

            # Remove UI elements for the completed job
            if job_info.get('label'):
                self.dynamic_progress_layout.removeWidget(job_info['label'])
                job_info['label'].deleteLater()
            if job_info.get('progress_bar'):
                self.dynamic_progress_layout.removeWidget(job_info['progress_bar'])
                job_info['progress_bar'].deleteLater()
            if job_info.get('cancel_button'):
                self.dynamic_progress_layout.removeWidget(job_info['cancel_button'])
                job_info['cancel_button'].deleteLater()

            # Remove the job from active_jobs dictionary after UI cleanup
            # self._active_jobs.pop(job_id, None) # Now handled by _check_all_jobs_complete or when it's truly done with the job
            # It's important that _check_all_jobs_complete still knows about this job to count it as 'completed'.
            # The job_info['status'] = 'completed' is the key for that.
            # We can clear the UI widget references from the job_info though.
            job_info['label'] = None
            job_info['progress_bar'] = None
            job_info['cancel_button'] = None

        else:
            self._log_warning(f"Could not finalize progress row for job {job_id}: UI elements not found in _active_jobs.")

    def _clear_dynamic_job_rows(self):
        if not self.dynamic_progress_layout:
            return
        while self.dynamic_progress_layout.count():
            item = self.dynamic_progress_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._active_jobs.clear()


    def _validate_conversion_setup(self):
        """Validate the conversion setup."""
        if not self.selected_media_type_details:
            QMessageBox.warning(self, "Setup Error", "Please select a valid job and media type.")
            return False

        job_output_ext_config = self.selected_media_type_details.get("output_ext", [])
        if job_output_ext_config and not self.selected_output_filter:
            QMessageBox.warning(self, "Setup Error", "Please select an output file type for this job.")
            return False

        return True

    def _get_selected_files_for_conversion(self):
        """Get the list of selected files for conversion."""
        selected_files_data = []
        current_active_input_exts = self.active_input_filters or set(
            self.selected_media_type_details.get("input_ext", []))

        for row_data in self.table_data:
            if row_data[COL_CHECK]:
                item_type = row_data[COL_TYPE].lower()
                if (not self.selected_media_type_details or 
                    not current_active_input_exts or 
                    item_type in current_active_input_exts):
                    selected_files_data.append(row_data)

        return selected_files_data

    def _validate_and_prepare_output_folder(self):
        """Validate and prepare the output folder."""
        output_folder = None
        requires_output_folder = self.selected_media_type_details.get("requires_output_folder", False)

        if (requires_output_folder and self.output_same_folder_checkbox and 
            not self.output_same_folder_checkbox.isChecked()):
            
            if self.output_folder_path_display:
                output_folder = self.output_folder_path_display.text().strip()
            
            if not output_folder:
                QMessageBox.warning(self, "Output Folder Missing",
                                  "Please select an output folder or choose 'Output in same folder'.")
                return False

            if not self._create_output_folder_if_needed(output_folder):
                return False

            if not self._check_disk_space(output_folder):
                return False

        return output_folder

    def _create_output_folder_if_needed(self, output_folder):
        """Create output folder if it doesn't exist."""
        if not os.path.isdir(output_folder):
            if not os.path.exists(output_folder):
                try:
                    os.makedirs(output_folder)
                    if self.log_output_text:
                        self.log_output_text.append(f"INFO: Created output directory: {output_folder}")
                except Exception as e:
                    QMessageBox.critical(self, "Output Folder Error", 
                                       f"Could not create output folder: {output_folder}\nError: {e}")
                    return False
            else:
                QMessageBox.critical(self, "Output Folder Error", 
                                   f"Specified output path is not a directory: {output_folder}")
                return False
        return True

    def _check_disk_space(self, output_folder):
        """Check available disk space."""
        estimated_min_gb = 0.1
        free_space_gb = utils.get_free_disk_space_gb(output_folder)
        
        if free_space_gb is not None and free_space_gb < estimated_min_gb:
            QMessageBox.critical(self, "Insufficient Disk Space",
                               f"Output location '{output_folder}' has less than {estimated_min_gb:.1f}GB free "
                               f"(approximately {free_space_gb:.2f}GB available). "
                               f"Please select another location or free up space.")
            return False
        elif free_space_gb is None:
            reply = QMessageBox.question(self, "Disk Space Unknown",
                                       "Could not determine free disk space for the output location. Continue anyway?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            return reply == QMessageBox.StandardButton.Yes
        
        return True

    def _start_conversion_processes(self, selected_files_data, output_folder):
        """Initialize ProcessPoolExecutor and add jobs to the queue."""
        if not self._process_pool_executor:
            # Ensure the executor is created with the current CONCURRENT_JOBS setting
            current_max_workers = config.settings.CONCURRENT_JOBS
            self._emit_or_print(f"INFO: Initializing ProcessPoolExecutor with max_workers = {current_max_workers}", fallback_color_code="cyan")
            self._process_pool_executor = concurrent.futures.ProcessPoolExecutor(
                max_workers=current_max_workers
            )
        # else:
            # TODO: Future: Consider if executor needs recreation if CONCURRENT_JOBS changed
            # since it was last created. For now, it's recreated if None.
            # The _handle_concurrent_jobs_changed method now handles shutting down the executor
            # if it exists and the setting changes, so this 'else' branch is less critical.

        if not self._results_timer.isActive():
            self._results_timer.start()

        primary_out_ext, secondary_out_ext = self._get_output_extensions()
        current_overwrite_files = (self.overwrite_files_checkbox.isChecked()
                                   if self.overwrite_files_checkbox else False)

        total_files_to_queue = len(selected_files_data)
        self._active_jobs.clear() # Clear from previous run
        self._job_id_counter = 0 # Reset job ID counter
        self._clear_dynamic_job_rows() # Clear UI rows from previous run


        # Setup UI for conversion (overall progress)
        self.set_ui_enabled_for_conversion(False)
        self._setup_progress_ui(total_files_to_queue) # This will need adjustment for individual jobs
        self._setup_log_visibility()
        if self.log_output_text: # Clear log from previous run
            self.log_output_text.clear()


        for file_data_row in selected_files_data:
            file_path = file_data_row[COL_PATH]
            self._job_id_counter += 1
            job_id = self._job_id_counter

            job_payload = {
                "job_id": job_id,
                "file_path": file_path,
                # "conversion_details_repr": repr(self.selected_media_type_details), # Not used currently
                "conversion_func_name": self.selected_media_type_details.get('conversion_func_name'),
                "output_folder_path": output_folder,
                "overwrite_files": current_overwrite_files,
                "selected_primary_output_ext": primary_out_ext,
                "selected_secondary_output_ext": secondary_out_ext,
                "config_settings_dict": config.settings.get_all_settings_for_sharing(), # Pass relevant settings
                "is_multi_file_job_type": any(ext in (self.selected_media_type_details.get("input_ext") or []) for ext in ['cue', 'gdi'])
            }
            self._job_queue.put(job_payload)
            self._active_jobs[job_id] = {
                'filename': os.path.basename(file_path),
                'status': 'queued',
                'progress_bar': None, # Will be created later
                'label': None # Will be created later
            }

        # Submit worker_task to the executor for each worker
        for _ in range(config.settings.CONCURRENT_JOBS):
            self._process_pool_executor.submit(
                process_worker_task, # This will be a new top-level function
                self._job_queue,
                self._results_queue
            )
        
        # Update overall progress label based on queued jobs
        if self.overall_label:
            self.overall_label.setText(f"Overall Progress (0/{total_files_to_queue} files queued)")
        if self.overall_progress_bar:
             self.overall_progress_bar.setMaximum(total_files_to_queue) # Each job is one unit for overall
             self.overall_progress_bar.setValue(0)


    def _get_output_extensions(self):
        """Get primary and secondary output extensions."""
        primary_out_ext = self.selected_output_filter
        secondary_out_ext = None

        possible_primary_outputs = self.selected_media_type_details.get("output_ext", [])
        possible_secondary_outputs = self.selected_media_type_details.get("output_ext_secondary")

        if primary_out_ext and isinstance(possible_primary_outputs, list) and primary_out_ext in possible_primary_outputs:
            idx = possible_primary_outputs.index(primary_out_ext)
            if isinstance(possible_secondary_outputs, list) and idx < len(possible_secondary_outputs):
                secondary_out_ext = possible_secondary_outputs[idx]
            elif isinstance(possible_secondary_outputs, str) and idx == 0:
                secondary_out_ext = possible_secondary_outputs

        return primary_out_ext, secondary_out_ext

    def _setup_progress_ui(self, total_files):
        """Setup the progress UI for conversion."""
        if self.progress_group_box:
            self.progress_group_box.setVisible(True)

        if self.overall_label:
            self.overall_label.setText(f"Overall Progress (0/{total_files} files)")
        
        if self.overall_progress_bar:
            self.overall_progress_bar.setMaximum(total_files) # Max is total number of jobs
            self.overall_progress_bar.setValue(0)

        # The old single file_label and file_progress_bar are hidden, so no need to set them up here.
        # Dynamic rows will handle individual job display.

        if self.overall_cancel_button: # Only overall cancel button is relevant at this stage
            self.overall_cancel_button.setEnabled(True)
        if self.file_cancel_button: # This one is for the old single file progress, should be hidden
            self.file_cancel_button.setEnabled(False)


        action_button_text = self.main_action_button.text() if self.main_action_button else "Job"
        if self.statusbar:
            self.statusbar.showMessage(f"Starting '{action_button_text}' for {total_files} file(s)...")

    def _setup_log_visibility(self):
        """Setup log visibility for conversion."""
        if self.log_output_text and not self.log_output_text.isVisible():
            if self.toggle_log_button:
                self.toggle_log_button.setChecked(True)
        
        if self.log_output_text:
            self.log_output_text.clear()

    # The _connect_worker_signals method has been removed as it was specific to the old QThread-based worker
    # and is not used with the ProcessPoolExecutor, which uses queues for communication.

    # Progress and completion handlers
    @Slot(int, int, str)
    def handle_overall_progress_update(self, current_step, total_steps, phase_description):
        """Handle overall progress updates."""
        if self.overall_progress_bar:
            self.overall_progress_bar.setMaximum(total_steps)
            self.overall_progress_bar.setValue(current_step)

        parts = phase_description.split(': ', 1)
        current_op_label = parts[0]
        current_filename_display = parts[1] if len(parts) > 1 else ""

        if self.overall_label:
            self.overall_label.setText(f"Overall: {phase_description} ({current_step}/{total_steps} stages)")
        
        if self.statusbar:
            self.statusbar.showMessage(f"Overall: {phase_description}")

        self._update_file_progress_for_operation(current_op_label, current_filename_display)

    def _update_file_progress_for_operation(self, operation, filename):
        """Update file progress based on current operation."""
        should_update_file_label = (
            "Preparing" in operation or "Copying" in operation or
            (self.file_label and (self.file_label.text() == "Current File: -" or
                                (filename and filename not in self.file_label.text())))
        )

        if should_update_file_label and self.file_label:
            self.file_label.setText(f"Current: {filename}")
            if self.file_progress_bar:
                self.file_progress_bar.setRange(0, 100)
                self.file_progress_bar.setValue(0)

        if self.file_progress_bar:
            progress_map = {
                "Preparing": 33,
                "Copying": 33,
                "Converting": 66,
                "Finalizing": 100,
                "File failed": 100,
                "Interrupted": 100
            }
            
            for key, value in progress_map.items():
                if key in operation:
                    self.file_progress_bar.setValue(value)
                    break

    @Slot(int)
    def handle_file_progress_update(self, percentage):
        """Handle file progress updates."""
        if self.file_progress_bar and percentage == 100:
            self.file_progress_bar.setValue(100)

    @Slot(str)
    def handle_critical_error(self, message):
        """Handle critical errors."""
        QMessageBox.critical(self, "Critical Conversion Error", message)
        self.set_ui_enabled_for_conversion(True)
        self.update_convert_button_state()
        if self.progress_group_box:
            self.progress_group_box.setVisible(False)

    @Slot(int, int)
    def handle_conversion_finished(self, success_count, fail_count):
        """Handle conversion completion."""
        total_attempted = success_count + fail_count
        status_msg = f"Job finished. Success: {success_count}, Failed: {fail_count} (Total attempted: {total_attempted})."
        
        if self.statusbar:
            self.statusbar.showMessage(status_msg)
        
        if self.log_output_text:
            # Reset character format to default before appending the summary
            cursor = self.log_output_text.textCursor()
            default_char_format = QTextCharFormat()
            # If you want to use the theme's default text color explicitly:
            # palette_default_color = self.log_output_text.palette().color(QPalette.ColorRole.Text)
            # default_char_format.setForeground(palette_default_color)
            cursor.setCharFormat(default_char_format)
            self.log_output_text.setTextCursor(cursor) # Apply the format change at current cursor position

            # Now append the message. It should use the default format.
            # The <b> tag will still apply boldness.
            self.log_output_text.append(f"\n<b>{status_msg}</b>")

        # Update progress bars to completion
        if self.overall_progress_bar:
            self.overall_progress_bar.setValue(self.overall_progress_bar.maximum())

        if self.file_label:
            self.file_label.setText("Finished.")
        
        if self.file_progress_bar:
            self.file_progress_bar.setValue(100 if total_attempted > 0 else 0)

        # Disable cancel buttons
        for button in [self.overall_cancel_button, self.file_cancel_button]:
            if button:
                button.setEnabled(False)

        # Re-enable UI and cleanup
        self.set_ui_enabled_for_conversion(True)
        # self.conversion_thread = None # Removed as it's no longer used
        self.update_convert_button_state()

    def set_ui_enabled_for_conversion(self, enabled):
        """Set UI enabled state for conversion."""
        # Widgets that should be disabled during conversion
        widgets_to_disable = [
            self.add_files_button, self.add_folder_button, self.recursive_checkbox,
            self.file_table, self.job_type_combo, self.output_same_folder_checkbox,
            self.delete_input_checkbox, self.overwrite_files_checkbox, self.actionSettings
        ]

        for widget in widgets_to_disable:
            if widget:
                widget.setEnabled(enabled)

        if enabled:
            self.update_ui_for_job_selection()
            if self.progress_group_box:
                self.progress_group_box.setVisible(False)
            self.update_convert_button_state()
        else:
            # Disable additional widgets during conversion
            conversion_disabled_widgets = [
                self.media_type_combo, self.select_input_types_button,
                self.select_output_type_button, self.output_folder_group_box,
                self.main_action_button
            ]
            
            for widget in conversion_disabled_widgets:
                if widget:
                    widget.setEnabled(False)

            if self.progress_group_box:
                self.progress_group_box.setVisible(True)
            
            for button in [self.overall_cancel_button, self.file_cancel_button]:
                if button:
                    button.setEnabled(True)

    # Log and UI utility methods
    @Slot(bool)
    def toggle_log_visibility(self, checked):
        """Toggle log visibility."""
        if self.log_output_text:
            self.log_output_text.setVisible(checked)
        
        if self.clear_log_button:
            self.clear_log_button.setVisible(checked)
        
        if self.toggle_log_button:
            self.toggle_log_button.setText("Hide Log ▲" if checked else "Show Log ▼")

    @Slot()
    def clear_log(self):
        """Clear the log text."""
        if self.log_output_text:
            self.log_output_text.clear()

    @Slot(str)
    def handle_output_update(self, message):
        """Handle output log updates by emitting plain (escaped) text."""
        self._emit_or_print(message) # No specific color, will use default

    @Slot(str)
    def handle_error_update(self, message):
        """Handle error log updates by emitting red (escaped) text."""
        self._emit_or_print(message, is_error=True) # is_error=True will make it red

    @Slot()
    def open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.ui)
        if dialog.exec():
            if self.statusbar:
                self.statusbar.showMessage("Settings updated and saved.")
            if self.delete_input_checkbox:
                self.delete_input_checkbox.setChecked(config.settings.DELETE_SOURCE_ON_SUCCESS)
        else:
            if self.statusbar:
                self.statusbar.showMessage("Settings dialog cancelled.")

    # Application lifecycle methods
    @Slot()
    def close_application(self):
        """Close the application."""
        print("DEBUG: close_application() called (e.g., from File > Exit).")
        self.close()

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        print("DEBUG: ConverterWindow.closeEvent() triggered.")
        app = QApplication.instance()

        jobs_are_active = False
        if self._process_pool_executor: # Check if executor exists
            # Check if job queue has pending items or if active_jobs has non-completed tasks
            if not self._job_queue.empty():
                jobs_are_active = True
            else:
                for job_id, job_info in self._active_jobs.items():
                    if job_info.get('status') != 'completed':
                        jobs_are_active = True
                        break

        if jobs_are_active:
            reply = QMessageBox.question(
                self, 'Confirm Exit',
                "Conversion jobs are currently active or queued. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                print("DEBUG: User confirmed exit during active/queued jobs.")
                self._request_conversion_stop() # Attempt to clear queue and signal stop
                self._shutdown_executor()       # Shutdown executor gracefully
                if self._results_timer.isActive():
                    self._results_timer.stop()
                event.accept()
                if app:
                    print("DEBUG: Calling app.quit() from closeEvent (jobs were active).")
                    app.quit() # Ensure app quits
            else:
                print("DEBUG: User cancelled exit during active/queued jobs.")
                event.ignore()
        else: # No jobs active or queued, or executor is already shutdown
            print("DEBUG: No active jobs, accepting close event.")
            # Ensure cleanup if executor exists but might not have been active
            if self._process_pool_executor: # Check if executor exists before trying to shut down
                self._request_conversion_stop() # Should be harmless if queue is empty
                self._shutdown_executor()
            if self._results_timer.isActive():
                self._results_timer.stop()
            event.accept()
            if app:
                print("DEBUG: Calling app.quit() from closeEvent (no jobs active).")
                app.quit() # Ensure app quits

    def eventFilter(self, watched_object, event):
        """Handle drag and drop events."""
        if watched_object is self.file_table:
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasUrls():
                    if self.statusbar:
                        self.statusbar.showMessage("Drop files/folders onto the table...", 2000)
                    event.acceptProposedAction()
                else:
                    if self.statusbar:
                        self.statusbar.showMessage("Drop ignored: Only files/folders accepted.", 2000)
                    event.ignore()
                return True

            elif event.type() == QEvent.Type.Drop:
                paths = []
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        if url.isLocalFile():
                            paths.append(url.toLocalFile())

                if paths:
                    self.process_added_paths(paths)
                    event.acceptProposedAction()
                    if self.statusbar:
                        self.statusbar.showMessage(f"{len(paths)} item(s) dropped.", 2000)
                else:
                    event.ignore()
                return True

        return super().eventFilter(watched_object, event)


def run_gui():
    """Run the GUI application."""
    print("DEBUG: Initializing QApplication in gui_main_window.run_gui()...")
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    # Set application icon
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))
        print(f"DEBUG: Application icon set from {ICON_PATH}")
    else:
        print(f"DEBUG: Application icon not found at {ICON_PATH}. Using default system icon.")

    print(f"DEBUG (gui_main_window): Config SUBPROCESS_TIMEOUT: {config.settings.SUBPROCESS_TIMEOUT}")

    print("DEBUG: Creating ConverterWindow instance...")
    window_wrapper = ConverterWindow()

    if window_wrapper.ui:
        print("DEBUG: Showing main window (window_wrapper.ui)...")
        window_wrapper.ui.show()

        print("DEBUG: Entering Qt event loop (app.exec())...")
        exit_code = app.exec()
        print(f"DEBUG: Qt event loop finished. app.exec() returned: {exit_code}")

        # Debug thread information
        active_threads = threading.enumerate()
        print(f"DEBUG: Active threads before sys.exit() ({len(active_threads)}):")
        for thread_item in active_threads:
            print(f"  - Name: {thread_item.name}, Daemon: {thread_item.daemon}, Alive: {thread_item.is_alive()}")
            if (thread_item != threading.main_thread() and 
                thread_item.is_alive() and not thread_item.daemon):
                print(f"WARNING: Non-daemon thread '{thread_item.name}' is still alive. "
                     f"Python might hang if not handled.")

        print(f"DEBUG: Calling sys.exit({exit_code}). Python process should terminate if all non-daemon threads are done.")
        sys.exit(exit_code)
    else:
        print("DEBUG: Exiting due to UI load failure in ConverterWindow initialization.")
        sys.exit(-1)