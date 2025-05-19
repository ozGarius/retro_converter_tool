# -*- coding: utf-8 -*-
# /convert_tools/gui.py (Enhanced Progress Indication & Cancel)

import sys
import os
import traceback
import time

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
        QPushButton, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QComboBox, QLabel, QTextEdit, QSizePolicy, QSpacerItem, QMenuBar,
        QFileDialog, QMessageBox, QStatusBar, QDialog, QDialogButtonBox,
        QLineEdit, QSpinBox, QGroupBox, QMenu, QProgressBar
    )
    from PySide6.QtGui import QAction, QKeySequence, QColor, QPalette, QCloseEvent
    from PySide6.QtCore import Qt, Slot, QThread, Signal, QPoint
    from PySide6.QtUiTools import QUiLoader
except ImportError as e:
    print(f"FATAL ERROR: PySide6 or PySide6.QtUiTools is not installed or found: {e}")
    sys.exit(1)

try:
    import config
    import utils
    import conversions
    import menu_definitions
except ImportError as e:
    print(f"FATAL ERROR: gui.py failed to import sibling modules.\nDetails: {e}")
    sys.exit(1)

COL_CHECK = 0
COL_PATH = 1
COL_TYPE = 2
TABLE_HEADINGS = ['✓', 'File Path', 'Type']

N_STAGES_PER_FILE = 3  # 1: Prep/Copy, 2: Convert, 3: Finalize/Move


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Converter Settings")
        self.setMinimumWidth(450)
        main_layout = QVBoxLayout(self)
        core_group_box = QGroupBox("Core Settings")
        core_layout = QFormLayout(core_group_box)
        self.copy_locally_checkbox = QCheckBox("Copy files locally before processing")
        self.delete_source_checkbox = QCheckBox("Delete original file on successful conversion")
        self.temp_dir_edit = QLineEdit()
        self.temp_dir_browse_button = QPushButton("Browse...")
        self.temp_dir_browse_button.clicked.connect(self.browse_temp_dir)
        core_layout.addRow(self.copy_locally_checkbox)
        core_layout.addRow(self.delete_source_checkbox)
        temp_dir_layout = QHBoxLayout()
        temp_dir_layout.addWidget(self.temp_dir_edit)
        temp_dir_layout.addWidget(self.temp_dir_browse_button)
        core_layout.addRow("Main Temp Directory:", temp_dir_layout)
        main_layout.addWidget(core_group_box)
        tool_group_box = QGroupBox("Tool-Specific Settings")
        tool_layout = QFormLayout(tool_group_box)
        self.validate_7z_checkbox = QCheckBox("Validate 7z archive after creation")
        self.compress_level_spinbox = QSpinBox()
        self.compress_level_spinbox.setRange(1, 22)
        tool_layout.addRow(self.validate_7z_checkbox)
        tool_layout.addRow("RVZ Compression Level (1-22):", self.compress_level_spinbox)
        main_layout.addWidget(tool_group_box)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.load_settings()

    def load_settings(self):
        self.copy_locally_checkbox.setChecked(config.COPY_LOCALLY)
        self.delete_source_checkbox.setChecked(config.DELETE_SOURCE_ON_SUCCESS)
        self.validate_7z_checkbox.setChecked(config.VALIDATE_FILE)
        self.temp_dir_edit.setText(config.MAIN_TEMP_DIR)
        self.compress_level_spinbox.setValue(config.DOLPHIN_COMPRESS_LEVEL)

    def browse_temp_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Temporary Directory", self.temp_dir_edit.text())
        if directory:
            self.temp_dir_edit.setText(os.path.normpath(directory))

    def accept(self):
        temp_dir = os.path.normpath(self.temp_dir_edit.text())
        if not os.path.isdir(os.path.dirname(temp_dir)) and not os.path.exists(temp_dir):
            parent = os.path.dirname(temp_dir)
            if not parent or not os.path.isdir(parent):
                QMessageBox.warning(self, "Settings Error", f"Invalid Temp Directory path:\n{temp_dir}\nParent directory does not exist or path is invalid.")
                return
        config.COPY_LOCALLY = self.copy_locally_checkbox.isChecked()
        config.DELETE_SOURCE_ON_SUCCESS = self.delete_source_checkbox.isChecked()
        config.VALIDATE_FILE = self.validate_7z_checkbox.isChecked()
        config.MAIN_TEMP_DIR = temp_dir
        config.DOLPHIN_COMPRESS_LEVEL = self.compress_level_spinbox.value()
        main_window = self.parent()
        if isinstance(main_window, ConverterWindow) and hasattr(main_window, 'delete_input_checkbox'):
            main_window.delete_input_checkbox.setChecked(config.DELETE_SOURCE_ON_SUCCESS)
        super().accept()


class ConversionWorker(QThread):
    # Replace status_update with a more granular signal
    # overall_progress_signal = Signal(int, int, str) # current_cumulative_step, total_overall_steps, description_with_filename
    # For clarity, let's reuse status_update and adjust its meaning in the slot.
    # The slot handle_overall_progress_update in ConverterWindow will interpret these.
    status_update = Signal(int, int, str)
    output_update = Signal(str)
    error_update = Signal(str)
    critical_error_occurred = Signal(str)
    file_progress_update = Signal(int)
    finished = Signal(int, int)

    def __init__(self, files_to_convert, conversion_details, output_folder_path,
                 overwrite_files, selected_primary_output_ext, selected_secondary_output_ext,
                 parent=None):
        super().__init__(parent)
        self.files_to_convert = files_to_convert
        self.conversion_details = conversion_details
        self.output_folder_path = output_folder_path
        self.overwrite_files = overwrite_files
        self.selected_primary_output_ext = selected_primary_output_ext
        self.selected_secondary_output_ext = selected_secondary_output_ext
        self._stop_requested = False
        self.total_overall_steps = len(self.files_to_convert) * N_STAGES_PER_FILE
        self.cumulative_overall_steps = 0
        # Initialize progress tracking attributes
        self.total_files_in_job = 0
        self.total_steps_in_job = 0
        self.current_file_idx_for_label = 0
        self.current_overall_step = 0

    def _report_stage_progress(self, stage_description, current_filename):
        if self._stop_requested:
            return
        self.cumulative_overall_steps += 1
        self.status_update.emit(  # Use the existing status_update signal with new meaning
            self.cumulative_overall_steps,
            self.total_overall_steps,
            f"{stage_description}: {current_filename}"
        )

    def run(self):
        self._stop_requested = False
        success_count = 0
        fail_count = 0
        # total_files = len(self.files_to_convert)
        func_name = self.conversion_details.get('conversion_func_name')
        conv_func = getattr(conversions, func_name, None) if func_name else None

        if not callable(conv_func):
            critical_msg = f"Critical Error: Conversion function '{func_name}' is not valid. Job cannot proceed."
            self.error_update.emit(critical_msg)
            self.critical_error_occurred.emit(critical_msg)
            self.finished.emit(0, len(self.files_to_convert))
            return

        primary_out_ext_for_util = self.selected_primary_output_ext
        secondary_out_ext_for_util = self.selected_secondary_output_ext
        self.cumulative_overall_steps = 0  # Initialize for the batch

        try:
            for i, file_path in enumerate(self.files_to_convert):
                if self._stop_requested:
                    self.output_update.emit("--- Conversion process aborted by user ---")
                    fail_count = len(self.files_to_convert) - success_count  # Correct calculation for aborted
                    break

                current_file_name = os.path.basename(file_path)
                self.output_update.emit(f"\n--- Processing: {current_file_name} ---")

                # Define a callback for utils.process_file to report its internal stages
                stage_reporter_for_process_file = lambda stage_desc: self._report_stage_progress(stage_desc, current_file_name)

                current_output_dir = self.output_folder_path
                if not self.conversion_details.get("requires_output_folder", True) or not current_output_dir:
                    current_output_dir = os.path.dirname(file_path)

                success = utils.process_file(
                    file_path, conv_func,
                    primary_out_ext_for_util,
                    secondary_out_ext_for_util,
                    output_signal=self.output_update,
                    error_signal=self.error_update,
                    explicit_output_dir=current_output_dir,
                    allow_overwrite=self.overwrite_files,
                    target_format_from_worker=primary_out_ext_for_util,
                    stage_reporter=stage_reporter_for_process_file
                )

                if success:
                    success_count += 1
                    self.output_update.emit(f"--- Success: {current_file_name} ---")
                    self.file_progress_update.emit(100)
                else:
                    fail_count += 1
                    self.error_update.emit(f"--- FAILED: {current_file_name} (check log for details) ---")
                    # Ensure all stages for this failed file are "accounted for" if it bails early
                    # This is tricky if process_file errors out mid-way.
                    # For simplicity, we assume process_file will call the reporter 3 times
                    # or the cumulative_overall_steps won't reach its max.
                    # To ensure the bar completes even on failure for a file's stages:
                    expected_steps_for_this_file = (i + 1) * N_STAGES_PER_FILE
                    if self.cumulative_overall_steps < expected_steps_for_this_file:
                        # Fast-forward steps for this failed file if process_file didn't report all
                        missing_stages = expected_steps_for_this_file - self.cumulative_overall_steps
                        for _ in range(missing_stages):
                            self._report_stage_progress("File failed", current_file_name)
                    self.file_progress_update.emit(100)  # Mark current file as "done" (processed)

        except Exception as e:
            tb = traceback.format_exc()
            critical_msg = f"Critical Error in conversion worker: {tb} | {e}"
            self.error_update.emit(critical_msg)
            self.critical_error_occurred.emit(critical_msg)
            fail_count = len(self.files_to_convert) - success_count
        finally:
            # Ensure overall progress bar reaches its maximum if all files were attempted (even if some failed)
            # This might already be handled if _report_stage_progress is called correctly for failures.
            if not self._stop_requested and self.cumulative_overall_steps < self.total_overall_steps:
                final_stage_desc = "Finalizing job completion"
                # Potentially emit remaining steps to fill the bar
                remaining_ticks = self.total_overall_steps - self.cumulative_overall_steps
                for _ in range(remaining_ticks):
                    self.cumulative_overall_steps += 1
                    self.status_update.emit(self.cumulative_overall_steps, self.total_overall_steps, final_stage_desc)

            self.finished.emit(success_count, fail_count)

    def request_stop(self):
        self.output_update.emit("--- Stop requested for current job ---")
        self._stop_requested = True


class ConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ui_file_path = os.path.join(os.path.dirname(__file__), "qt", "main_window.ui")
        if not os.path.exists(ui_file_path):
            QMessageBox.critical(self, "Error", f"UI file not found: {ui_file_path}")
            sys.exit(-1)
        loader = QUiLoader()
        self.ui = loader.load(ui_file_path, self)
        if not self.ui:
            QMessageBox.critical(self, "UI Load Error", f"Could not load: {loader.errorString()}")
            sys.exit(-1)

        # --- Find Widgets (ensure names match your .ui file) ---
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
        self.statusbar = self.ui.statusBar()
        self.actionSettings = self.ui.findChild(QAction, "actionSettings")
        self.actionExit = self.ui.findChild(QAction, "actionExit")

        # ** Find Progress UI Elements **
        self.progress_group_box = self.ui.findChild(QGroupBox, "progress_group_box")
        self.overall_label = self.ui.findChild(QLabel, "overall_label")
        self.overall_progress_bar = self.ui.findChild(QProgressBar, "overall_progress_bar")
        self.overall_cancel_button = self.ui.findChild(QPushButton, "overall_cancel_button")
        self.file_label = self.ui.findChild(QLabel, "file_label")
        self.file_progress_bar = self.ui.findChild(QProgressBar, "file_progress_bar")
        self.file_cancel_button = self.ui.findChild(QPushButton, "file_cancel_button")


# --- Basic Widget Sanity Check ---
        critical_widget_names = [
            "job_type_combo", "media_type_combo", "add_files_button", "file_table",
            "output_folder_group_box", "main_action_button", "log_output_text",
            "statusbar", "actionSettings", "actionExit",
            "progress_group_box", "overall_label", "overall_progress_bar", "overall_cancel_button",
            "file_label", "file_progress_bar", "file_cancel_button"
        ]
        for name in critical_widget_names:
            widget = getattr(self, name, None)  # Check if attribute was set
            if widget is None:  # It means findChild failed for this objectName
                QMessageBox.critical(self, "UI Element Error", f"UI element '{name}' not found. Check objectName in .ui file.")
                sys.exit(-1)

        # --- Initialize Progress UI ---
        self.progress_group_box.setVisible(False)  # Hide the whole group initially
        self.overall_progress_bar.setValue(0)
        self.file_progress_bar.setValue(0)
        self.overall_label.setText("Overall Progress:")
        self.file_label.setText("Current File:")

        self.file_table.setHorizontalHeaderLabels(TABLE_HEADINGS)
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_PATH, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        header.setStyleSheet("QHeaderView::section { padding-left: 4px; padding-right: 4px; }")

        # --- Connect Signals ---
        self.job_type_combo.currentTextChanged.connect(self._on_job_type_changed)
        self.media_type_combo.currentTextChanged.connect(self._on_media_type_changed)
        self.add_files_button.clicked.connect(self.add_files)
        self.add_folder_button.clicked.connect(self.add_folder)
        self.select_input_types_button.clicked.connect(self._on_select_input_types_clicked)
        self.file_table.cellClicked.connect(self.handle_cell_click)
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._show_file_table_context_menu)
        self.select_output_folder_button.clicked.connect(self._on_select_output_folder_clicked)
        self.select_output_type_button.clicked.connect(self._on_select_output_type_clicked)
        self.output_same_folder_checkbox.toggled.connect(self._on_output_same_folder_toggled)
        self.delete_input_checkbox.toggled.connect(self._on_delete_input_toggled)
        self.main_action_button.clicked.connect(self.start_conversion)
        self.toggle_log_button.toggled.connect(self.toggle_log_visibility)
        self.clear_log_button.clicked.connect(self.clear_log)
        self.actionSettings.triggered.connect(self.open_settings)
        self.actionExit.triggered.connect(self.close_application)
        # Connect Cancel Buttons
        self.overall_cancel_button.clicked.connect(self._request_conversion_stop)
        self.file_cancel_button.clicked.connect(self._request_conversion_stop)  # Both can point to the same stop for now

        self.conversion_thread = None
        self.table_data = []
        self.selected_job_details = None
        self.selected_media_type_details = None
        self.active_input_filters = set()
        self.selected_output_filter = None

        self._populate_job_types()
        self.delete_input_checkbox.setChecked(config.DELETE_SOURCE_ON_SUCCESS)
        self._on_output_same_folder_toggled(self.output_same_folder_checkbox.isChecked())
        self.update_ui_for_job_selection()
        self.statusbar.showMessage("Ready. Select a job type to begin.")
        self.setWindowTitle("Converter Tool (UI Loaded)")

    @Slot()  # New slot for cancel buttons
    def _request_conversion_stop(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.request_stop()
            # Optionally disable cancel buttons here to prevent multiple clicks
            self.overall_cancel_button.setEnabled(False)
            self.file_cancel_button.setEnabled(False)
            self.statusbar.showMessage("Cancellation requested...")

    @Slot()
    def start_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            QMessageBox.warning(self, "Busy", "A conversion is already in progress.")
            return
        if not self.selected_media_type_details:
            QMessageBox.warning(self, "Setup Error", "Please select a valid job and media type.")
            return
        if not self.selected_output_filter and self.selected_media_type_details.get("output_ext"):
            QMessageBox.warning(self, "Setup Error", "Please select an output file type for this job.")
            return

        selected_files_data = []
        for i, row_data in enumerate(self.table_data):
            if row_data[COL_CHECK]:
                item_type = row_data[COL_TYPE].lower()
                is_active_by_filter = False
                current_filter_set = self.active_input_filters
                if not current_filter_set and self.selected_media_type_details:
                    current_filter_set = set(self.selected_media_type_details.get("input_ext", []))
                if not self.selected_media_type_details or (current_filter_set and item_type in current_filter_set):
                    is_active_by_filter = True
                if is_active_by_filter:
                    selected_files_data.append(row_data)

        if not selected_files_data:
            QMessageBox.warning(self, "No Files", "No files selected for conversion (or none match current filters).")
            return

        total_files_to_process = len(selected_files_data)
        selected_file_paths = [data[COL_PATH] for data in selected_files_data]

        output_folder = None
        job_requires_output_folder = self.selected_media_type_details.get("requires_output_folder", False)
        output_in_same_folder = self.output_same_folder_checkbox.isChecked()

        if job_requires_output_folder:
            if not output_in_same_folder:
                output_folder = self.output_folder_path_display.text()
                if not output_folder:
                    QMessageBox.warning(self, "Output Folder Missing", "Please select an output folder or choose 'Output in same folder'.")
                    return
                estimated_min_gb = 0.1
                free_space_gb = utils.get_free_disk_space_gb(output_folder)
                if free_space_gb is not None and free_space_gb < estimated_min_gb:
                    QMessageBox.critical(self, "Insufficient Disk Space",
                                         f"Output location '{output_folder}' has < {estimated_min_gb:.1f}GB free "
                                         f"(~{free_space_gb:.2f}GB available). Select another location or free up space.")
                    return
                elif free_space_gb is None:
                    if not QMessageBox.question(self, "Disk Space Unknown",
                                                "Could not determine free disk space for output. Continue anyway?",
                                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                        return

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

        if not primary_out_ext and self.selected_media_type_details.get("output_ext"):
            QMessageBox.warning(self, "Output Type Error", "No primary output type selected/defined for this job.")
            return

        current_overwrite_files = self.overwrite_files_checkbox.isChecked()
        self.set_ui_enabled(False)  # Disables general UI, enables progress UI

        # --- Setup Progress Bars & Labels ---
        self.progress_group_box.setVisible(True)
        self.overall_label.setText(f"Overall Progress (0/{total_files_to_process})")
        self.overall_progress_bar.setMaximum(total_files_to_process)
        self.overall_progress_bar.setValue(0)
        self.file_label.setText("Current File: -")
        self.file_progress_bar.setValue(0)
        self.overall_cancel_button.setEnabled(True)
        self.file_cancel_button.setEnabled(True)

        self.statusbar.showMessage(f"Starting '{self.main_action_button.text()}' for {total_files_to_process} file(s)...")
        if not self.log_output_text.isVisible():
            self.toggle_log_button.setChecked(True)
        self.log_output_text.clear()

        self.conversion_thread = ConversionWorker(
            selected_file_paths, self.selected_media_type_details,
            output_folder, current_overwrite_files,
            primary_out_ext, secondary_out_ext
        )
        self.conversion_thread.status_update.connect(self.handle_overall_progress_update)
        self.conversion_thread.file_progress_update.connect(self.handle_file_progress_update)
        self.conversion_thread.output_update.connect(self.handle_output_update)
        self.conversion_thread.error_update.connect(self.handle_error_update)
        self.conversion_thread.critical_error_occurred.connect(self.handle_critical_error)
        self.conversion_thread.finished.connect(self.handle_conversion_finished)
        self.conversion_thread.start()

    @Slot(str)
    def handle_critical_error(self, message):
        QMessageBox.critical(self, "Critical Conversion Error", message)
        self.set_ui_enabled(True)
        self.update_convert_button_state()
        # Hide progress UI on critical error
        self.progress_group_box.setVisible(False)

    @Slot(int, int, str)
    def handle_overall_progress_update(self, current_overall_step, total_overall_steps, phase_description):
        self.overall_progress_bar.setMaximum(total_overall_steps)
        self.overall_progress_bar.setValue(current_overall_step)
        self.overall_label.setText(f"Overall: {phase_description} ({current_overall_step}/{total_overall_steps})")
        self.statusbar.showMessage(phase_description)  # Show current phase in status bar
        # For Per-File Progress (Indeterminate)
        # Filename for the per-file label will now be part of phase_description
        # We need to extract it or have a separate way to update file_label
        # Let's assume phase_description is like "Stage: filename.ext"
        parts = phase_description.split(': ', 1)
        current_op_label = parts[0]
        current_filename_display = parts[1] if len(parts) > 1 else ""

        # Only set file_label and indeterminate if it's the "Preparing" stage for a new file,
        # or find a better way to know a new file started.
        # For now, we'll assume the phase_description helps.
        if "Preparing" in current_op_label or "Copying" in current_op_label:
            self.file_label.setText(f"Current: {current_filename_display}")
            self.file_progress_bar.setRange(0, 0)  # Set to indeterminate

    @Slot(int)
    def handle_file_progress_update(self, percentage):
        if percentage == 100:  # Called when a single file's processing (convert + move) is done
            self.file_progress_bar.setRange(0, 100)  # Set back to determinate
            self.file_progress_bar.setValue(100)
        # If the bar is indeterminate and percentage is not 100 (e.g. an old emit(0)), it stays indeterminate.

    @Slot(int, int)
    def handle_conversion_finished(self, success_count, fail_count):
        status_msg = f"Job '{self.main_action_button.text()}' finished. Success: {success_count}, Failed: {fail_count}."
        self.statusbar.showMessage(status_msg)
        self.log_output_text.append(f"\n<b>{status_msg}</b>")

        # Update overall progress to max if all files were attempted
        if self.overall_progress_bar.maximum() == success_count + fail_count:
            self.overall_progress_bar.setValue(self.overall_progress_bar.maximum())
        else:  # If aborted, show actual processed count
            self.overall_progress_bar.setValue(success_count + fail_count)

        self.file_label.setText("Finished.")
        self.file_progress_bar.setValue(100 if success_count + fail_count > 0 else 0)  # Show 100 if any file was processed

        # Don't hide immediately, let user see final state
        # self.progress_group_box.setVisible(False)
        self.overall_cancel_button.setEnabled(False)  # Disable cancel buttons on finish
        self.file_cancel_button.setEnabled(False)

        self.set_ui_enabled(True)
        self.conversion_thread = None
        self.update_convert_button_state()

    def set_ui_enabled(self, enabled):
        # General UI elements
        self.add_files_button.setEnabled(enabled)
        self.add_folder_button.setEnabled(enabled)
        self.recursive_checkbox.setEnabled(enabled)
        self.file_table.setEnabled(enabled)
        self.job_type_combo.setEnabled(enabled)
        self.output_same_folder_checkbox.setEnabled(enabled)
        self.delete_input_checkbox.setEnabled(enabled)
        self.overwrite_files_checkbox.setEnabled(enabled)
        # ... other general controls ...

        if enabled:
            self.update_ui_for_job_selection()  # This handles media_combo, select_buttons, output_folder_group
            self.progress_group_box.setVisible(False)  # Hide progress when enabling general UI
            self.main_action_button.setEnabled(True)  # Will be re-evaluated by update_convert_button_state
            self.update_convert_button_state()
        else:  # UI disabled (conversion running)
            self.media_type_combo.setEnabled(False)
            self.select_input_types_button.setEnabled(False)
            self.select_output_type_button.setEnabled(False)
            self.output_folder_group_box.setEnabled(False)  # Disable output options during run
            self.main_action_button.setEnabled(False)
            self.progress_group_box.setVisible(True)  # Show progress UI
            self.overall_cancel_button.setEnabled(True)
            self.file_cancel_button.setEnabled(True)

    # ... (Rest of the methods: _populate_job_types, _on_job_type_changed, _on_media_type_changed,
    # update_ui_for_job_selection, update_ui_for_media_selection, _on_select_input_types_clicked,
    # _on_input_filter_type_toggled, _on_select_output_type_clicked, _on_output_filter_type_selected,
    # _apply_filter_to_table, _on_select_output_folder_clicked, update_convert_button_state,
    # context menu methods, add_files, add_folder, clear_input_list, handle_cell_click,
    # toggle_log_visibility, clear_log, handle_output_update, handle_error_update,
    # process_added_paths, _scan_folder, update_table_widget, set_row_enabled_state,
    # open_settings, close_application, closeEvent)
    # Ensure these are present from the previous version (`gui_py_input_filter_button`)
    # and adapted if necessary. For brevity, only directly modified/new methods are fully shown here.

    def _populate_job_types(self):
        self.job_type_combo.blockSignals(True)
        self.job_type_combo.clear()
        self.job_type_combo.addItem("(Select Job Type)")
        for job in menu_definitions.JOB_DEFINITIONS:
            self.job_type_combo.addItem(job["job_name"])
        self.job_type_combo.blockSignals(False)
        self.job_type_combo.setCurrentIndex(0)

    @Slot(bool)
    def _on_output_same_folder_toggled(self, checked):
        if self.select_output_folder_button and self.output_folder_path_display:
            self.select_output_folder_button.setVisible(not checked)
            self.output_folder_path_display.setVisible(not checked)
            if checked:
                self.output_folder_path_display.clear()
        self.update_convert_button_state()

    @Slot(bool)
    def _on_delete_input_toggled(self, checked):
        config.DELETE_SOURCE_ON_SUCCESS = checked
        self.statusbar.showMessage(f"Delete input files on success: {'Enabled' if checked else 'Disabled'}")

    @Slot(str)
    def _on_job_type_changed(self, selected_job_name):
        self.media_type_combo.blockSignals(True)
        self.media_type_combo.clear()
        self.media_type_combo.addItem("(Select Media Type)")
        self.selected_job_details = None
        self.selected_media_type_details = None
        self.active_input_filters.clear()
        self.selected_output_filter = None
        # Clear the file list in the table data and update the widget
        self.table_data = []
        self.update_table_widget()

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
        self.statusbar.showMessage("Input list cleared. Select a job type to begin.")

    @Slot(str)
    def _on_media_type_changed(self, selected_media_name):
        self.selected_media_type_details = None
        self.active_input_filters.clear()
        self.selected_output_filter = None

        if self.selected_job_details and selected_media_name and selected_media_name != "(Select Media Type)":
            for media_def in self.selected_job_details.get("media_types", []):
                if media_def["media_name"] == selected_media_name:
                    self.selected_media_type_details = media_def
                    self.active_input_filters = set(self.selected_media_type_details.get("input_ext", []))
                    output_exts = self.selected_media_type_details.get("output_ext", [])
                    if output_exts and isinstance(output_exts, list):
                        self.selected_output_filter = output_exts[0]
                    elif isinstance(output_exts, str):
                        self.selected_output_filter = output_exts
                    break
        self.update_ui_for_media_selection()

    def update_ui_for_job_selection(self):
        job_is_selected = bool(self.selected_job_details)
        self.media_type_combo.setEnabled(job_is_selected)
        if not job_is_selected:
            self.selected_media_type_details = None
            self.active_input_filters.clear()
            self.selected_output_filter = None
        self.update_ui_for_media_selection()

    def update_ui_for_media_selection(self):
        media_is_selected = bool(self.selected_media_type_details)
        action_text = "Start Job"
        input_ext_str = "N/A"
        output_ext_str = "N/A"
        requires_output_folder_setting = False
        can_select_output_type = False

        if self.selected_job_details:
            action_text = self.selected_job_details.get("action_text", "Start Job").upper()
        if media_is_selected:
            action_text = self.selected_media_type_details.get("action_text", action_text).upper()

            current_display_input_exts = self.active_input_filters
            if not current_display_input_exts and self.selected_media_type_details:
                current_display_input_exts = set(self.selected_media_type_details.get("input_ext", []))
            input_ext_str = ", ".join([f".{ext}" for ext in sorted(list(current_display_input_exts))]) if current_display_input_exts else "N/A"

            possible_output_exts = self.selected_media_type_details.get("output_ext", [])
            if self.selected_output_filter:
                output_ext_str = f".{self.selected_output_filter}"
            elif possible_output_exts and isinstance(possible_output_exts, list) and possible_output_exts:
                output_ext_str = f".{possible_output_exts[0]}"
            elif isinstance(possible_output_exts, str):
                output_ext_str = f".{possible_output_exts}"

            if isinstance(possible_output_exts, list) and len(possible_output_exts) > 1:
                can_select_output_type = True

            requires_output_folder_setting = self.selected_media_type_details.get("requires_output_folder", False)

        self.main_action_button.setText(action_text)
        self.input_file_types_label.setText(f"Input: {input_ext_str}")
        self.output_file_types_label.setText(f"Output: {output_ext_str}")
        self.select_input_types_button.setEnabled(media_is_selected and bool(self.selected_media_type_details.get("input_ext") if self.selected_media_type_details else False))
        self.select_output_type_button.setEnabled(can_select_output_type)

        output_in_same_folder = self.output_same_folder_checkbox.isChecked()
        can_show_custom_output = requires_output_folder_setting and not output_in_same_folder

        self.output_folder_group_box.setEnabled(requires_output_folder_setting)
        self.select_output_folder_button.setVisible(can_show_custom_output)
        self.output_folder_path_display.setVisible(can_show_custom_output)

        if not requires_output_folder_setting or output_in_same_folder:
            self.output_folder_path_display.clear()

        self._apply_filter_to_table()
        self.update_convert_button_state()

    @Slot()
    def _on_select_input_types_clicked(self):
        if not self.selected_media_type_details:
            self.statusbar.showMessage("Please select a job and media type first.", 3000)
            return
        possible_input_exts = self.selected_media_type_details.get("input_ext", [])
        if not possible_input_exts:
            self.statusbar.showMessage("No specific input types to filter for this selection.", 3000)
            return

        menu = QMenu(self)
        for ext in sorted(possible_input_exts):
            action = QAction(f".{ext}", self)
            action.setCheckable(True)
            action.setChecked(ext in self.active_input_filters)
            action.toggled.connect(lambda checked, current_ext=ext: self._on_input_filter_type_toggled(checked, current_ext))
            menu.addAction(action)
        button_pos = self.select_input_types_button.mapToGlobal(QPoint(0, self.select_input_types_button.height()))
        menu.exec(button_pos)

    @Slot(bool, str)
    def _on_input_filter_type_toggled(self, checked, extension):
        if checked:
            self.active_input_filters.add(extension)
        else:
            self.active_input_filters.discard(extension)

        active_filter_display_list = sorted(list(self.active_input_filters))
        if active_filter_display_list:
            self.input_file_types_label.setText(f"Input: {', '.join(['.' + ext for ext in active_filter_display_list])}")
        elif self.selected_media_type_details:
            all_media_exts = self.selected_media_type_details.get("input_ext", [])
            self.input_file_types_label.setText(f"Input: {', '.join(['.' + ext for ext in all_media_exts]) if all_media_exts else 'N/A'}")
        else:
            self.input_file_types_label.setText("Input: N/A")

        self.statusbar.showMessage(f"Input filter updated. Active: {', '.join(active_filter_display_list)}", 3000)
        self._apply_filter_to_table()

    @Slot()
    def _on_select_output_type_clicked(self):
        if not self.selected_media_type_details:
            self.statusbar.showMessage("Please select a media type first.", 3000)
            return

        possible_output_exts = self.selected_media_type_details.get("output_ext", [])
        if not isinstance(possible_output_exts, list) or not possible_output_exts:
            self.statusbar.showMessage("No selectable output types for this media.", 3000)
            return

        menu = QMenu(self)
        for ext_string in possible_output_exts:
            action = QAction(f".{ext_string}", self)
            action.setCheckable(True)
            action.setChecked(ext_string == self.selected_output_filter)
            action.triggered.connect(
                lambda checked_status, bound_ext_string=ext_string: self._on_output_filter_type_selected(bound_ext_string)
            )
            menu.addAction(action)

        button_pos = self.select_output_type_button.mapToGlobal(QPoint(0, self.select_output_type_button.height()))
        menu.exec(button_pos)

    @Slot(str)
    def _on_output_filter_type_selected(self, extension):
        self.selected_output_filter = extension
        self.output_file_types_label.setText(f"Output: .{extension}")
        self.statusbar.showMessage(f"Output type set to: .{extension}", 3000)
        self.update_convert_button_state()

    def _apply_filter_to_table(self):
        if not self.selected_media_type_details:
            for i in range(self.file_table.rowCount()):
                self.set_row_enabled_state(i, True)
            return

        visible_exts = self.active_input_filters
        if not visible_exts and self.selected_media_type_details:
            visible_exts = set(self.selected_media_type_details.get("input_ext", []))

        for i in range(self.file_table.rowCount()):
            row_data = self.table_data[i]
            file_type_in_table = row_data[COL_TYPE].lower()
            is_enabled = not self.selected_media_type_details or (visible_exts and file_type_in_table in visible_exts)
            self.set_row_enabled_state(i, is_enabled)
            if not is_enabled and self.table_data[i][COL_CHECK]:
                self.table_data[i][COL_CHECK] = False
                item = self.file_table.item(i, COL_CHECK)
                if item:
                    item.setCheckState(Qt.CheckState.Unchecked)
        self.update_convert_button_state()

    @Slot()
    def _on_select_output_folder_clicked(self):
        current_path = self.output_folder_path_display.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", current_path)
        if folder:
            self.output_folder_path_display.setText(os.path.normpath(folder))
        self.update_convert_button_state()

    @Slot()
    def update_convert_button_state(self):
        job_and_media_selected = bool(self.selected_media_type_details)
        output_type_selected = bool(self.selected_output_filter) or not bool(self.selected_media_type_details.get("output_ext") if self.selected_media_type_details else True)

        files_checked_and_active = False
        for i, row_data in enumerate(self.table_data):
            if row_data[COL_CHECK]:
                item_type = row_data[COL_TYPE].lower()
                is_active_by_filter = False
                current_filter_set = self.active_input_filters
                if not current_filter_set and self.selected_media_type_details:
                    current_filter_set = set(self.selected_media_type_details.get("input_ext", []))
                if not self.selected_media_type_details or (current_filter_set and item_type in current_filter_set):
                    is_active_by_filter = True
                if is_active_by_filter:
                    files_checked_and_active = True
                    break

        output_folder_ok = True
        if self.selected_media_type_details and self.selected_media_type_details.get("requires_output_folder", False):
            if not self.output_same_folder_checkbox.isChecked():
                output_folder_ok = bool(self.output_folder_path_display.text())

        self.main_action_button.setEnabled(job_and_media_selected and output_type_selected and files_checked_and_active and output_folder_ok)

    @Slot(QPoint)
    def _show_file_table_context_menu(self, position: QPoint):
        menu = QMenu(self)
        select_all_action = menu.addAction("Select all (visible and active)")
        clear_selection_action = menu.addAction("Clear selection in rows")
        remove_selected_action = menu.addAction("Remove selected rows")
        menu.addSeparator()
        clear_all_action = menu.addAction("Clear all items from list")
        select_all_action.triggered.connect(self._on_table_select_all)
        clear_selection_action.triggered.connect(self._on_table_clear_selection)
        remove_selected_action.triggered.connect(self._on_table_remove_selected)
        clear_all_action.triggered.connect(self.clear_input_list)
        menu.exec(self.file_table.mapToGlobal(position))

    @Slot()
    def _on_table_select_all(self):
        for i in range(self.file_table.rowCount()):
            item_chk = self.file_table.item(i, COL_CHECK)
            if item_chk and item_chk.flags() & Qt.ItemFlag.ItemIsEnabled:
                self.table_data[i][COL_CHECK] = True
        self.update_table_widget()
        self.update_convert_button_state()

    @Slot()
    def _on_table_clear_selection(self):
        for i in range(len(self.table_data)):
            self.table_data[i][COL_CHECK] = False
        self.update_table_widget()
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
            self.statusbar.showMessage(f"{removed_count} item(s) removed. {len(self.table_data)} remaining.")
        self.update_convert_button_state()

    @Slot()
    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.statusbar.showMessage("Settings updated.")
            if hasattr(self, 'delete_input_checkbox'):
                self.delete_input_checkbox.setChecked(config.DELETE_SOURCE_ON_SUCCESS)
        else:
            self.statusbar.showMessage("Settings dialog cancelled.")

    @Slot()
    def add_files(self):
        current_input_exts_to_filter_by = self.active_input_filters
        dialog_filter_name = "Filtered Files"
        if not current_input_exts_to_filter_by and self.selected_media_type_details:
            current_input_exts_to_filter_by = set(self.selected_media_type_details.get("input_ext", []))
            dialog_filter_name = f"{self.selected_media_type_details.get('media_name', 'Job')} Files"
        elif not current_input_exts_to_filter_by:
            current_input_exts_to_filter_by = set(menu_definitions.ALL_VALID_INPUT_EXTENSIONS)
            dialog_filter_name = "All Supported Files"

        patterns = [f"*.{ext}" for ext in sorted(list(current_input_exts_to_filter_by))] if current_input_exts_to_filter_by else ["*.*"]
        dialog_filter = f"{dialog_filter_name} ({' '.join(patterns)});;All Files (*.*)"

        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", dialog_filter)
        if files:
            added_files_details = []
            ignored_files_log = []
            for f_path in files:
                ext_lower = os.path.splitext(f_path)[1].lower().lstrip('.')
                if ext_lower in current_input_exts_to_filter_by:
                    added_files_details.append(f_path)
                else:
                    ignored_files_log.append(os.path.basename(f_path))
            if ignored_files_log:
                self.log_output_text.append(f"<font color='orange'>WARNING: Files ignored (type mismatch with current filter): {', '.join(ignored_files_log)}</font>")
            if added_files_details:
                self.process_added_paths(added_files_details)
            elif files:
                self.statusbar.showMessage("No files matched current input filter.")

    @Slot()
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.process_added_paths([folder])

    @Slot()
    def clear_input_list(self):
        self.table_data = []
        self.update_table_widget()
        self.statusbar.showMessage("Input list cleared.")
        self.update_convert_button_state()

    @Slot(int, int)
    def handle_cell_click(self, row, column):
        if column == COL_CHECK and 0 <= row < len(self.table_data):
            item_flags = self.file_table.item(row, column).flags()
            if item_flags & Qt.ItemFlag.ItemIsEnabled:
                self.table_data[row][COL_CHECK] = not self.table_data[row][COL_CHECK]
                item = self.file_table.item(row, COL_CHECK)
                if item:
                    item.setCheckState(Qt.CheckState.Checked if self.table_data[row][COL_CHECK] else Qt.CheckState.Unchecked)
                self.update_convert_button_state()
            else:
                self.statusbar.showMessage("This file type is currently filtered out. Adjust filters to select.", 3000)

    @Slot(bool)
    def toggle_log_visibility(self, checked):
        self.log_output_text.setVisible(checked)
        self.clear_log_button.setVisible(checked)
        self.toggle_log_button.setText("Hide Log ▲" if checked else "Show Log ▼")

    @Slot()
    def clear_log(self):
        self.log_output_text.clear()

    @Slot(str)  # This is for the generic output_update from worker/utils
    def handle_output_update(self, message):
        self.log_output_text.append(message)

    @Slot(str)
    def handle_error_update(self, message):
        self.log_output_text.append(f"<font color='red'>{message}</font>")

    def process_added_paths(self, paths):
        is_recursive = self.recursive_checkbox.isChecked()
        newly_added_count = 0
        current_paths_in_table = {row[COL_PATH] for row in self.table_data}

        valid_exts_for_scan = self.active_input_filters
        if not valid_exts_for_scan and self.selected_media_type_details:
            valid_exts_for_scan = set(self.selected_media_type_details.get("input_ext", []))
        if not valid_exts_for_scan:
            valid_exts_for_scan = set(menu_definitions.ALL_VALID_INPUT_EXTENSIONS)

        for item_path_raw in paths:
            item_path = os.path.normpath(item_path_raw)
            if not item_path or not os.path.exists(item_path):
                continue
            if os.path.isfile(item_path):
                ext = os.path.splitext(item_path)[1].lower().lstrip('.')
                if ext in valid_exts_for_scan and item_path not in current_paths_in_table:
                    self.table_data.append([True, item_path, ext.upper()])
                    newly_added_count += 1
            elif os.path.isdir(item_path):
                for f_path in self._scan_folder(item_path, is_recursive, valid_exts_for_scan):
                    if f_path not in current_paths_in_table:
                        ext = os.path.splitext(f_path)[1].lower().lstrip('.')
                        self.table_data.append([True, f_path, ext.upper()])
                        newly_added_count += 1
        if newly_added_count > 0:
            self.table_data.sort(key=lambda x: x[COL_PATH])
            self.update_table_widget()
        self.statusbar.showMessage(f"{len(self.table_data)} file(s) in list. ({newly_added_count} added).")
        self.update_convert_button_state()

    def _scan_folder(self, folder_path, recursive, valid_extensions):
        found = []
        norm_folder = os.path.normpath(folder_path)
        if not os.path.isdir(norm_folder):
            return found
        norm_temp = os.path.normpath(config.MAIN_TEMP_DIR)
        for r, _, fs in os.walk(norm_folder) if recursive else [(norm_folder, [], os.listdir(norm_folder))]:
            norm_r = os.path.normpath(r)
            if '_temp' in norm_r or norm_temp in norm_r:
                if recursive:
                    continue
                else:
                    break
            for f_item in fs:
                fp = os.path.join(norm_r, f_item)
                if os.path.isfile(fp):
                    if os.path.splitext(f_item)[1].lower().lstrip('.') in valid_extensions:
                        found.append(os.path.normpath(fp))
            if not recursive:
                break
        return found

    def update_table_widget(self):
        self.file_table.setRowCount(0)
        self.file_table.setRowCount(len(self.table_data))
        for r_idx, r_data in enumerate(self.table_data):
            chk_state, path, type_s = r_data
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked if chk_state else Qt.CheckState.Unchecked)
            self.file_table.setItem(r_idx, COL_CHECK, chk_item)
            self.file_table.setItem(r_idx, COL_PATH, QTableWidgetItem(path))
            type_item = QTableWidgetItem(type_s)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.file_table.setItem(r_idx, COL_TYPE, type_item)
        self._apply_filter_to_table()

    def set_row_enabled_state(self, r_idx, enabled):
        dis_color = self.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText)
        en_color = self.palette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText)
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
        self.close()

    def closeEvent(self, event: QCloseEvent):
        if self.conversion_thread and self.conversion_thread.isRunning():
            reply = QMessageBox.question(self, 'Confirm Exit',
                                         "A job is currently running. Are you sure you want to exit?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if self.conversion_thread:
                    self.conversion_thread.request_stop()
                    if not self.conversion_thread.wait(5000):
                        self.log_output_text.append("<font color='orange'>WARNING: Conversion thread did not stop gracefully. Forcing exit.</font>")
                        event.accept()
                        QApplication.instance().quit()
                        return
                    self.conversion_thread.join()
                else:
                    event.ignore()
            else:
                event.ignore()
        else:
            event.accept()
            QApplication.instance().quit()


def run_gui():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)

    window = ConverterWindow()
    if window.ui:
        window.ui.show()
        exit_code = app.exec()
        sys.exit(exit_code)
    else:
        print("Exiting due to UI load failure.")
        sys.exit(-1)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    # try:
    #     import config, utils, conversions, menu_definitions
    # except ImportError as e:
    #     print(f"Could not import backend modules: {e}"); sys.exit(1)
    run_gui()
