# -*- coding: utf-8 -*-
# /convert_tools/gui.py (PySide6 Version - v1 - Worker Logging Updated)

import sys
import os
import traceback # For detailed error reporting if needed

# Attempt to import necessary modules from PySide6
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
        QPushButton, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QComboBox, QLabel, QTextEdit, QSizePolicy, QSpacerItem, QMenuBar,
        QFileDialog, QMessageBox, QStatusBar, QDialog, QDialogButtonBox,
        QLineEdit, QSpinBox, QGroupBox # Import QGroupBox
    )
    from PySide6.QtGui import QAction, QKeySequence, QColor, QPalette
    from PySide6.QtCore import Qt, Slot, QThread, Signal # Import threading basics
except ImportError:
    print("ERROR: PySide6 is not installed.")
    print("Please install it, for example: pip install PySide6")
    sys.exit(1)

# Placeholder for importing backend logic (adjust paths if needed)
try:
    import config
    import utils
    import conversions
    import menu_definitions
except ImportError as e:
    print(f"ERROR: gui.py failed to import sibling modules.\nDetails: {e}")
    # In a real app, show this in a dialog if possible, otherwise print and exit.
    sys.exit(1)

# --- Constants ---
COL_CHECK = 0
COL_PATH = 1
COL_TYPE = 2
TABLE_HEADINGS = ['✓', ' File Path', ' Type']

# --- Settings Dialog ---
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Converter Settings")
        self.setMinimumWidth(450)

        # Main layout for the dialog
        main_layout = QVBoxLayout(self)

        # --- Core Settings Group ---
        core_group_box = QGroupBox("Core Settings")
        core_layout = QFormLayout(core_group_box) # Layout for this group

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

        main_layout.addWidget(core_group_box) # Add group to main layout

        # --- Tool-Specific Settings Group ---
        tool_group_box = QGroupBox("Tool-Specific Settings")
        tool_layout = QFormLayout(tool_group_box) # Layout for this group

        self.validate_7z_checkbox = QCheckBox("Validate 7z archive after creation")
        self.compress_level_spinbox = QSpinBox()
        self.compress_level_spinbox.setRange(1, 22)

        tool_layout.addRow(self.validate_7z_checkbox)
        tool_layout.addRow("RVZ Compression Level (1-22):", self.compress_level_spinbox)

        main_layout.addWidget(tool_group_box) # Add group to main layout

        # --- Dialog buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.load_settings()

    def load_settings(self):
        """Load current settings from the config module."""
        self.copy_locally_checkbox.setChecked(config.COPY_LOCALLY)
        self.delete_source_checkbox.setChecked(config.DELETE_SOURCE_ON_SUCCESS)
        self.validate_7z_checkbox.setChecked(config.VALIDATE_FILE)
        self.temp_dir_edit.setText(config.MAIN_TEMP_DIR)
        self.compress_level_spinbox.setValue(config.DOLPHIN_COMPRESS_LEVEL)

    def browse_temp_dir(self):
        """Open a folder dialog to select the temporary directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Temporary Directory", self.temp_dir_edit.text())
        if directory:
            self.temp_dir_edit.setText(os.path.normpath(directory)) # Normalize path

    def accept(self):
        """Save settings back to the config module (in memory) and close."""
        temp_dir = os.path.normpath(self.temp_dir_edit.text())

        # Basic validation for temp dir
        if not os.path.isdir(os.path.dirname(temp_dir)) and not os.path.exists(temp_dir):
             parent = os.path.dirname(temp_dir)
             if not parent or not os.path.isdir(parent):
                    QMessageBox.warning(self, "Settings Error", f"Invalid Temp Directory path:\n{temp_dir}\nParent directory does not exist or path is invalid.")
                    return

        # Update config module attributes (in memory only for this session)
        config.COPY_LOCALLY = self.copy_locally_checkbox.isChecked()
        config.DELETE_SOURCE_ON_SUCCESS = self.delete_source_checkbox.isChecked()
        config.VALIDATE_FILE = self.validate_7z_checkbox.isChecked()
        config.MAIN_TEMP_DIR = temp_dir
        config.DOLPHIN_COMPRESS_LEVEL = self.compress_level_spinbox.value()

        print("Settings updated for this session:") # Optional: Log changes
        print(f"  COPY_LOCALLY: {config.COPY_LOCALLY}")
        print(f"  DELETE_SOURCE_ON_SUCCESS: {config.DELETE_SOURCE_ON_SUCCESS}")
        print(f"  VALIDATE_FILE: {config.VALIDATE_FILE}")
        print(f"  MAIN_TEMP_DIR: {config.MAIN_TEMP_DIR}")
        print(f"  COMPRESS_LEVEL: {config.DOLPHIN_COMPRESS_LEVEL}")

        super().accept() # Close the dialog with accepted status


# --- Conversion Worker Thread ---
class ConversionWorker(QThread):
    status_update = Signal(str)
    output_update = Signal(str)
    error_update = Signal(str)
    finished = Signal(int, int) # success_count, fail_count

    def __init__(self, files_to_convert, conversion_details, parent=None):
        super().__init__(parent)
        self.files_to_convert = files_to_convert
        self.conversion_details = conversion_details
        # Note: Accesses config module directly, ensure it's thread-safe if modified during run
        # (Currently only modified via Settings dialog before worker starts)

    def run(self):
        """The actual conversion process runs here."""
        success_count = 0
        fail_count = 0
        total_files = len(self.files_to_convert)

        conv_func = self.conversion_details.get('func')
        fmt_out = self.conversion_details.get('format_out')
        fmt_out2 = self.conversion_details.get('format_out2')

        if not callable(conv_func):
             self.error_update.emit("Invalid conversion function selected in definition.")
             self.finished.emit(0, total_files)
             return

        try:
            for i, file_path in enumerate(self.files_to_convert):
                # Emit status before processing each file
                self.status_update.emit(f"Processing file {i+1}/{total_files}: {os.path.basename(file_path)}")
                # Emit a clear separator message for each file's log section
                self.output_update.emit(f"\n--- Processing: {file_path} ---")

                # Call the main processing function from utils, passing signals
                # This function now handles emitting detailed logs from backend operations
                success = utils.process_file(
                    file_path,
                    conv_func,
                    fmt_out,
                    fmt_out2,
                    output_signal=self.output_update, # Pass signal for normal output
                    error_signal=self.error_update    # Pass signal for errors/warnings
                )

                # Update counts based on the return value of process_file
                if success:
                    success_count += 1
                    # Emit final success message for this file
                    self.output_update.emit(f"--- Success: {os.path.basename(file_path)} ---")
                else:
                    fail_count += 1
                    # Emit final failure message for this file
                    # Specific error details should have been emitted by process_file or its sub-calls
                    self.error_update.emit(f"--- FAILED: {os.path.basename(file_path)} ---")

        except Exception as e:
            # Catch unexpected errors within the worker loop itself
            tb = traceback.format_exc() # Get traceback
            self.error_update.emit(f"Unexpected Error during conversion worker loop:\n{tb}")
            fail_count = total_files - success_count # Adjust fail count based on error
        finally:
            # Signal completion with final counts
            self.finished.emit(success_count, fail_count)


# --- Main Window Class ---
class ConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Oz Converter Tool (Qt6)")
        self.setGeometry(100, 100, 800, 600) # x, y, width, height
        self.setMinimumSize(700, 500) # Enforce minimum size

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self._create_menu_bar()
        self._create_top_bar()
        self._create_file_table()
        self._create_conversion_controls()
        self._create_log_output()
        self._create_status_bar()

        # Apply layout stretching
        self.layout.setStretchFactor(self.file_table, 1) # Table takes most vertical space
        self.layout.setStretchFactor(self.log_output_group, 0) # Log output less initially

        self.conversion_thread = None
        self.table_data = [] # Store data backing the table [[check_state, path, type], ...]
        self.current_filter_type = None # Store the currently selected file type for filtering


    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _create_top_bar(self):
        top_bar_layout = QHBoxLayout()
        self.add_files_button = QPushButton("&Add Files...")
        self.add_folder_button = QPushButton("Add F&older...")
        self.recursive_checkbox = QCheckBox("&Recursive")
        self.clear_input_button = QPushButton("&Clear Input List")

        self.add_files_button.clicked.connect(self.add_files)
        self.add_folder_button.clicked.connect(self.add_folder)
        self.clear_input_button.clicked.connect(self.clear_input_list)

        top_bar_layout.addWidget(self.add_files_button)
        top_bar_layout.addWidget(self.add_folder_button)
        top_bar_layout.addWidget(self.recursive_checkbox)
        top_bar_layout.addStretch(1)
        top_bar_layout.addWidget(self.clear_input_button)
        self.layout.addLayout(top_bar_layout)

    def _create_file_table(self):
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(len(TABLE_HEADINGS))
        self.file_table.setHorizontalHeaderLabels(TABLE_HEADINGS)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.verticalHeader().setVisible(False) # Hide row numbers

        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_PATH, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)

        self.file_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.file_table.cellClicked.connect(self.handle_cell_click) # Use generic handler

        self.layout.addWidget(self.file_table)

    def _create_conversion_controls(self):
        controls_layout = QVBoxLayout()
        h_layout1 = QHBoxLayout()
        h_layout2 = QHBoxLayout()

        self.file_type_label = QLabel("Select file type to convert:")
        self.file_type_combo = QComboBox()
        self.file_type_combo.setEnabled(False)
        self.file_type_combo.currentTextChanged.connect(self.update_ui_for_file_type)
        h_layout1.addWidget(self.file_type_label)
        h_layout1.addWidget(self.file_type_combo)

        self.conversion_label = QLabel("Select conversion:")
        self.conversion_combo = QComboBox()
        self.conversion_combo.setEnabled(False)
        self.conversion_combo.currentTextChanged.connect(self.update_convert_button_state)
        h_layout2.addWidget(self.conversion_label)
        h_layout2.addWidget(self.conversion_combo)

        self.convert_button = QPushButton("CONVERT")
        self.convert_button.setEnabled(False)
        self.convert_button.setStyleSheet("QPushButton { background-color: lightgrey; color: grey; } QPushButton:enabled { background-color: lightgreen; color: black; }")
        self.convert_button.clicked.connect(self.start_conversion)

        controls_layout.addLayout(h_layout1)
        controls_layout.addLayout(h_layout2)
        controls_layout.addWidget(self.convert_button)
        self.layout.addLayout(controls_layout)

    def _create_log_output(self):
        self.log_output_group = QWidget()
        log_layout = QVBoxLayout(self.log_output_group)
        log_layout.setContentsMargins(0,0,0,0)

        log_top_bar = QHBoxLayout()
        self.toggle_log_button = QPushButton("Show Log ▼")
        self.clear_log_button = QPushButton("Clear Output")
        self.toggle_log_button.setCheckable(True)
        self.toggle_log_button.toggled.connect(self.toggle_log_visibility)
        self.clear_log_button.clicked.connect(self.clear_log)
        log_top_bar.addWidget(self.toggle_log_button)
        log_top_bar.addStretch(1)
        log_top_bar.addWidget(self.clear_log_button)

        self.log_output_text = QTextEdit()
        self.log_output_text.setReadOnly(True)
        self.log_output_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_output_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.log_output_text.setVisible(False)

        log_layout.addLayout(log_top_bar)
        log_layout.addWidget(self.log_output_text)
        self.log_output_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.layout.addWidget(self.log_output_group)

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Add files or folders.")

    # --- Slots (Event Handlers) ---

    @Slot()
    def open_settings(self):
        dialog = SettingsDialog(self)
        # dialog.exec() blocks until closed
        if dialog.exec(): # Returns true if accepted (Save clicked)
            self.status_bar.showMessage("Settings updated for this session.")
        else:
            self.status_bar.showMessage("Settings dialog cancelled.")

    @Slot()
    def add_files(self):
        # Build filter string dynamically
        valid_ext_list = sorted(list(menu_definitions.VALID_INPUT_EXTENSIONS))
        patterns = [f"*.{ext}" for ext in valid_ext_list]
        filter_string = f"Convertible Files ({' '.join(patterns)});;All Files (*.*)"

        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", filter_string)
        if files:
            # Filter again here just in case 'All Files' was used
            valid_files = []
            for f in files:
                ext_lower = os.path.splitext(f)[1].lower().lstrip('.')
                if ext_lower in menu_definitions.VALID_INPUT_EXTENSIONS:
                    valid_files.append(f)
                else:
                    print(f"Ignoring file with unsupported extension: {f}") # Log ignored file

            if valid_files:
                self.process_added_paths(valid_files)
            else:
                 self.status_bar.showMessage("No convertible files selected.")


    @Slot()
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.process_added_paths([folder]) # process_added_paths handles scanning

    @Slot()
    def clear_input_list(self):
        self.table_data = []
        self.current_filter_type = None # Reset filter
        self.update_table_widget()
        self.update_file_type_dropdown()
        self.status_bar.showMessage("Input list cleared.")

    @Slot(int, int)
    def handle_cell_click(self, row, column):
        """Handles clicks on table cells, specifically for toggling checks."""
        if column == COL_CHECK and 0 <= row < len(self.table_data):
            # Check if the row should be checkable based on current filter
            row_type = self.table_data[row][COL_TYPE]
            is_enabled = (self.current_filter_type is None or
                          row_type.lower() == self.current_filter_type.lower())

            if is_enabled:
                current_state = self.table_data[row][COL_CHECK]
                self.table_data[row][COL_CHECK] = not current_state
                # Update only the check state visually for performance
                item = self.file_table.item(row, COL_CHECK)
                if item:
                    item.setCheckState(Qt.CheckState.Checked if not current_state else Qt.CheckState.Unchecked)
                self.update_convert_button_state()
            else:
                self.status_bar.showMessage(f"Cannot select type '{row_type}' when '{self.current_filter_type}' is filtered.", 3000) # Show for 3 secs


    @Slot(bool)
    def toggle_log_visibility(self, checked):
        self.log_output_text.setVisible(checked)
        self.toggle_log_button.setText("Hide Log ▲" if checked else "Show Log ▼")
        # Adjust layout stretch factor if desired
        # self.layout.setStretchFactor(self.log_output_group, 1 if checked else 0)

    @Slot()
    def clear_log(self):
        self.log_output_text.clear()

    @Slot(str)
    def update_ui_for_file_type(self, selected_type):
        """Update checkmarks, table visual state, and conversion dropdown based on file type."""
        self.current_filter_type = selected_type if selected_type else None

        # Auto-check rows matching selected type and enable/disable rows
        for i in range(len(self.table_data)):
            row_type = self.table_data[i][COL_TYPE]
            is_match = (self.current_filter_type is None or
                        row_type.lower() == self.current_filter_type.lower())

            # Update check state in data model
            self.table_data[i][COL_CHECK] = is_match # Check if matching, uncheck if not

            # Update visual state in the table widget
            self.set_row_enabled_state(i, is_match)
            # *** Explicitly update the visual check state here ***
            item = self.file_table.item(i, COL_CHECK)
            if item:
                item.setCheckState(Qt.CheckState.Checked if is_match else Qt.CheckState.Unchecked)


        # Update conversion dropdown
        self.conversion_combo.clear()
        possible_conversions = []
        self.gui_conversion_display_map = {} # Store map from display text to choice_num

        if self.current_filter_type:
            selected_type_lower = self.current_filter_type.lower()
            for choice_num, details in menu_definitions.CONVERSION_MAP.items():
                input_formats = details.get('formats_in', [])
                if choice_num in ['80', '81']: continue # Skip special audio

                if isinstance(input_formats, (list, tuple)) and selected_type_lower in input_formats:
                    gui_display_text = details.get('gui_text', details.get('cli_text'))
                    if gui_display_text and gui_display_text not in self.gui_conversion_display_map:
                        possible_conversions.append(gui_display_text)
                        self.gui_conversion_display_map[gui_display_text] = choice_num

            self.conversion_combo.addItems(sorted(possible_conversions))

        self.conversion_combo.setEnabled(bool(possible_conversions))
        self.update_convert_button_state()


    @Slot()
    def update_convert_button_state(self):
        """Enable convert button if a conversion is selected and files are checked."""
        conversion_selected = bool(self.conversion_combo.currentText()) and self.conversion_combo.isEnabled()
        # Check the data model for checked items
        files_checked = any(row[COL_CHECK] for row in self.table_data)
        self.convert_button.setEnabled(conversion_selected and files_checked)


    @Slot()
    def start_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            QMessageBox.warning(self, "Busy", "A conversion is already in progress.")
            return

        selected_files = [row[COL_PATH] for row in self.table_data if row[COL_CHECK]]
        selected_conversion_display = self.conversion_combo.currentText()

        # Need to handle the case where gui_conversion_display_map might not be populated yet
        if not hasattr(self, 'gui_conversion_display_map'):
             self.gui_conversion_display_map = {}

        choice_num = self.gui_conversion_display_map.get(selected_conversion_display)


        if not selected_files:
            self.status_bar.showMessage("No files selected for conversion.")
            return
        if not choice_num or choice_num not in menu_definitions.CONVERSION_MAP:
             # Check if combo text is blank, meaning no selection
             if not selected_conversion_display:
                  self.status_bar.showMessage("Please select a conversion type.")
             else:
                  self.status_bar.showMessage("Invalid conversion selected.")
             return


        conversion_details = menu_definitions.CONVERSION_MAP[choice_num]

        self.set_ui_enabled(False)
        self.status_bar.showMessage(f"Starting conversion for {len(selected_files)} file(s)...")
        self.log_output_text.clear()
        if not self.log_output_text.isVisible():
             self.toggle_log_button.setChecked(True)

        # --- Start worker thread ---
        self.conversion_thread = ConversionWorker(selected_files, conversion_details)
        self.conversion_thread.status_update.connect(self.handle_status_update)
        self.conversion_thread.output_update.connect(self.handle_output_update)
        self.conversion_thread.error_update.connect(self.handle_error_update)
        self.conversion_thread.finished.connect(self.handle_conversion_finished)
        self.conversion_thread.start()

    # --- Thread Signal Handlers ---
    @Slot(str)
    def handle_status_update(self, message):
        self.status_bar.showMessage(message)

    @Slot(str)
    def handle_output_update(self, message):
        self.log_output_text.append(message) # Use append to add new lines

    @Slot(str)
    def handle_error_update(self, message):
        # Maybe format error messages differently? Use HTML for color?
        self.log_output_text.append(f"<font color='red'>ERROR: {message}</font>")

    @Slot(int, int)
    def handle_conversion_finished(self, success_count, fail_count):
        status_msg = f"Conversion finished. Success: {success_count}, Failed: {fail_count}."
        self.status_bar.showMessage(status_msg)
        # Maybe add a final message to the log
        self.log_output_text.append(f"\n<b>{status_msg}</b>")
        self.set_ui_enabled(True)
        self.conversion_thread = None

    # --- Helper Methods ---

    def set_ui_enabled(self, enabled):
        """Enable/disable relevant UI elements during conversion."""
        self.add_files_button.setEnabled(enabled)
        self.add_folder_button.setEnabled(enabled)
        self.recursive_checkbox.setEnabled(enabled)
        self.clear_input_button.setEnabled(enabled)
        self.file_table.setEnabled(enabled)
        # Enable/disable based on content as well
        self.file_type_combo.setEnabled(enabled and bool(self.file_type_combo.count() > 1)) # count > 1 because of blank item
        self.conversion_combo.setEnabled(enabled and bool(self.conversion_combo.count()))
        if enabled:
            self.update_convert_button_state()
        else:
            self.convert_button.setEnabled(False)


    def process_added_paths(self, paths):
        """Handles newly added file/folder paths, normalizes, and filters."""
        is_recursive = self.recursive_checkbox.isChecked()
        newly_added_count = 0
        current_paths_in_table = {row[COL_PATH] for row in self.table_data}

        for item_path_raw in paths:
            # Normalize path separator early
            item_path = os.path.normpath(item_path_raw)

            if not item_path or not os.path.exists(item_path): continue

            if os.path.isfile(item_path):
                ext_lower = os.path.splitext(item_path)[1].lower().lstrip('.')
                # Ensure it's a valid convertible type AND not already in table
                if ext_lower in menu_definitions.VALID_INPUT_EXTENSIONS and item_path not in current_paths_in_table:
                    # Add with check state determined by current filter
                    is_checked = (self.current_filter_type is None or
                                  ext_lower == self.current_filter_type.lower())
                    self.table_data.append([is_checked, item_path, ext_lower.upper()])
                    newly_added_count += 1
            elif os.path.isdir(item_path):
                # Scan folder returns normalized paths already if done right
                files_in_folder = self._scan_folder(item_path, is_recursive)
                for f_path in files_in_folder:
                    if f_path not in current_paths_in_table:
                        ext_lower = os.path.splitext(f_path)[1].lower().lstrip('.')
                        # Add with check state determined by current filter
                        is_checked = (self.current_filter_type is None or
                                      ext_lower == self.current_filter_type.lower())
                        self.table_data.append([is_checked, f_path, ext_lower.upper()])
                        newly_added_count += 1

        if newly_added_count > 0:
            self.table_data.sort(key=lambda x: x[COL_PATH])
            self.update_table_widget()
            self.update_file_type_dropdown() # This cascades other UI updates

        self.status_bar.showMessage(f"{len(self.table_data)} convertible file(s) loaded. ({newly_added_count} added).")


    def _scan_folder(self, folder_path, recursive):
        """Scans folder for valid files, returns normalized paths."""
        found_files = []
        norm_folder_path = os.path.normpath(folder_path) # Normalize base path
        if not os.path.isdir(norm_folder_path):
            return found_files

        if recursive:
            for root, _, files in os.walk(norm_folder_path):
                 norm_root = os.path.normpath(root)
                 # More robust temp dir check
                 # Check against normalized config path
                 norm_temp_dir = os.path.normpath(config.MAIN_TEMP_DIR)
                 if '_temp' in norm_root or norm_temp_dir in norm_root: continue
                 for file in files:
                    ext = os.path.splitext(file)[1].lower().lstrip('.')
                    if ext in menu_definitions.VALID_INPUT_EXTENSIONS:
                        full_path = os.path.join(norm_root, file)
                        found_files.append(os.path.normpath(full_path)) # Normalize result
        else:
            try:
                for item in os.listdir(norm_folder_path):
                    full_path = os.path.join(norm_folder_path, item)
                    if os.path.isfile(full_path):
                        ext = os.path.splitext(item)[1].lower().lstrip('.')
                        if ext in menu_definitions.VALID_INPUT_EXTENSIONS:
                             found_files.append(os.path.normpath(full_path)) # Normalize result
            except OSError as e:
                self.status_bar.showMessage(f"Error scanning folder {norm_folder_path}: {e}")

        return found_files


    def update_table_widget(self):
        """Refreshes the QTableWidget from self.table_data and applies visual state."""
        self.file_table.setRowCount(0) # Clear table before redraw
        self.file_table.setRowCount(len(self.table_data))

        for row_idx, row_data in enumerate(self.table_data):
            checked_state, path, type_str = row_data

            # Determine if row should be enabled based on current filter
            is_enabled = (self.current_filter_type is None or
                          type_str.lower() == self.current_filter_type.lower())

            # Checkbox item
            chk_item = QTableWidgetItem()
            # Set checkable flag based on enabled state
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled if is_enabled else Qt.ItemFlag.ItemIsUserCheckable)
            chk_item.setCheckState(Qt.CheckState.Checked if checked_state else Qt.CheckState.Unchecked)
            self.file_table.setItem(row_idx, COL_CHECK, chk_item)

            # Path item
            path_item = QTableWidgetItem(path)
            self.file_table.setItem(row_idx, COL_PATH, path_item)

            # Type item
            type_item = QTableWidgetItem(type_str)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.file_table.setItem(row_idx, COL_TYPE, type_item)

            # Apply visual disabled state (color and flags)
            self.set_row_enabled_state(row_idx, is_enabled)


    def set_row_enabled_state(self, row_idx, enabled):
         """Sets the visual enabled/disabled state for all items in a row."""
         # Correct way to get disabled text color using ColorGroup and ColorRole
         disabled_color = self.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText)
         enabled_color = self.palette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText)

         for col_idx in range(self.file_table.columnCount()):
            item = self.file_table.item(row_idx, col_idx)
            if item:
                # Set Flags
                current_flags = item.flags()
                if enabled:
                    # Ensure ItemIsEnabled is set
                    item.setFlags(current_flags | Qt.ItemFlag.ItemIsEnabled)
                else:
                    # Ensure ItemIsEnabled is NOT set
                    item.setFlags(current_flags & ~Qt.ItemFlag.ItemIsEnabled)

                # Set Color (apply to all columns including checkbox text if applicable)
                item.setForeground(enabled_color if enabled else disabled_color)


    def update_file_type_dropdown(self):
        """Updates the file type dropdown based on files in the table."""
        current_selection = self.file_type_combo.currentText()
        self.file_type_combo.blockSignals(True) # Prevent triggering updates while modifying
        self.file_type_combo.clear()

        file_types_in_table = sorted(list(set(row[COL_TYPE] for row in self.table_data)))

        can_enable = bool(file_types_in_table)
        self.file_type_combo.setEnabled(can_enable)

        if can_enable:
            self.file_type_combo.addItems([""] + file_types_in_table) # Add blank option first
            # Try to restore previous selection if still valid
            idx = self.file_type_combo.findText(current_selection)
            if idx != -1:
                self.file_type_combo.setCurrentIndex(idx)
            # Don't automatically select first type - let user choose or leave blank
        else:
             self.current_filter_type = None # No types, clear filter

        self.file_type_combo.blockSignals(False)
        # Manually trigger update based on final state if needed
        # Avoid calling update_ui_for_file_type here if it was called by setCurrentIndex
        # Check if the text actually changed before manually calling
        if self.file_type_combo.currentText() != current_selection:
             self.update_ui_for_file_type(self.file_type_combo.currentText())
        else:
             # If selection didn't change (e.g. list cleared but selection was blank)
             # still ensure UI state is correct for the current (blank) selection
             self.update_ui_for_file_type(self.file_type_combo.currentText())


    def closeEvent(self, event):
        if self.conversion_thread and self.conversion_thread.isRunning():
            reply = QMessageBox.question(self, 'Confirm Exit',
                                         "A conversion is currently running. Are you sure you want to exit?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Add mechanism to signal thread to stop if possible
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# --- Main Execution ---
def run_gui():
    app = QApplication(sys.argv)
    # You might want to set application name, version, org for settings persistence
    # app.setOrganizationName("YourOrg")
    # app.setApplicationName("OzConverter")
    window = ConverterWindow()
    window.show()
    sys.exit(app.exec())

# Allow direct execution for testing
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    if parent_dir not in sys.path:
         sys.path.insert(0, parent_dir)
    if script_dir not in sys.path:
         sys.path.insert(0, script_dir)
    try:
        import config, utils, conversions, menu_definitions
    except ImportError:
        print("Could not import backend modules. Ensure script is run correctly relative to project structure.")
        sys.exit(1)
    run_gui()
