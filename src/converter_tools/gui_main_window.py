# converter_tools/gui_main_window.py

import sys
import os
import traceback
import time
import json
import multiprocessing
import threading

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QComboBox, QLabel, QTextEdit, QSizePolicy, QSpacerItem, QMenuBar,
        QFileDialog, QMessageBox, QStatusBar, QDialog, QDialogButtonBox,
        QLineEdit, QSpinBox, QGroupBox, QMenu, QProgressBar
    )
    from PySide6.QtGui import QAction, QKeySequence, QColor, QPalette, QCloseEvent, QIcon
    from PySide6.QtCore import Qt, Slot, Signal, QPoint
    from PySide6.QtUiTools import QUiLoader
    # QMenu is already imported from PySide6.QtWidgets
    # QAction is already imported from PySide6.QtGui
    from .gui_m3u_creator import M3UCreatorWindow
except ImportError as e:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app_exists = QApplication.instance()
        if not app_exists:
            temp_app = QApplication([])
        QMessageBox.critical(
            None, "Fatal Error", f"PySide6 is not installed or found for gui_main_window.py: {e}")
    except Exception:
        print(
            f"FATAL ERROR (gui_main_window.py): PySide6 not found, and QMessageBox fallback failed. {e}")
    sys.exit(1)

# Core application modules
from . import config
from . import utils
from . import conversions
from . import menu_definitions

# GUI components from other files in this package
from .gui_settings import SettingsDialog
from .gui_worker import ConversionWorker, N_STAGES_PER_FILE

# Constants for table columns
COL_CHECK = 0
COL_PATH = 1
COL_TYPE = 2
TABLE_HEADINGS = ['✓', 'File Path', 'Type']


class ConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        app_instance = QApplication.instance()
        if not app_instance:
            print(
                "Warning: QApplication instance not found during ConverterWindow init. Creating one.")
            app_instance = QApplication(sys.argv)

        if app_instance:
            app_instance.setQuitOnLastWindowClosed(True)
            app_instance.aboutToQuit.connect(self._on_about_to_quit)

        main_ui_file_path = os.path.join(os.path.dirname(
            __file__), "assets", "qt", "main_window.ui")
        if not os.path.exists(main_ui_file_path):
            QMessageBox.critical(
                self, "Fatal Error", f"Main UI file not found: {main_ui_file_path}")
            if app_instance:
                app_instance.quit()
            else:
                sys.exit(-1)
            return

        loader = QUiLoader()
        self.ui = loader.load(main_ui_file_path, self)
        if not self.ui:
            QMessageBox.critical(self, "Fatal UI Load Error",
                                 f"Could not load main_window.ui: {loader.errorString()}")
            if app_instance:
                app_instance.quit()
            else:
                sys.exit(-1)
            return

        self.ui.setAttribute(Qt.WA_DeleteOnClose, True)

        # --- Find UI Elements ---
        self.job_type_combo = self.ui.findChild(QComboBox, "job_type_combo")
        self.media_type_combo = self.ui.findChild(QComboBox, "media_type_combo")
        self.add_files_button = self.ui.findChild(QPushButton, "add_files_button")
        self.add_folder_button = self.ui.findChild(QPushButton, "add_folder_button")
        self.recursive_checkbox = self.ui.findChild(QCheckBox, "recursive_checkbox")
        self.input_file_types_label = self.ui.findChild(QLabel, "input_file_types_label")
        self.select_input_types_button = self.ui.findChild(QPushButton, "select_input_types_button")
        self.file_table = self.ui.findChild(QTableWidget, "file_table")

        self.output_folder_group_box = self.ui.findChild(QGroupBox, "output_folder_group_box")
        self.select_output_folder_button = self.ui.findChild(QPushButton, "select_output_folder_button")
        self.output_folder_path_display = self.ui.findChild(QLineEdit, "output_folder_path_display")
        self.output_file_types_label = self.ui.findChild(QLabel, "output_file_types_label")
        self.select_output_type_button = self.ui.findChild(QPushButton, "select_output_type_button")

        self.overwrite_files_checkbox = self.ui.findChild(QCheckBox, "overwrite_files_checkbox")
        self.delete_input_checkbox = self.ui.findChild(QCheckBox, "delete_input_checkbox") 
        self.output_same_folder_checkbox = self.ui.findChild(QCheckBox, "output_same_folder_checkbox")

        self.main_action_button = self.ui.findChild(QPushButton, "main_action_button")
        self.toggle_log_button = self.ui.findChild(QPushButton, "toggle_log_button")
        self.clear_log_button = self.ui.findChild(QPushButton, "clear_log_button")
        self.log_output_text = self.ui.findChild(QTextEdit, "log_output_text")

        self.statusbar = self.ui.statusBar() if hasattr(self.ui, 'statusBar') and self.ui.statusBar() else QStatusBar(self.ui)
        if not (hasattr(self.ui, 'statusBar') and self.ui.statusBar()): 
             if isinstance(self.ui.layout(), QVBoxLayout): self.ui.layout().addWidget(self.statusbar)

        self.actionSettings = self.ui.findChild(QAction, "actionSettings")
        self.actionExit = self.ui.findChild(QAction, "actionExit")

        self.progress_group_box = self.ui.findChild(
            QGroupBox, "progress_group_box")
        self.overall_label = self.ui.findChild(QLabel, "overall_label")
        self.overall_progress_bar = self.ui.findChild(
            QProgressBar, "overall_progress_bar")
        self.overall_cancel_button = self.ui.findChild(
            QPushButton, "overall_cancel_button")
        self.file_label = self.ui.findChild(QLabel, "file_label")
        self.file_progress_bar = self.ui.findChild(
            QProgressBar, "file_progress_bar")
        self.file_cancel_button = self.ui.findChild(
            QPushButton, "file_cancel_button")

        critical_main_widget_names = [
            "job_type_combo", "media_type_combo", "add_files_button", "file_table",
            "output_folder_group_box", "main_action_button", "log_output_text",
            "actionSettings", "actionExit",
            "progress_group_box", "overall_label", "overall_progress_bar",
            "overall_cancel_button", "file_label", "file_progress_bar", "file_cancel_button"
        ]
        for name in critical_main_widget_names:
            widget = getattr(self, name, None)
            if widget is None:
                QMessageBox.critical(self, "Main UI Element Error",
                                     f"UI element '{name}' not found in main_window.ui. "
                                     "Please check objectName in Qt Designer.")
                if app_instance:
                    app_instance.quit()
                else:
                    sys.exit(-1)
                return

        # --- Initialize UI States ---
        if self.progress_group_box:
            self.progress_group_box.setVisible(False)
        if self.overall_progress_bar:
            self.overall_progress_bar.setValue(0)
        if self.file_progress_bar:
            self.file_progress_bar.setValue(0)
        if self.overall_label:
            self.overall_label.setText("Overall Progress:")
        if self.file_label:
            self.file_label.setText("Current File:")

        if self.file_table:
            self.file_table.setHorizontalHeaderLabels(TABLE_HEADINGS)
            header = self.file_table.horizontalHeader()
            header.setSectionResizeMode(
                COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(
                COL_PATH, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(
                COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
            header.setStyleSheet(
                "QHeaderView::section { padding-left: 4px; padding-right: 4px; }")
            self.file_table.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu)
            self.file_table.customContextMenuRequested.connect(
                self._show_file_table_context_menu)
            self.file_table.cellClicked.connect(self.handle_cell_click)

        # --- Connect Signals and Slots ---
        if self.job_type_combo:
            self.job_type_combo.currentTextChanged.connect(
                self._on_job_type_changed)
        if self.media_type_combo:
            self.media_type_combo.currentTextChanged.connect(
                self._on_media_type_changed)
        if self.add_files_button:
            self.add_files_button.clicked.connect(self.add_files)
        if self.add_folder_button:
            self.add_folder_button.clicked.connect(self.add_folder)
        if self.select_input_types_button:
            self.select_input_types_button.clicked.connect(
                self._on_select_input_types_clicked)

        if self.select_output_folder_button:
            self.select_output_folder_button.clicked.connect(
                self._on_select_output_folder_clicked)
        if self.select_output_type_button:
            self.select_output_type_button.clicked.connect(
                self._on_select_output_type_clicked)
        if self.output_same_folder_checkbox:
            self.output_same_folder_checkbox.toggled.connect(
                self._on_output_same_folder_toggled)
        if self.delete_input_checkbox:
            self.delete_input_checkbox.toggled.connect(
                self._on_delete_input_toggled)

        if self.main_action_button:
            self.main_action_button.clicked.connect(self.start_conversion)
        if self.toggle_log_button:
            self.toggle_log_button.toggled.connect(self.toggle_log_visibility)
        if self.clear_log_button:
            self.clear_log_button.clicked.connect(self.clear_log)

        if self.actionSettings:
            self.actionSettings.triggered.connect(self.open_settings)
        if self.actionExit:
            self.actionExit.triggered.connect(self.close_application)

        if self.overall_cancel_button:
            self.overall_cancel_button.clicked.connect(
                self._request_conversion_stop)
        if self.file_cancel_button:
            self.file_cancel_button.clicked.connect(
                self._request_conversion_stop)

        # --- Initialize Member Variables ---
        self.conversion_thread = None
        self.table_data = []
        self.selected_job_details = None
        self.selected_media_type_details = None
        self.active_input_filters = set()
        self.selected_output_filter = None

        # --- Initial UI Setup ---
        self._populate_job_types()
        if self.delete_input_checkbox:
            self.delete_input_checkbox.setChecked(
                config.settings.DELETE_SOURCE_ON_SUCCESS)
        if self.output_same_folder_checkbox:
            self._on_output_same_folder_toggled(
                self.output_same_folder_checkbox.isChecked())

        self.update_ui_for_job_selection()
        if self.statusbar:
            self.statusbar.showMessage("Ready. Select a job type to begin.")

        # --- Begin M3U Creator Integration ---
        if hasattr(self, 'ui') and self.ui is not None and hasattr(self.ui, 'menuBar'):
            main_menubar = self.ui.menuBar() # Use self.ui.menuBar()

            tools_menu = None
            # Iterate through existing top-level menu actions to find "Tools" menu
            for action_iter_menu_find in main_menubar.actions(): # Renamed loop variable for clarity
                menu_candidate = action_iter_menu_find.menu()
                if menu_candidate and menu_candidate.title() == "&Tools":
                    tools_menu = menu_candidate
                    break

            if tools_menu is None: # If not found, create it
                tools_menu = main_menubar.addMenu("&Tools")

            # Create and add the M3U Creator action
            # Parent action to self.ui (the main QMainWindow object from .ui file)
            self.actionM3UPlaylistCreator = QAction("M3U Playlist Creator...", self.ui)
            self.actionM3UPlaylistCreator.setObjectName("actionM3UPlaylistCreator")
            self.actionM3UPlaylistCreator.triggered.connect(self._open_m3u_creator)
            tools_menu.addAction(self.actionM3UPlaylistCreator)
        else:
            # This else block is for debugging if the menu bar isn't found as expected.
            if hasattr(self, 'log_output_text') and self.log_output_text:
                self.log_output_text.append("<font color='orange'>Warning: Could not find menuBar on self.ui to add Tools menu for M3U Creator.</font>")
            else:
                print("DEBUG: Could not find menuBar on self.ui to add Tools menu for M3U Creator.", file=sys.stderr)
        # --- End M3U Creator Integration ---

        self.ui.setWindowTitle("Converter Tool")

    @Slot()
    def _open_m3u_creator(self):
        # Determine the correct parent: self.ui if it's the main widget from loader, otherwise self (QMainWindow)
        parent_widget = self.ui if hasattr(self, 'ui') and self.ui is not None else self
        try:
            # M3UCreatorWindow's __init__ handles its own UI file loading by default
            dialog = M3UCreatorWindow(parent=parent_widget)
            dialog.exec() # Show as modal dialog
        except Exception as e:
            error_message = f"Could not open M3U Playlist Creator: {e}"
            # Log to main window's log if available
            if hasattr(self, 'log_output_text') and self.log_output_text:
                self.log_output_text.append(f"<font color='red'>ERROR: {error_message}</font>")
            else:
                print(f"ERROR: {error_message}", file=sys.stderr)
            # Also show a QMessageBox to the user
            # Determine parent for QMessageBox carefully
            parent_for_msgbox = self.ui if hasattr(self, 'ui') and self.ui is not None and isinstance(self.ui, QWidget) else self
            if not isinstance(parent_for_msgbox, QWidget): # Final fallback if self.ui is not a QWidget
                parent_for_msgbox = None
            QMessageBox.critical(parent_for_msgbox, "M3U Creator Error", error_message)

    def _ensure_thread_stopped(self):
        """Ensures the conversion thread is properly stopped."""
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.request_stop()
            # Wait with a timeout for thread to finish
            if not self.conversion_thread.wait(3000):  # 3-second timeout
                self._emit_or_print("WARNING: Conversion thread did not stop gracefully, forcing termination.",
                                    fallback_color_code="yellow")
                self.conversion_thread.terminate()  # Force termination as last resort
            self.conversion_thread = None

    @Slot()
    def _on_about_to_quit(self):
        print("DEBUG: QApplication.aboutToQuit signal received in ConverterWindow.")
        self._ensure_thread_stopped()
        if self.conversion_thread and self.conversion_thread.isRunning():
            print("DEBUG: Conversion thread is running, requesting stop during app quit.")
            self.conversion_thread.request_stop()
            if not self.conversion_thread.wait(2000):
                print(
                    "DEBUG: Conversion thread did not stop gracefully after 2s in aboutToQuit.")
            else:
                print("DEBUG: Conversion thread stopped gracefully in aboutToQuit.")
        else:
            print("DEBUG: No conversion thread running or thread is None in aboutToQuit.")
        print("DEBUG: Exiting _on_about_to_quit in ConverterWindow.")

    @Slot()
    def _request_conversion_stop(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.request_stop()
            if self.overall_cancel_button:
                self.overall_cancel_button.setEnabled(False)
            if self.file_cancel_button:
                self.file_cancel_button.setEnabled(False)
            if self.statusbar:
                self.statusbar.showMessage("Cancellation requested...")

    @Slot()
    def start_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            QMessageBox.warning(
                self, "Busy", "A conversion is already in progress.")
            return
        if not self.selected_media_type_details:
            QMessageBox.warning(self, "Setup Error",
                                "Please select a valid job and media type.")
            return

        job_output_ext_config = self.selected_media_type_details.get(
            "output_ext", [])
        if job_output_ext_config and not self.selected_output_filter:
            QMessageBox.warning(
                self, "Setup Error", "Please select an output file type for this job.")
            return

        selected_files_data = []
        for i, row_data in enumerate(self.table_data):
            if row_data[COL_CHECK]:
                item_type_in_table = row_data[COL_TYPE].lower()
                current_active_input_exts = self.active_input_filters
                if not current_active_input_exts and self.selected_media_type_details:
                    current_active_input_exts = set(
                        self.selected_media_type_details.get("input_ext", []))

                if not self.selected_media_type_details or \
                   not current_active_input_exts or \
                   item_type_in_table in current_active_input_exts:
                    selected_files_data.append(row_data)

        if not selected_files_data:
            QMessageBox.warning(
                self, "No Files", "No files selected for conversion (or none match current input filters).")
            return

        total_files_to_process = len(selected_files_data)
        selected_file_paths = [data[COL_PATH] for data in selected_files_data]

        output_folder = None
        job_requires_output_folder_ui_section = self.selected_media_type_details.get(
            "requires_output_folder", False)

        if job_requires_output_folder_ui_section and self.output_same_folder_checkbox and not self.output_same_folder_checkbox.isChecked():
            if self.output_folder_path_display:
                output_folder = self.output_folder_path_display.text().strip()
            if not output_folder:
                QMessageBox.warning(self, "Output Folder Missing",
                                    "Please select an output folder or choose 'Output in same folder'.")
                return
            if not os.path.isdir(output_folder):
                if not os.path.exists(output_folder):
                    try:
                        os.makedirs(output_folder)
                        if self.log_output_text:
                            self.log_output_text.append(
                                f"INFO: Created output directory: {output_folder}")
                    except Exception as e:
                        QMessageBox.critical(
                            self, "Output Folder Error", f"Could not create output folder: {output_folder}\nError: {e}")
                        return
                else:
                    QMessageBox.critical(
                        self, "Output Folder Error", f"Specified output path is not a directory: {output_folder}")
                    return

            estimated_min_gb = 0.1
            free_space_gb = utils.get_free_disk_space_gb(output_folder)
            if free_space_gb is not None and free_space_gb < estimated_min_gb:
                QMessageBox.critical(self, "Insufficient Disk Space",
                                     f"Output location '{output_folder}' has less than {estimated_min_gb:.1f}GB free "
                                     f"(approximately {free_space_gb:.2f}GB available). Please select another location or free up space.")
                return
            elif free_space_gb is None:
                if QMessageBox.question(self, "Disk Space Unknown",
                                        "Could not determine free disk space for the output location. Continue anyway?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
                    return

        primary_out_ext = self.selected_output_filter
        secondary_out_ext = None

        possible_primary_outputs = self.selected_media_type_details.get(
            "output_ext", [])
        possible_secondary_outputs = self.selected_media_type_details.get(
            "output_ext_secondary")

        if primary_out_ext and isinstance(possible_primary_outputs, list) and primary_out_ext in possible_primary_outputs:
            idx = possible_primary_outputs.index(primary_out_ext)
            if isinstance(possible_secondary_outputs, list) and idx < len(possible_secondary_outputs):
                secondary_out_ext = possible_secondary_outputs[idx]
            elif isinstance(possible_secondary_outputs, str) and idx == 0:
                secondary_out_ext = possible_secondary_outputs

        current_overwrite_files = self.overwrite_files_checkbox.isChecked(
        ) if self.overwrite_files_checkbox else False

        self.set_ui_enabled_for_conversion(False)

        if self.progress_group_box:
            self.progress_group_box.setVisible(True)

        if self.overall_label:
            self.overall_label.setText(
                f"Overall Progress (0/{total_files_to_process} files)")
        if self.overall_progress_bar:
            self.overall_progress_bar.setMaximum(
                total_files_to_process * N_STAGES_PER_FILE)
            self.overall_progress_bar.setValue(0)

        if self.file_label:
            self.file_label.setText("Current File: -")
        if self.file_progress_bar:
            self.file_progress_bar.setRange(0, 100)
            self.file_progress_bar.setValue(0)

        if self.overall_cancel_button:
            self.overall_cancel_button.setEnabled(True)
        if self.file_cancel_button:
            self.file_cancel_button.setEnabled(True)

        action_button_text = self.main_action_button.text(
        ) if self.main_action_button else "Job"
        if self.statusbar:
            self.statusbar.showMessage(
                f"Starting '{action_button_text}' for {total_files_to_process} file(s)...")

        if self.log_output_text and not self.log_output_text.isVisible():
            if self.toggle_log_button:
                self.toggle_log_button.setChecked(True)
        if self.log_output_text:
            self.log_output_text.clear()

        self.conversion_thread = ConversionWorker(
            selected_file_paths, self.selected_media_type_details,
            output_folder, current_overwrite_files,
            primary_out_ext, secondary_out_ext
        )
        self.conversion_thread.status_update.connect(
            self.handle_overall_progress_update)
        self.conversion_thread.file_progress_update.connect(
            self.handle_file_progress_update)
        self.conversion_thread.output_update.connect(self.handle_output_update)
        self.conversion_thread.error_update.connect(self.handle_error_update)
        self.conversion_thread.critical_error_occurred.connect(
            self.handle_critical_error)
        self.conversion_thread.finished.connect(
            self.handle_conversion_finished)
        self.conversion_thread.start()

    @Slot(str)
    def handle_critical_error(self, message):
        QMessageBox.critical(self, "Critical Conversion Error", message)
        self.set_ui_enabled_for_conversion(True)
        self.update_convert_button_state()
        if self.progress_group_box:
            self.progress_group_box.setVisible(False)

    @Slot(int, int, str)
    def handle_overall_progress_update(self, current_overall_step, total_overall_steps, phase_description):
        if self.overall_progress_bar:
            self.overall_progress_bar.setMaximum(total_overall_steps)
            self.overall_progress_bar.setValue(current_overall_step)

        parts = phase_description.split(': ', 1)
        current_op_label = parts[0]
        current_filename_display = parts[1] if len(parts) > 1 else ""

        if self.overall_label:
            self.overall_label.setText(
                f"Overall: {phase_description} ({current_overall_step}/{total_overall_steps} stages)")
        if self.statusbar:
            self.statusbar.showMessage(f"Overall: {phase_description}")

        if "Preparing" in current_op_label or "Copying" in current_op_label or \
           (self.file_label and (self.file_label.text() == "Current File: -" or
                                 (current_filename_display and current_filename_display not in self.file_label.text()))):
            if self.file_label:
                self.file_label.setText(f"Current: {current_filename_display}")
            if self.file_progress_bar:
                self.file_progress_bar.setRange(0, 100)
                self.file_progress_bar.setValue(0)

        if self.file_progress_bar:
            if "Preparing" in current_op_label or "Copying" in current_op_label:
                self.file_progress_bar.setValue(33)
            elif "Converting" in current_op_label:
                self.file_progress_bar.setValue(66)
            elif "Finalizing" in current_op_label or "File failed" in current_op_label or "Interrupted" in current_op_label:
                self.file_progress_bar.setValue(100)

    @Slot(int)
    def handle_file_progress_update(self, percentage):
        if self.file_progress_bar:
            if percentage == 100:
                self.file_progress_bar.setValue(100)

    @Slot(int, int)
    def handle_conversion_finished(self, success_count, fail_count):
        total_attempted = success_count + fail_count
        status_msg = f"Job finished. Success: {success_count}, Failed: {fail_count} (Total attempted: {total_attempted})."
        if self.statusbar:
            self.statusbar.showMessage(status_msg)
        if self.log_output_text:
            self.log_output_text.append(f"\n<b>{status_msg}</b>")

        if self.overall_progress_bar:
            self.overall_progress_bar.setValue(
                self.overall_progress_bar.maximum())

        if self.file_label:
            self.file_label.setText("Finished.")
        if self.file_progress_bar:
            self.file_progress_bar.setValue(100 if total_attempted > 0 else 0)

        if self.overall_cancel_button:
            self.overall_cancel_button.setEnabled(False)
        if self.file_cancel_button:
            self.file_cancel_button.setEnabled(False)

        self.set_ui_enabled_for_conversion(True)
        self.conversion_thread = None
        self.update_convert_button_state()

    def set_ui_enabled_for_conversion(self, enabled):
        if self.add_files_button:
            self.add_files_button.setEnabled(enabled)
        if self.add_folder_button:
            self.add_folder_button.setEnabled(enabled)
        if self.recursive_checkbox:
            self.recursive_checkbox.setEnabled(enabled)
        if self.file_table:
            self.file_table.setEnabled(enabled)
        if self.job_type_combo:
            self.job_type_combo.setEnabled(enabled)
        if self.output_same_folder_checkbox:
            self.output_same_folder_checkbox.setEnabled(enabled)
        if self.delete_input_checkbox:
            self.delete_input_checkbox.setEnabled(enabled)
        if self.overwrite_files_checkbox:
            self.overwrite_files_checkbox.setEnabled(enabled)
        if self.actionSettings:
            self.actionSettings.setEnabled(enabled)

        if enabled:
            self.update_ui_for_job_selection()
            if self.progress_group_box:
                self.progress_group_box.setVisible(False)
            self.update_convert_button_state()
        else:
            if self.media_type_combo:
                self.media_type_combo.setEnabled(False)
            if self.select_input_types_button:
                self.select_input_types_button.setEnabled(False)
            if self.select_output_type_button:
                self.select_output_type_button.setEnabled(False)
            if self.output_folder_group_box:
                self.output_folder_group_box.setEnabled(False)
            if self.main_action_button:
                self.main_action_button.setEnabled(False)

            if self.progress_group_box:
                self.progress_group_box.setVisible(True)
            if self.overall_cancel_button:
                self.overall_cancel_button.setEnabled(True)
            if self.file_cancel_button:
                self.file_cancel_button.setEnabled(True)

    def _populate_job_types(self):
        if not self.job_type_combo:
            return
        self.job_type_combo.blockSignals(True)
        self.job_type_combo.clear()
        self.job_type_combo.addItem("(Select Job Type)")
        for job in menu_definitions.JOB_DEFINITIONS:
            self.job_type_combo.addItem(job["job_name"])
        self.job_type_combo.blockSignals(False)
        self.job_type_combo.setCurrentIndex(0)

    @Slot(bool)
    def _on_output_same_folder_toggled(self, checked):
        show_custom_output_widgets = not checked
        if self.select_output_folder_button:
            self.select_output_folder_button.setVisible(
                show_custom_output_widgets)
        if self.output_folder_path_display:
            self.output_folder_path_display.setVisible(
                show_custom_output_widgets)

        if checked and self.output_folder_path_display:
            self.output_folder_path_display.clear()
        self.update_convert_button_state()

    @Slot(bool)
    def _on_delete_input_toggled(self, checked):
        config.settings.DELETE_SOURCE_ON_SUCCESS = checked
        if self.statusbar:
            self.statusbar.showMessage(
                f"Delete input files on success: {'Enabled' if checked else 'Disabled'}")

    @Slot(str)
    def _on_job_type_changed(self, selected_job_name):
        if not self.media_type_combo:
            return
        self.media_type_combo.blockSignals(True)
        self.media_type_combo.clear()
        self.media_type_combo.addItem("(Select Media Type)")

        self.selected_job_details = None
        self.selected_media_type_details = None
        self.active_input_filters.clear()
        self.selected_output_filter = None

        if selected_job_name and selected_job_name != "(Select Job Type)":
            for job_def in menu_definitions.JOB_DEFINITIONS:
                if job_def["job_name"] == selected_job_name:
                    self.selected_job_details = job_def
                    for media_type in job_def.get("media_types", []):
                        self.media_type_combo.addItem(media_type["media_name"])
                    break

        self.media_type_combo.blockSignals(False)
        self.media_type_combo.setCurrentIndex(0)
        self.update_ui_for_job_selection()
        if self.statusbar:
            self.statusbar.showMessage(
                f"Job type '{selected_job_name}' selected. Now select a media type.")

    @Slot(str)
    def _on_media_type_changed(self, selected_media_name):
        self.selected_media_type_details = None
        self.active_input_filters.clear()
        self.selected_output_filter = None

        if self.selected_job_details and selected_media_name and selected_media_name != "(Select Media Type)":
            for media_def in self.selected_job_details.get("media_types", []):
                if media_def["media_name"] == selected_media_name:
                    self.selected_media_type_details = media_def
                    self.active_input_filters = set(
                        self.selected_media_type_details.get("input_ext", []))
                    output_exts = self.selected_media_type_details.get(
                        "output_ext", [])
                    if output_exts:
                        if isinstance(output_exts, list) and len(output_exts) == 1 and output_exts[0]:
                            self.selected_output_filter = output_exts[0]
                        elif isinstance(output_exts, str):
                            self.selected_output_filter = output_exts
                    break

        self.update_ui_for_media_selection()

    def update_ui_for_job_selection(self):
        job_is_selected = bool(self.selected_job_details)
        if self.media_type_combo:
            self.media_type_combo.setEnabled(job_is_selected)

        if not job_is_selected:
            self.selected_media_type_details = None
            self.active_input_filters.clear()
            self.selected_output_filter = None

        self.update_ui_for_media_selection()

    def update_ui_for_media_selection(self):
        media_is_selected = bool(self.selected_media_type_details)

        action_text = "START JOB"
        input_ext_str = "N/A"
        output_ext_str = "N/A"
        requires_output_folder_ui_section = False
        can_select_output_type = False

        if self.selected_job_details:
            action_text = self.selected_job_details.get(
                "action_text", "START JOB").upper()

        if media_is_selected and self.selected_media_type_details:
            action_text = self.selected_media_type_details.get(
                "action_text", action_text).upper()

            current_display_input_exts = self.active_input_filters
            if not current_display_input_exts:
                current_display_input_exts = set(
                    self.selected_media_type_details.get("input_ext", []))
            input_ext_str = ", ".join([f".{ext}" for ext in sorted(
                list(current_display_input_exts))]) if current_display_input_exts else "Any"

            possible_output_exts = self.selected_media_type_details.get(
                "output_ext", [])
            if self.selected_output_filter:
                output_ext_str = f".{self.selected_output_filter}"
            elif not possible_output_exts:
                output_ext_str = "N/A (Folder/Info)" if not self.selected_media_type_details.get(
                    "requires_output_folder", False) else "Folder"
            elif possible_output_exts and not self.selected_output_filter:
                output_ext_str = "(Select Output)"

            if isinstance(possible_output_exts, list) and len(possible_output_exts) > 1:
                can_select_output_type = True
            elif isinstance(possible_output_exts, list) and len(possible_output_exts) == 1 and possible_output_exts[0]:
                can_select_output_type = False
            elif isinstance(possible_output_exts, str) and possible_output_exts:
                can_select_output_type = False
            elif not possible_output_exts:
                can_select_output_type = False

            requires_output_folder_ui_section = self.selected_media_type_details.get(
                "requires_output_folder", False)

        if self.main_action_button:
            self.main_action_button.setText(action_text)
        if self.input_file_types_label:
            self.input_file_types_label.setText(f"Input: {input_ext_str}")
        if self.output_file_types_label:
            self.output_file_types_label.setText(f"Output: {output_ext_str}")

        can_select_input_types = media_is_selected and bool(self.selected_media_type_details.get(
            "input_ext") if self.selected_media_type_details else False)
        if self.select_input_types_button:
            self.select_input_types_button.setEnabled(can_select_input_types)

        if self.select_output_type_button:
            self.select_output_type_button.setEnabled(can_select_output_type)

        if self.output_folder_group_box:
            self.output_folder_group_box.setEnabled(
                requires_output_folder_ui_section)

        output_in_same_folder = self.output_same_folder_checkbox.isChecked(
        ) if self.output_same_folder_checkbox else True
        show_custom_output_path_widgets = requires_output_folder_ui_section and not output_in_same_folder

        if self.select_output_folder_button:
            self.select_output_folder_button.setVisible(
                show_custom_output_path_widgets)
        if self.output_folder_path_display:
            self.output_folder_path_display.setVisible(
                show_custom_output_path_widgets)

        if not requires_output_folder_ui_section or output_in_same_folder:
            if self.output_folder_path_display:
                self.output_folder_path_display.clear()

        self._apply_filter_to_table()
        self.update_convert_button_state()

    @Slot()
    def _on_select_input_types_clicked(self):
        if not self.selected_media_type_details:
            if self.statusbar:
                self.statusbar.showMessage(
                    "Please select a job and media type first.", 3000)
            return

        possible_input_exts = self.selected_media_type_details.get(
            "input_ext", [])
        if not possible_input_exts:
            if self.statusbar:
                self.statusbar.showMessage(
                    "No specific input types to filter for this selection.", 3000)
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
        if checked:
            self.active_input_filters.add(extension)
        else:
            self.active_input_filters.discard(extension)

        active_filter_display_list = sorted(list(self.active_input_filters))
        if self.input_file_types_label:
            if active_filter_display_list:
                self.input_file_types_label.setText(
                    f"Input: {', '.join(['.' + ext for ext in active_filter_display_list])}")
            elif self.selected_media_type_details:
                all_media_exts = self.selected_media_type_details.get(
                    "input_ext", [])
                self.input_file_types_label.setText(
                    f"Input: {', '.join(['.' + ext for ext in all_media_exts]) if all_media_exts else 'Any'}")
            else:
                self.input_file_types_label.setText("Input: N/A")

        if self.statusbar:
            self.statusbar.showMessage(
                f"Input filter updated. Active: {', '.join(active_filter_display_list) if active_filter_display_list else 'None (showing all for media type)'}", 3000)
        self._apply_filter_to_table()
        self.update_convert_button_state()

    @Slot()
    def _on_select_output_type_clicked(self):
        if not self.selected_media_type_details:
            if self.statusbar:
                self.statusbar.showMessage(
                    "Please select a media type first.", 3000)
            return

        possible_output_exts = self.selected_media_type_details.get(
            "output_ext", [])
        if not isinstance(possible_output_exts, list) or not possible_output_exts:
            if self.statusbar:
                self.statusbar.showMessage(
                    "No selectable output types for this media.", 3000)
            return

        menu = QMenu(self)
        for ext_string in possible_output_exts:
            if not ext_string:
                continue
            action = QAction(f".{ext_string}", self)
            action.setCheckable(True)
            action.setChecked(ext_string == self.selected_output_filter)
            action.triggered.connect(
                lambda checked_status=False, bound_ext_string=ext_string: self._on_output_filter_type_selected(bound_ext_string))
            menu.addAction(action)

        if self.select_output_type_button:
            button_pos = self.select_output_type_button.mapToGlobal(
                QPoint(0, self.select_output_type_button.height()))
            menu.exec(button_pos)

    @Slot(str)
    def _on_output_filter_type_selected(self, extension):
        self.selected_output_filter = extension
        if self.output_file_types_label:
            self.output_file_types_label.setText(f"Output: .{extension}")
        if self.statusbar:
            self.statusbar.showMessage(
                f"Output type set to: .{extension}", 3000)
        self.update_convert_button_state()

    def _apply_filter_to_table(self):
        if not self.file_table:
            return

        visible_exts_for_current_selection = self.active_input_filters
        if not visible_exts_for_current_selection and self.selected_media_type_details:
            visible_exts_for_current_selection = set(
                self.selected_media_type_details.get("input_ext", []))

        for i in range(self.file_table.rowCount()):
            row_data_type_str = self.table_data[i][COL_TYPE].lower()

            is_enabled = False
            if not self.selected_media_type_details:
                is_enabled = True
            elif visible_exts_for_current_selection:
                if row_data_type_str in visible_exts_for_current_selection:
                    is_enabled = True

            self.set_row_enabled_state(i, is_enabled)

            if not is_enabled and self.table_data[i][COL_CHECK]:
                self.table_data[i][COL_CHECK] = False
                item = self.file_table.item(i, COL_CHECK)
                if item:
                    item.setCheckState(Qt.CheckState.Unchecked)

        self.update_convert_button_state()

    @Slot()
    def _on_select_output_folder_clicked(self):
        if not self.output_folder_path_display:
            return
        current_path = self.output_folder_path_display.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self.ui, "Select Output Folder", current_path)
        if folder:
            self.output_folder_path_display.setText(os.path.normpath(folder))
        self.update_convert_button_state()

    @Slot()
    def update_convert_button_state(self):
        if not self.main_action_button:
            return

        job_and_media_selected = bool(self.selected_media_type_details)

        output_type_ok = True
        if self.selected_media_type_details:
            defined_output_exts = self.selected_media_type_details.get(
                "output_ext", [])
            if defined_output_exts:
                output_type_ok = bool(self.selected_output_filter)

        files_checked_and_active = False
        if self.file_table:
            for i, row_data in enumerate(self.table_data):
                if row_data[COL_CHECK]:
                    item_type_in_table = row_data[COL_TYPE].lower()
                    current_filter_set = self.active_input_filters
                    if not current_filter_set and self.selected_media_type_details:
                        current_filter_set = set(
                            self.selected_media_type_details.get("input_ext", []))

                    if not self.selected_media_type_details or \
                       not current_filter_set or \
                       item_type_in_table in current_filter_set:
                        files_checked_and_active = True
                        break

        output_folder_ok = True
        if self.selected_media_type_details and self.selected_media_type_details.get("requires_output_folder", False):
            if self.output_same_folder_checkbox and not self.output_same_folder_checkbox.isChecked():
                if self.output_folder_path_display and not self.output_folder_path_display.text():
                    output_folder_ok = False

        self.main_action_button.setEnabled(
            job_and_media_selected and
            output_type_ok and
            files_checked_and_active and
            output_folder_ok
        )

    @Slot(QPoint)
    def _show_file_table_context_menu(self, position: QPoint):
        if not self.file_table:
            return
        menu = QMenu(self)

        select_all_action = menu.addAction("Select all (visible/active)")
        clear_selection_action = menu.addAction("Clear selection in rows")
        remove_selected_action = menu.addAction("Remove selected rows")
        menu.addSeparator()
        clear_all_action = menu.addAction("Clear all items from list")

        select_all_action.triggered.connect(self._on_table_select_all)
        clear_selection_action.triggered.connect(
            self._on_table_clear_selection)
        remove_selected_action.triggered.connect(
            self._on_table_remove_selected)
        clear_all_action.triggered.connect(self.clear_input_list)

        menu.exec(self.file_table.mapToGlobal(position))

    @Slot()
    def _on_table_select_all(self):
        if not self.file_table:
            return
        for i in range(len(self.table_data)):
            item_chk_widget = self.file_table.item(i, COL_CHECK)
            if item_chk_widget and item_chk_widget.flags() & Qt.ItemFlag.ItemIsEnabled:
                self.table_data[i][COL_CHECK] = True
                item_chk_widget.setCheckState(Qt.CheckState.Checked)
        self.update_convert_button_state()

    @Slot()
    def _on_table_clear_selection(self):
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
        removed_count = 0
        for i in range(len(self.table_data) - 1, -1, -1):
            if self.table_data[i][COL_CHECK]:
                del self.table_data[i]
                removed_count += 1

        if removed_count > 0:
            self.update_table_widget()
            if self.statusbar:
                self.statusbar.showMessage(
                    f"{removed_count} item(s) removed. {len(self.table_data)} remaining.")
        self.update_convert_button_state()

    @Slot()
    def open_settings(self):
        dialog = SettingsDialog(self.ui)
        if dialog.exec():
            if self.statusbar:
                self.statusbar.showMessage("Settings updated and saved.")
            if self.delete_input_checkbox:
                self.delete_input_checkbox.setChecked(
                    config.settings.DELETE_SOURCE_ON_SUCCESS)
        else:
            if self.statusbar:
                self.statusbar.showMessage("Settings dialog cancelled.")

    @Slot()
    def add_files(self):
        dialog_filter_name = "All Supported Files"
        current_input_exts_to_use_for_dialog = set(
            menu_definitions.ALL_VALID_INPUT_EXTENSIONS)

        if self.selected_media_type_details:
            media_specific_exts = self.selected_media_type_details.get(
                "input_ext", [])
            if media_specific_exts:
                current_input_exts_to_use_for_dialog = set(media_specific_exts)
                media_name = self.selected_media_type_details.get(
                    "media_name", "Current Job")
                dialog_filter_name = f"{media_name} Files"

        patterns = [
            f"*.{ext}" for ext in sorted(list(current_input_exts_to_use_for_dialog))]
        dialog_filter_string = f"{dialog_filter_name} ({' '.join(patterns)});;All Files (*.*)"

        files, _ = QFileDialog.getOpenFileNames(
            self.ui, "Select Files", "", dialog_filter_string)
        if files:
            self.process_added_paths(files, from_add_files_dialog=True,
                                     dialog_filter_exts=current_input_exts_to_use_for_dialog)

    @Slot()
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self.ui, "Select Folder")
        if folder:
            self.process_added_paths([folder])

    @Slot()
    def clear_input_list(self):
        self.table_data = []
        self.update_table_widget()
        if self.statusbar:
            self.statusbar.showMessage("Input list cleared.")
        self.update_convert_button_state()

    @Slot(int, int)
    def handle_cell_click(self, row, column):
        if not self.file_table or column != COL_CHECK or not (0 <= row < len(self.table_data)):
            return

        item_flags = self.file_table.item(row, column).flags()
        if item_flags & Qt.ItemFlag.ItemIsEnabled:
            self.table_data[row][COL_CHECK] = not self.table_data[row][COL_CHECK]
            self.file_table.item(row, COL_CHECK).setCheckState(
                Qt.CheckState.Checked if self.table_data[row][COL_CHECK] else Qt.CheckState.Unchecked
            )
            self.update_convert_button_state()
        else:
            if self.statusbar:
                self.statusbar.showMessage(
                    "This file type is currently filtered out. Adjust input filters to select.", 3000)

    @Slot(bool)
    def toggle_log_visibility(self, checked):
        if self.log_output_text:
            self.log_output_text.setVisible(checked)
        if self.clear_log_button:
            self.clear_log_button.setVisible(checked)
        if self.toggle_log_button:
            self.toggle_log_button.setText(
                "Hide Log ▲" if checked else "Show Log ▼")

    @Slot()
    def clear_log(self):
        if self.log_output_text:
            self.log_output_text.clear()

    @Slot(str)
    def handle_output_update(self, message):
        if self.log_output_text:
            self.log_output_text.append(message)

    @Slot(str)
    def handle_error_update(self, message):
        if self.log_output_text:
            self.log_output_text.append(f"<font color='red'>{message}</font>")

    def process_added_paths(self, paths, from_add_files_dialog=False, dialog_filter_exts=None):
        is_recursive = self.recursive_checkbox.isChecked(
        ) if self.recursive_checkbox else False
        newly_added_count = 0
        current_paths_in_table = {row_data[COL_PATH]
                                  for row_data in self.table_data}

        valid_exts_for_adding = set()
        if from_add_files_dialog and dialog_filter_exts:
            valid_exts_for_adding = dialog_filter_exts
        elif self.active_input_filters:
            valid_exts_for_adding = self.active_input_filters
        elif self.selected_media_type_details:
            valid_exts_for_adding = set(
                self.selected_media_type_details.get("input_ext", []))
        else:
            valid_exts_for_adding = set(
                menu_definitions.ALL_VALID_INPUT_EXTENSIONS)

        ignored_files_log = []

        for item_path_raw in paths:
            item_path = os.path.normpath(item_path_raw)
            if not item_path or not os.path.exists(item_path):
                continue

            if os.path.isfile(item_path):
                file_ext_lower = os.path.splitext(
                    item_path)[1].lower().lstrip('.')
                if (not valid_exts_for_adding or file_ext_lower in valid_exts_for_adding) and \
                   item_path not in current_paths_in_table:
                    self.table_data.append(
                        [True, item_path, file_ext_lower.upper()])
                    newly_added_count += 1
                elif item_path not in current_paths_in_table:
                    ignored_files_log.append(os.path.basename(
                        item_path) + f" (type '.{file_ext_lower}' not in current add filter)")

            elif os.path.isdir(item_path):
                for f_path in self._scan_folder(item_path, is_recursive, valid_exts_for_adding):
                    if f_path not in current_paths_in_table:
                        file_ext_lower = os.path.splitext(
                            f_path)[1].lower().lstrip('.')
                        self.table_data.append(
                            [True, f_path, file_ext_lower.upper()])
                        newly_added_count += 1

        if ignored_files_log and self.log_output_text:
            self.log_output_text.append(
                f"<font color='orange'>WARNING: Files ignored during add (type mismatch or duplicate): {', '.join(ignored_files_log)}</font>")

        if newly_added_count > 0:
            self.table_data.sort(key=lambda x: x[COL_PATH])
            self.update_table_widget()

        if self.statusbar:
            self.statusbar.showMessage(
                f"{len(self.table_data)} file(s) in list. ({newly_added_count} added).")
        self.update_convert_button_state()

    def _scan_folder(self, folder_path, recursive, valid_extensions_for_scan):
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

    def update_table_widget(self):
        if not self.file_table:
            return

        self.file_table.setRowCount(0)
        self.file_table.setRowCount(len(self.table_data))

        for r_idx, r_data in enumerate(self.table_data):
            chk_state_from_model, path, type_s_from_model = r_data

            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable |
                              Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(
                Qt.CheckState.Checked if chk_state_from_model else Qt.CheckState.Unchecked)
            self.file_table.setItem(r_idx, COL_CHECK, chk_item)

            self.file_table.setItem(r_idx, COL_PATH, QTableWidgetItem(path))

            type_item = QTableWidgetItem(type_s_from_model)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.file_table.setItem(r_idx, COL_TYPE, type_item)

        self._apply_filter_to_table()

    def set_row_enabled_state(self, r_idx, enabled):
        if not self.file_table or not (0 <= r_idx < self.file_table.rowCount()):
            return

        dis_color = self.palette().color(QPalette.ColorGroup.Disabled,
                                         QPalette.ColorRole.WindowText)
        en_color = self.palette().color(QPalette.ColorGroup.Normal,
                                        QPalette.ColorRole.WindowText)

        for c_idx in range(self.file_table.columnCount()):
            item = self.file_table.item(r_idx, c_idx)
            if item:
                current_flags = item.flags()
                if enabled:
                    item.setFlags(current_flags | Qt.ItemFlag.ItemIsEnabled)
                    item.setForeground(en_color)
                else:
                    item.setFlags(current_flags & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setForeground(dis_color)

    @Slot()
    def close_application(self):
        print("DEBUG: close_application() called (e.g., from File > Exit).")
        self.close()

    def closeEvent(self, event: QCloseEvent):
        print("DEBUG: ConverterWindow.closeEvent() triggered.")
        app = QApplication.instance()

        if self.conversion_thread and self.conversion_thread.isRunning():
            reply = QMessageBox.question(
                self,
                'Confirm Exit',
                "A job is currently running. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                print("DEBUG: User confirmed exit during active conversion.")
                self._ensure_thread_stopped()  # Use the new method
                event.accept()
                if app:
                    print(
                        "DEBUG: Calling app.quit() from closeEvent (conversion was active).")
                    app.quit()
            else:
                print("DEBUG: User cancelled exit during active conversion.")
                event.ignore()
        else:
            print("DEBUG: No active conversion, accepting close event.")
            event.accept()
            if app:
                print("DEBUG: Calling app.quit() from closeEvent (no conversion).")
                app.quit()


def run_gui():
    print("DEBUG: Initializing QApplication in gui_main_window.run_gui()...")
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    # --- Application Icon Setting ---
    # The __file__ variable gives the path to the current script (gui_main_window.py)
    # os.path.dirname(__file__) gives the directory of this script (converter_tools)
    # Then we join "assets", "qt" and "app_icon.png" to get the full path to the icon.
    icon_path = os.path.join(os.path.dirname(
        __file__), "assets", "qt", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))  # Set the application-wide icon
        print(f"DEBUG: Application icon set from {icon_path}")
    else:
        print(f"DEBUG: Application icon not found at {icon_path}. Using default system icon.")

    print(
        f"DEBUG (gui_main_window): Config SUBPROCESS_TIMEOUT: {config.settings.SUBPROCESS_TIMEOUT}")

    print("DEBUG: Creating ConverterWindow instance...")
    window_wrapper = ConverterWindow()

    if window_wrapper.ui:
        print("DEBUG: Showing main window (window_wrapper.ui)...")
        window_wrapper.ui.show()

        print("DEBUG: Entering Qt event loop (app.exec())...")
        exit_code = app.exec()
        print(
            f"DEBUG: Qt event loop finished. app.exec() returned: {exit_code}")

        active_threads = threading.enumerate()
        print(f"DEBUG: Active threads before sys.exit() ({len(active_threads)}):")
        for thread_item in active_threads:
            print(f"  - Name: {thread_item.name}, Daemon: {thread_item.daemon}, Alive: {thread_item.is_alive()}")
            if thread_item != threading.main_thread() and thread_item.is_alive() and not thread_item.daemon:
                print(f"WARNING: Non-daemon thread '{thread_item.name}' is still alive. Python might hang if not handled.")

        print(f"DEBUG: Calling sys.exit({exit_code}). Python process should terminate if all non-daemon threads are done.")
        sys.exit(exit_code)
    else:
        print("DEBUG: Exiting due to UI load failure in ConverterWindow initialization.")
        sys.exit(-1)
