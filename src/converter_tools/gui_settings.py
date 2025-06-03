# converter_tools/gui_settings.py

import os
try:
    from PySide6.QtWidgets import (
        QDialog, QCheckBox, QLineEdit, QPushButton, QComboBox, QSpinBox,
        QDialogButtonBox, QFileDialog, QMessageBox, QVBoxLayout
    )
    from PySide6.QtGui import QIntValidator # Moved import here
    from PySide6.QtUiTools import QUiLoader
except ImportError as e:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app_exists = QApplication.instance()
        if not app_exists:
            temp_app = QApplication([]) 
        QMessageBox.critical(None, "Fatal Error", f"PySide6 is not installed or found for gui_settings.py: {e}")
    except Exception:
        print(f"FATAL ERROR (gui_settings.py): PySide6 not found, and QMessageBox fallback failed. {e}")
    raise 

import config

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        ui_file_path = os.path.join(os.path.dirname(__file__), "assets", "qt", "widget_settings.ui") 
        if not os.path.exists(ui_file_path):
            QMessageBox.critical(self, "Error", f"Settings UI file not found: {ui_file_path}")
            self.setup_fallback_ui() 
            return

        loader = QUiLoader()
        self.ui_container = loader.load(ui_file_path, self) 
        if not self.ui_container:
            QMessageBox.critical(self, "UI Load Error", f"Could not load widget_settings.ui: {loader.errorString()}")
            self.setup_fallback_ui()
            return
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.ui_container)
        self.setLayout(main_layout)
        self.setWindowTitle("Converter Settings")
        self.resize(720, 610)

        # Find Widgets
        self.copy_locally_checkbox = self.ui_container.findChild(QCheckBox, "copy_locally_checkbox")
        self.temp_dir_edit = self.ui_container.findChild(QLineEdit, "temp_dir_edit")
        self.temp_dir_browse_button = self.ui_container.findChild(QPushButton, "temp_dir_browse_button")
        self.chdman_threaded_processors_combo_box = self.ui_container.findChild(QComboBox, "chdman_threaded_processors_combo_box")
        self.chdman_cd_hunksize_check_box = self.ui_container.findChild(QCheckBox, "chdman_cd_hunksize_check_box")
        self.chdman_cd_hunksize_line_edit = self.ui_container.findChild(QLineEdit, "chdman_cd_hunksize_line_edit")
        self.chdman_cd_compression_check_box = self.ui_container.findChild(QCheckBox, "chdman_cd_compression_check_box")
        self.chdman_cd_compression_line_edit = self.ui_container.findChild(QLineEdit, "chdman_cd_compression_line_edit")
        self.chdman_dvd_hunksize_check_box = self.ui_container.findChild(QCheckBox, "chdman_dvd_hunksize_check_box")
        self.chdman_dvd_hunksize_line_edit = self.ui_container.findChild(QLineEdit, "chdman_dvd_hunksize_line_edit")
        self.chdman_dvd_compression_check_box = self.ui_container.findChild(QCheckBox, "chdman_dvd_compression_check_box")
        self.chdman_dvd_compression_line_edit = self.ui_container.findChild(QLineEdit, "chdman_dvd_compression_line_edit")
        self.chdman_laserdisc_hunksize_check_box = self.ui_container.findChild(QCheckBox, "chdman_laserdisc_hunksize_check_box")
        self.chdman_laserdisc_hunksize_line_edit = self.ui_container.findChild(QLineEdit, "chdman_laserdisc_hunksize_line_edit")
        self.chdman_laserdisc_compression_check_box = self.ui_container.findChild(QCheckBox, "chdman_laserdisc_compression_check_box")
        self.chdman_laserdisc_compression_line_edit = self.ui_container.findChild(QLineEdit, "chdman_laserdisc_compression_line_edit")
        self.chdman_laserdisc_startframe_check_box = self.ui_container.findChild(QCheckBox, "chdman_laserdisc_startframe_check_box")
        self.chdman_laserdisc_startframe_line_edit = self.ui_container.findChild(QLineEdit, "chdman_laserdisc_startframe_line_edit")
        self.chdman_laserdisc_inputframes_check_box = self.ui_container.findChild(QCheckBox, "chdman_laserdisc_inputframes_check_box")
        self.chdman_laserdisc_inputframes_line_edit = self.ui_container.findChild(QLineEdit, "chdman_laserdisc_inputframes_line_edit")
        self.chdman_harddisk_hunksize_check_box = self.ui_container.findChild(QCheckBox, "chdman_harddisk_hunksize_check_box")
        self.chdman_harddisk_hunksize_line_edit = self.ui_container.findChild(QLineEdit, "chdman_harddisk_hunksize_line_edit")
        self.chdman_harddisk_compression_check_box = self.ui_container.findChild(QCheckBox, "chdman_harddisk_compression_check_box")
        self.chdman_harddisk_compression_line_edit = self.ui_container.findChild(QLineEdit, "chdman_harddisk_compression_line_edit")
        self.chdman_harddisk_sector_check_box = self.ui_container.findChild(QCheckBox, "chdman_harddisk_sector_check_box")
        self.chdman_harddisk_sector_line_edit = self.ui_container.findChild(QLineEdit, "chdman_harddisk_sector_line_edit")
        self.chdman_harddisk_size_check_box = self.ui_container.findChild(QCheckBox, "chdman_harddisk_size_check_box")
        self.chdman_harddisk_size_line_edit = self.ui_container.findChild(QLineEdit, "chdman_harddisk_size_line_edit")
        self.chdman_harddisk_chs_check_box = self.ui_container.findChild(QCheckBox, "chdman_harddisk_chs_check_box")
        self.chdman_harddisk_chs_c_line_edit = self.ui_container.findChild(QLineEdit, "chdman_harddisk_chs_c_line_edit")
        self.chdman_harddisk_chs_h_line_edit = self.ui_container.findChild(QLineEdit, "chdman_harddisk_chs_h_line_edit")
        self.chdman_harddisk_chs_s_line_edit = self.ui_container.findChild(QLineEdit, "chdman_harddisk_chs_s_line_edit")
        self.chdman_harddisk_template_check_box = self.ui_container.findChild(QCheckBox, "chdman_harddisk_template_check_box")
        self.chdman_harddisk_template_line_edit = self.ui_container.findChild(QLineEdit, "chdman_harddisk_template_line_edit")
        self.chdman_raw_hunksize_check_box = self.ui_container.findChild(QCheckBox, "chdman_raw_hunksize_check_box")
        self.chdman_raw_hunksize_line_edit = self.ui_container.findChild(QLineEdit, "chdman_raw_hunksize_line_edit")
        self.chdman_raw_compression_check_box = self.ui_container.findChild(QCheckBox, "chdman_raw_compression_check_box")
        self.chdman_raw_compression_line_edit = self.ui_container.findChild(QLineEdit, "chdman_raw_compression_line_edit")
        self.chdman_verify_fix_checkbox = self.ui_container.findChild(QCheckBox, "chdman_verify_fix_checkbox")
        self.dolphintool_rvz_blocksize_combo_box = self.ui_container.findChild(QComboBox, "dolphintool_rvz_blocksize_combo_box")
        self.dolphintool_rvz_compression_combo_box = self.ui_container.findChild(QComboBox, "dolphintool_rvz_compression_combo_box")
        self.dolphintool_rvz_level_spin_box = self.ui_container.findChild(QSpinBox, "dolphintool_rvz_level_spin_box")
        self.dolphintool_wia_compression_combo_box = self.ui_container.findChild(QComboBox, "dolphintool_wia_compression_combo_box")
        self.dolphintool_wia_level_spin_box = self.ui_container.findChild(QSpinBox, "dolphintool_wia_level_spin_box")
        self.dolphintool_gcz_blocksize_combo_box = self.ui_container.findChild(QComboBox, "dolphintool_gcz_blocksize_combo_box")
        self.button_box = self.ui_container.findChild(QDialogButtonBox, "button_box") 

        self._validate_widgets() 
        self._setup_validators_and_interactive_logic()
        self.load_settings_to_ui()
        self._connect_signals()

    def _validate_widgets(self):
        if not self.button_box:
            QMessageBox.critical(self, "Settings UI Error",
                                 "The main button box (OK/Cancel) was not found in widget_settings.ui. "
                                 "Please ensure it has the objectName 'button_box'.")
            return False 
        return True

    def _setup_validators_and_interactive_logic(self):
        int_validator = QIntValidator(0, 9999999, self) 
        positive_int_validator = QIntValidator(1, 9999999, self) 

        if self.chdman_cd_hunksize_line_edit: self.chdman_cd_hunksize_line_edit.setValidator(int_validator)
        if self.chdman_dvd_hunksize_line_edit: self.chdman_dvd_hunksize_line_edit.setValidator(int_validator)
        if self.chdman_laserdisc_hunksize_line_edit: self.chdman_laserdisc_hunksize_line_edit.setValidator(int_validator)
        if self.chdman_laserdisc_startframe_line_edit: self.chdman_laserdisc_startframe_line_edit.setValidator(int_validator)
        if self.chdman_laserdisc_inputframes_line_edit: self.chdman_laserdisc_inputframes_line_edit.setValidator(positive_int_validator) 
        if self.chdman_harddisk_hunksize_line_edit: self.chdman_harddisk_hunksize_line_edit.setValidator(int_validator)
        if self.chdman_harddisk_sector_line_edit: self.chdman_harddisk_sector_line_edit.setValidator(int_validator)
        if self.chdman_harddisk_chs_c_line_edit: self.chdman_harddisk_chs_c_line_edit.setValidator(int_validator)
        if self.chdman_harddisk_chs_h_line_edit: self.chdman_harddisk_chs_h_line_edit.setValidator(int_validator)
        if self.chdman_harddisk_chs_s_line_edit: self.chdman_harddisk_chs_s_line_edit.setValidator(int_validator)
        if self.chdman_raw_hunksize_line_edit: self.chdman_raw_hunksize_line_edit.setValidator(int_validator)
        
        if self.chdman_threaded_processors_combo_box:
            self.chdman_threaded_processors_combo_box.clear() 
            self.chdman_threaded_processors_combo_box.addItem("Auto", userData="auto") 
            cpu_cores = config.CPU_COUNT # This is a module-level constant, not on settings object
            for i in range(1, cpu_cores + 1):
                self.chdman_threaded_processors_combo_box.addItem(f"{i} core(s)", userData=i)
        
        self._setup_chdman_options_group(
            self.chdman_cd_hunksize_check_box, self.chdman_cd_hunksize_line_edit, str(config.DEFAULT_SETTINGS["CHDMAN_CD_HUNKS"]),
            self.chdman_cd_compression_check_box, self.chdman_cd_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_CD_COMPRESSION_TYPES"]
        )
        self._setup_chdman_options_group(
            self.chdman_dvd_hunksize_check_box, self.chdman_dvd_hunksize_line_edit, str(config.DEFAULT_SETTINGS["CHDMAN_DVD_HUNKS"]),
            self.chdman_dvd_compression_check_box, self.chdman_dvd_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_DVD_COMPRESSION_TYPES"]
        )
        self._setup_chdman_options_group(
            self.chdman_laserdisc_hunksize_check_box, self.chdman_laserdisc_hunksize_line_edit, str(config.DEFAULT_SETTINGS["CHDMAN_LD_HUNKS"]),
            self.chdman_laserdisc_compression_check_box, self.chdman_laserdisc_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_LD_COMPRESSION_TYPES"]
        )
        self._connect_checkbox_to_lineedit_enable(self.chdman_laserdisc_startframe_check_box, [self.chdman_laserdisc_startframe_line_edit], uncheck_clears=True)
        self._connect_checkbox_to_lineedit_enable(self.chdman_laserdisc_inputframes_check_box, [self.chdman_laserdisc_inputframes_line_edit], uncheck_clears=True)

        self._setup_chdman_options_group(
            self.chdman_harddisk_hunksize_check_box, self.chdman_harddisk_hunksize_line_edit, str(config.DEFAULT_SETTINGS["CHDMAN_HD_HUNKS"]),
            self.chdman_harddisk_compression_check_box, self.chdman_harddisk_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_HD_COMPRESSION_TYPES"]
        )
        self._connect_checkbox_to_lineedit_enable(self.chdman_harddisk_sector_check_box, [self.chdman_harddisk_sector_line_edit], uncheck_clears=True)
        self._connect_checkbox_to_lineedit_enable(self.chdman_harddisk_size_check_box, [self.chdman_harddisk_size_line_edit], uncheck_clears=True)
        self._connect_checkbox_to_lineedit_enable(self.chdman_harddisk_chs_check_box, [
            self.chdman_harddisk_chs_c_line_edit, self.chdman_harddisk_chs_h_line_edit, self.chdman_harddisk_chs_s_line_edit
        ], uncheck_clears=True)
        self._connect_checkbox_to_lineedit_enable(self.chdman_harddisk_template_check_box, [self.chdman_harddisk_template_line_edit], uncheck_clears=True)
        
        self._setup_chdman_options_group(
            self.chdman_raw_hunksize_check_box, self.chdman_raw_hunksize_line_edit, str(config.DEFAULT_SETTINGS["CHDMAN_RAW_HUNKS"]),
            self.chdman_raw_compression_check_box, self.chdman_raw_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_RAW_COMPRESSION_TYPES"]
        )

        if self.dolphintool_rvz_blocksize_combo_box:
            self.dolphintool_rvz_blocksize_combo_box.clear()
            items = {"32 KiB": 32768, "64 KiB": 65536, "128 KiB": 131072, "256 KiB": 262144, "512 KiB": 524288, "1 MiB": 1048576, "2 MiB": 2097152}
            for text, data in items.items(): self.dolphintool_rvz_blocksize_combo_box.addItem(text, userData=data)
        if self.dolphintool_rvz_compression_combo_box:
            self.dolphintool_rvz_compression_combo_box.clear()
            items = {"No compression": "none", "bzip2 (slow)": "bzip2", "LZMA (slow)": "lzma", "LZMA2 (slow)": "lzma2", "Zstandard (default)": "zstd"}
            for text, data in items.items(): self.dolphintool_rvz_compression_combo_box.addItem(text, userData=data)
            self.dolphintool_rvz_compression_combo_box.currentTextChanged.connect(self._update_dolphintool_rvz_level_spinbox_state)

        if self.dolphintool_wia_compression_combo_box:
            self.dolphintool_wia_compression_combo_box.clear()
            items = {"No compression": "none", "Purge": "purge", "bzip2 (slow)": "bzip2", "LZMA (slow)": "lzma", "LZMA2 (slow)": "lzma2"}
            for text, data in items.items(): self.dolphintool_wia_compression_combo_box.addItem(text, userData=data)
            self.dolphintool_wia_compression_combo_box.currentTextChanged.connect(self._update_dolphintool_wia_level_spinbox_state)
            
        if self.dolphintool_gcz_blocksize_combo_box:
            self.dolphintool_gcz_blocksize_combo_box.clear()
            items = {"32 KiB": 32768, "64 KiB": 65536, "128 KiB": 131072, "256 KiB": 262144}
            for text, data in items.items(): self.dolphintool_gcz_blocksize_combo_box.addItem(text, userData=data)

    def _setup_chdman_options_group(self, hunk_cb, hunk_le, hunk_default_str, comp_cb, comp_le, comp_default_str):
        if hunk_cb and hunk_le:
            self._connect_checkbox_to_lineedit_enable(hunk_cb, [hunk_le], default_text=hunk_default_str, uncheck_clears=False)
            if not hunk_cb.isChecked(): hunk_le.setText(hunk_default_str)
        if comp_cb and comp_le:
            self._connect_checkbox_to_lineedit_enable(comp_cb, [comp_le], default_text=comp_default_str, uncheck_clears=False)
            if not comp_cb.isChecked(): comp_le.setText(comp_default_str)

    def _connect_checkbox_to_lineedit_enable(self, checkbox, lineedits, default_text=None, uncheck_clears=True):
        if not checkbox: return
        valid_lineedits = [le for le in lineedits if le is not None]

        def toggle_lineedit_state(checked):
            for le in valid_lineedits:
                le.setEnabled(checked)
                if not checked: 
                    if default_text is not None:
                        le.setText(default_text) 
                    elif uncheck_clears: 
                        le.clear()
                elif checked and not le.text() and default_text is not None:
                     le.setText(default_text)
        
        checkbox.toggled.connect(toggle_lineedit_state)
        toggle_lineedit_state(checkbox.isChecked())

    def _update_dolphintool_rvz_level_spinbox_state(self, compression_text_not_used): 
        if not self.dolphintool_rvz_level_spin_box or not self.dolphintool_rvz_compression_combo_box: return
        selected_compression_data = self.dolphintool_rvz_compression_combo_box.currentData() 

        current_value = self.dolphintool_rvz_level_spin_box.value()
        default_level_for_type = 5 # Default fallback

        if selected_compression_data == "none":
            self.dolphintool_rvz_level_spin_box.setEnabled(False)
        elif selected_compression_data == "zstd":
            self.dolphintool_rvz_level_spin_box.setEnabled(True)
            self.dolphintool_rvz_level_spin_box.setRange(1, 22) 
            default_level_for_type = config.DEFAULT_SETTINGS["DOLPHINTOOL_RVZ_COMPRESSION_LEVEL"] # Accessing DEFAULT_SETTINGS is fine
            self.dolphintool_rvz_level_spin_box.setValue(current_value if 1 <= current_value <= 22 else default_level_for_type)
        elif selected_compression_data in ["bzip2", "lzma", "lzma2"]:
            self.dolphintool_rvz_level_spin_box.setEnabled(True)
            self.dolphintool_rvz_level_spin_box.setRange(1, 9) 
            # default_level_for_type = 5 # Already set
            self.dolphintool_rvz_level_spin_box.setValue(current_value if 1 <= current_value <= 9 else default_level_for_type)
        else: 
            self.dolphintool_rvz_level_spin_box.setEnabled(False)

    def _update_dolphintool_wia_level_spinbox_state(self, compression_text_not_used):
        if not self.dolphintool_wia_level_spin_box or not self.dolphintool_wia_compression_combo_box: return
        selected_compression_data = self.dolphintool_wia_compression_combo_box.currentData()
        
        current_value = self.dolphintool_wia_level_spin_box.value()
        default_level_for_type = 5

        if selected_compression_data in ["none", "purge"]:
            self.dolphintool_wia_level_spin_box.setEnabled(False)
        elif selected_compression_data in ["bzip2", "lzma", "lzma2"]: 
            self.dolphintool_wia_level_spin_box.setEnabled(True)
            self.dolphintool_wia_level_spin_box.setRange(1, 9)
            default_level_for_type = config.DEFAULT_SETTINGS["DOLPHINTOOL_WIA_COMPRESSION_LEVEL"] # Accessing DEFAULT_SETTINGS is fine
            self.dolphintool_wia_level_spin_box.setValue(current_value if 1 <= current_value <= 9 else default_level_for_type)
        else:
            self.dolphintool_wia_level_spin_box.setEnabled(False)

    def _connect_signals(self):
        if self.temp_dir_browse_button:
            self.temp_dir_browse_button.clicked.connect(self.browse_temp_dir)
        if self.button_box:
            self.button_box.accepted.connect(self.accept) 
            self.button_box.rejected.connect(self.reject) 
        
        checkboxes_to_emit = [
            self.chdman_cd_hunksize_check_box, self.chdman_cd_compression_check_box,
            self.chdman_dvd_hunksize_check_box, self.chdman_dvd_compression_check_box,
            self.chdman_laserdisc_hunksize_check_box, self.chdman_laserdisc_compression_check_box,
            self.chdman_laserdisc_startframe_check_box, self.chdman_laserdisc_inputframes_check_box,
            self.chdman_harddisk_hunksize_check_box, self.chdman_harddisk_compression_check_box,
            self.chdman_harddisk_sector_check_box, self.chdman_harddisk_size_check_box,
            self.chdman_harddisk_chs_check_box, self.chdman_harddisk_template_check_box,
            self.chdman_raw_hunksize_check_box, self.chdman_raw_compression_check_box
        ]
        for cb in checkboxes_to_emit:
            if cb: cb.toggled.emit(cb.isChecked()) 

        if self.dolphintool_rvz_compression_combo_box:
            self.dolphintool_rvz_compression_combo_box.currentTextChanged.emit(self.dolphintool_rvz_compression_combo_box.currentText())
        if self.dolphintool_wia_compression_combo_box:
            self.dolphintool_wia_compression_combo_box.currentTextChanged.emit(self.dolphintool_wia_compression_combo_box.currentText())

    def setup_fallback_ui(self): 
        self.setWindowTitle("Settings Error")
        layout = QVBoxLayout(self)
        # Fallback UI should use QLineEdit or QLabel for text display
        error_label = QLineEdit("Could not load settings UI from 'widget_settings.ui'. Displaying basic fallback.")
        error_label.setReadOnly(True) # Make it non-editable
        layout.addWidget(error_label)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.reject) 
        layout.addWidget(ok_button)
        self.setLayout(layout)

    def _set_combobox_by_data(self, combobox, data_to_find):
        if not combobox: return
        for i in range(combobox.count()):
            if combobox.itemData(i) == data_to_find:
                combobox.setCurrentIndex(i)
                return
        if combobox.count() > 0: combobox.setCurrentIndex(0) 

    def load_settings_to_ui(self):
        if self.copy_locally_checkbox: self.copy_locally_checkbox.setChecked(config.settings.COPY_LOCALLY)
        if self.temp_dir_edit: self.temp_dir_edit.setText(config.settings.MAIN_TEMP_DIR)

        if self.chdman_threaded_processors_combo_box:
            if config.settings.CHDMAN_NUM_PROCESSORS_MODE == "auto":
                self._set_combobox_by_data(self.chdman_threaded_processors_combo_box, "auto")
            else: 
                self._set_combobox_by_data(self.chdman_threaded_processors_combo_box, config.settings.CHDMAN_NUM_PROCESSORS_MANUAL)
        
        if self.chdman_cd_hunksize_check_box: self.chdman_cd_hunksize_check_box.setChecked(config.settings.CHDMAN_CD_USE_CUSTOM_HUNKS)
        if self.chdman_cd_hunksize_line_edit: self.chdman_cd_hunksize_line_edit.setText(str(config.settings.CHDMAN_CD_HUNKS))
        if self.chdman_cd_compression_check_box: self.chdman_cd_compression_check_box.setChecked(config.settings.CHDMAN_CD_USE_CUSTOM_COMPRESSION)
        if self.chdman_cd_compression_line_edit: self.chdman_cd_compression_line_edit.setText(config.settings.CHDMAN_CD_COMPRESSION_TYPES)
        
        if self.chdman_dvd_hunksize_check_box: self.chdman_dvd_hunksize_check_box.setChecked(config.settings.CHDMAN_DVD_USE_CUSTOM_HUNKS)
        if self.chdman_dvd_hunksize_line_edit: self.chdman_dvd_hunksize_line_edit.setText(str(config.settings.CHDMAN_DVD_HUNKS))
        if self.chdman_dvd_compression_check_box: self.chdman_dvd_compression_check_box.setChecked(config.settings.CHDMAN_DVD_USE_CUSTOM_COMPRESSION)
        if self.chdman_dvd_compression_line_edit: self.chdman_dvd_compression_line_edit.setText(config.settings.CHDMAN_DVD_COMPRESSION_TYPES)

        if self.chdman_laserdisc_hunksize_check_box: self.chdman_laserdisc_hunksize_check_box.setChecked(config.settings.CHDMAN_LD_USE_CUSTOM_HUNKS)
        if self.chdman_laserdisc_hunksize_line_edit: self.chdman_laserdisc_hunksize_line_edit.setText(str(config.settings.CHDMAN_LD_HUNKS))
        if self.chdman_laserdisc_compression_check_box: self.chdman_laserdisc_compression_check_box.setChecked(config.settings.CHDMAN_LD_USE_CUSTOM_COMPRESSION)
        if self.chdman_laserdisc_compression_line_edit: self.chdman_laserdisc_compression_line_edit.setText(config.settings.CHDMAN_LD_COMPRESSION_TYPES)
        if self.chdman_laserdisc_startframe_check_box: self.chdman_laserdisc_startframe_check_box.setChecked(config.settings.CHDMAN_LD_USE_INPUT_START_FRAME)
        if self.chdman_laserdisc_startframe_line_edit: self.chdman_laserdisc_startframe_line_edit.setText(str(config.settings.CHDMAN_LD_INPUT_START_FRAME or ""))
        if self.chdman_laserdisc_inputframes_check_box: self.chdman_laserdisc_inputframes_check_box.setChecked(config.settings.CHDMAN_LD_USE_INPUT_FRAMES)
        if self.chdman_laserdisc_inputframes_line_edit: self.chdman_laserdisc_inputframes_line_edit.setText(str(config.settings.CHDMAN_LD_INPUT_FRAMES or ""))

        if self.chdman_harddisk_hunksize_check_box: self.chdman_harddisk_hunksize_check_box.setChecked(config.settings.CHDMAN_HD_USE_CUSTOM_HUNKS)
        if self.chdman_harddisk_hunksize_line_edit: self.chdman_harddisk_hunksize_line_edit.setText(str(config.settings.CHDMAN_HD_HUNKS))
        if self.chdman_harddisk_compression_check_box: self.chdman_harddisk_compression_check_box.setChecked(config.settings.CHDMAN_HD_USE_CUSTOM_COMPRESSION)
        if self.chdman_harddisk_compression_line_edit: self.chdman_harddisk_compression_line_edit.setText(config.settings.CHDMAN_HD_COMPRESSION_TYPES)
        if self.chdman_harddisk_sector_check_box: self.chdman_harddisk_sector_check_box.setChecked(config.settings.CHDMAN_HD_USE_SECTOR_SIZE)
        if self.chdman_harddisk_sector_line_edit: self.chdman_harddisk_sector_line_edit.setText(str(config.settings.CHDMAN_HD_SECTOR_SIZE or ""))
        if self.chdman_harddisk_size_check_box: self.chdman_harddisk_size_check_box.setChecked(config.settings.CHDMAN_HD_USE_SIZE)
        if self.chdman_harddisk_size_line_edit: self.chdman_harddisk_size_line_edit.setText(str(config.settings.CHDMAN_HD_SIZE or ""))
        if self.chdman_harddisk_chs_check_box: self.chdman_harddisk_chs_check_box.setChecked(config.settings.CHDMAN_HD_USE_CHS)
        if self.chdman_harddisk_chs_c_line_edit: self.chdman_harddisk_chs_c_line_edit.setText(str(config.settings.CHDMAN_HD_CHS_C or ""))
        if self.chdman_harddisk_chs_h_line_edit: self.chdman_harddisk_chs_h_line_edit.setText(str(config.settings.CHDMAN_HD_CHS_H or ""))
        if self.chdman_harddisk_chs_s_line_edit: self.chdman_harddisk_chs_s_line_edit.setText(str(config.settings.CHDMAN_HD_CHS_S or ""))
        if self.chdman_harddisk_template_check_box: self.chdman_harddisk_template_check_box.setChecked(config.settings.CHDMAN_HD_USE_TEMPLATE)
        if self.chdman_harddisk_template_line_edit: self.chdman_harddisk_template_line_edit.setText(config.settings.CHDMAN_HD_TEMPLATE_PATH or "")

        if self.chdman_raw_hunksize_check_box: self.chdman_raw_hunksize_check_box.setChecked(config.settings.CHDMAN_RAW_USE_CUSTOM_HUNKS)
        if self.chdman_raw_hunksize_line_edit: self.chdman_raw_hunksize_line_edit.setText(str(config.settings.CHDMAN_RAW_HUNKS))
        if self.chdman_raw_compression_check_box: self.chdman_raw_compression_check_box.setChecked(config.settings.CHDMAN_RAW_USE_CUSTOM_COMPRESSION)
        if self.chdman_raw_compression_line_edit: self.chdman_raw_compression_line_edit.setText(config.settings.CHDMAN_RAW_COMPRESSION_TYPES)

        if self.chdman_verify_fix_checkbox: self.chdman_verify_fix_checkbox.setChecked(config.settings.CHDMAN_VERIFY_FIX)

        if self.dolphintool_rvz_blocksize_combo_box: self._set_combobox_by_data(self.dolphintool_rvz_blocksize_combo_box, config.settings.DOLPHINTOOL_RVZ_BLOCKSIZE)
        if self.dolphintool_rvz_compression_combo_box: self._set_combobox_by_data(self.dolphintool_rvz_compression_combo_box, config.settings.DOLPHINTOOL_RVZ_COMPRESSION_TYPE)
        if self.dolphintool_rvz_level_spin_box: self.dolphintool_rvz_level_spin_box.setValue(config.settings.DOLPHINTOOL_RVZ_COMPRESSION_LEVEL)
        
        if self.dolphintool_wia_compression_combo_box: self._set_combobox_by_data(self.dolphintool_wia_compression_combo_box, config.settings.DOLPHINTOOL_WIA_COMPRESSION_TYPE)
        if self.dolphintool_wia_level_spin_box: self.dolphintool_wia_level_spin_box.setValue(config.settings.DOLPHINTOOL_WIA_COMPRESSION_LEVEL)

        if self.dolphintool_gcz_blocksize_combo_box: self._set_combobox_by_data(self.dolphintool_gcz_blocksize_combo_box, config.settings.DOLPHINTOOL_GCZ_BLOCKSIZE)

    def browse_temp_dir(self):
        if not self.temp_dir_edit: return
        current_path = self.temp_dir_edit.text() or config.get_default_temp_dir() # get_default_temp_dir is fine
        directory = QFileDialog.getExistingDirectory(self, "Select Temporary Directory", current_path)
        if directory:
            self.temp_dir_edit.setText(os.path.normpath(directory))

    def _get_int_from_lineedit(self, lineedit, default_if_empty=None, allow_none_if_empty_and_default_is_none=False):
        if not lineedit: 
            return default_if_empty
        text = lineedit.text().strip()
        if not text:
            return None if allow_none_if_empty_and_default_is_none and default_if_empty is None else default_if_empty
        try:
            return int(text)
        except ValueError:
            return default_if_empty

    def _get_str_from_lineedit(self, lineedit, default_if_empty=None, allow_none_if_empty_and_default_is_none=False):
        if not lineedit: return default_if_empty
        text = lineedit.text().strip()
        if not text:
            return None if allow_none_if_empty_and_default_is_none and default_if_empty is None else default_if_empty
        return text

    def accept(self):
        if self.copy_locally_checkbox: config.settings.COPY_LOCALLY = self.copy_locally_checkbox.isChecked()
        if self.temp_dir_edit:
            temp_dir_text = self.temp_dir_edit.text().strip()
            config.settings.MAIN_TEMP_DIR = temp_dir_text if temp_dir_text else config.get_default_temp_dir()
            # Validation for MAIN_TEMP_DIR path
            if not os.path.exists(config.settings.MAIN_TEMP_DIR):
                parent_dir = os.path.dirname(config.settings.MAIN_TEMP_DIR)
                if not parent_dir or not os.path.isdir(parent_dir): 
                    QMessageBox.warning(self, "Settings Error", f"Parent directory for Temp Directory does not exist or is invalid: {parent_dir}")
                    return 
            elif not os.path.isdir(config.settings.MAIN_TEMP_DIR):
                 QMessageBox.warning(self, "Settings Error", f"Temp Directory path exists but is not a directory: {config.settings.MAIN_TEMP_DIR}")
                 return

        if self.chdman_threaded_processors_combo_box:
            selected_proc_data = self.chdman_threaded_processors_combo_box.currentData()
            if selected_proc_data == "auto":
                config.settings.CHDMAN_NUM_PROCESSORS_MODE = "auto"
                config.settings.CHDMAN_NUM_PROCESSORS_MANUAL = config.DEFAULT_SETTINGS["CHDMAN_NUM_PROCESSORS_MANUAL"]
            else: 
                config.settings.CHDMAN_NUM_PROCESSORS_MODE = "manual"
                config.settings.CHDMAN_NUM_PROCESSORS_MANUAL = int(selected_proc_data)
        
        if self.chdman_cd_hunksize_check_box: config.settings.CHDMAN_CD_USE_CUSTOM_HUNKS = self.chdman_cd_hunksize_check_box.isChecked()
        config.settings.CHDMAN_CD_HUNKS = self._get_int_from_lineedit(self.chdman_cd_hunksize_line_edit, config.DEFAULT_SETTINGS["CHDMAN_CD_HUNKS"])
        if self.chdman_cd_compression_check_box: config.settings.CHDMAN_CD_USE_CUSTOM_COMPRESSION = self.chdman_cd_compression_check_box.isChecked()
        config.settings.CHDMAN_CD_COMPRESSION_TYPES = self._get_str_from_lineedit(self.chdman_cd_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_CD_COMPRESSION_TYPES"])

        if self.chdman_dvd_hunksize_check_box: config.settings.CHDMAN_DVD_USE_CUSTOM_HUNKS = self.chdman_dvd_hunksize_check_box.isChecked()
        config.settings.CHDMAN_DVD_HUNKS = self._get_int_from_lineedit(self.chdman_dvd_hunksize_line_edit, config.DEFAULT_SETTINGS["CHDMAN_DVD_HUNKS"])
        if self.chdman_dvd_compression_check_box: config.settings.CHDMAN_DVD_USE_CUSTOM_COMPRESSION = self.chdman_dvd_compression_check_box.isChecked()
        config.settings.CHDMAN_DVD_COMPRESSION_TYPES = self._get_str_from_lineedit(self.chdman_dvd_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_DVD_COMPRESSION_TYPES"])

        if self.chdman_laserdisc_hunksize_check_box: config.settings.CHDMAN_LD_USE_CUSTOM_HUNKS = self.chdman_laserdisc_hunksize_check_box.isChecked()
        config.settings.CHDMAN_LD_HUNKS = self._get_int_from_lineedit(self.chdman_laserdisc_hunksize_line_edit, config.DEFAULT_SETTINGS["CHDMAN_LD_HUNKS"])
        if self.chdman_laserdisc_compression_check_box: config.settings.CHDMAN_LD_USE_CUSTOM_COMPRESSION = self.chdman_laserdisc_compression_check_box.isChecked()
        config.settings.CHDMAN_LD_COMPRESSION_TYPES = self._get_str_from_lineedit(self.chdman_laserdisc_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_LD_COMPRESSION_TYPES"])
        if self.chdman_laserdisc_startframe_check_box: config.settings.CHDMAN_LD_USE_INPUT_START_FRAME = self.chdman_laserdisc_startframe_check_box.isChecked()
        config.settings.CHDMAN_LD_INPUT_START_FRAME = self._get_int_from_lineedit(self.chdman_laserdisc_startframe_line_edit, default_if_empty=None, allow_none_if_empty_and_default_is_none=True)
        if self.chdman_laserdisc_inputframes_check_box: config.settings.CHDMAN_LD_USE_INPUT_FRAMES = self.chdman_laserdisc_inputframes_check_box.isChecked()
        config.settings.CHDMAN_LD_INPUT_FRAMES = self._get_int_from_lineedit(self.chdman_laserdisc_inputframes_line_edit, default_if_empty=None, allow_none_if_empty_and_default_is_none=True)

        if self.chdman_harddisk_hunksize_check_box: config.settings.CHDMAN_HD_USE_CUSTOM_HUNKS = self.chdman_harddisk_hunksize_check_box.isChecked()
        config.settings.CHDMAN_HD_HUNKS = self._get_int_from_lineedit(self.chdman_harddisk_hunksize_line_edit, config.DEFAULT_SETTINGS["CHDMAN_HD_HUNKS"])
        if self.chdman_harddisk_compression_check_box: config.settings.CHDMAN_HD_USE_CUSTOM_COMPRESSION = self.chdman_harddisk_compression_check_box.isChecked()
        config.settings.CHDMAN_HD_COMPRESSION_TYPES = self._get_str_from_lineedit(self.chdman_harddisk_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_HD_COMPRESSION_TYPES"])
        if self.chdman_harddisk_sector_check_box: config.settings.CHDMAN_HD_USE_SECTOR_SIZE = self.chdman_harddisk_sector_check_box.isChecked()
        config.settings.CHDMAN_HD_SECTOR_SIZE = self._get_int_from_lineedit(self.chdman_harddisk_sector_line_edit, default_if_empty=None, allow_none_if_empty_and_default_is_none=True)
        if self.chdman_harddisk_size_check_box: config.settings.CHDMAN_HD_USE_SIZE = self.chdman_harddisk_size_check_box.isChecked()
        config.settings.CHDMAN_HD_SIZE = self._get_str_from_lineedit(self.chdman_harddisk_size_line_edit, default_if_empty=None, allow_none_if_empty_and_default_is_none=True)
        if self.chdman_harddisk_chs_check_box: config.settings.CHDMAN_HD_USE_CHS = self.chdman_harddisk_chs_check_box.isChecked()
        config.settings.CHDMAN_HD_CHS_C = self._get_int_from_lineedit(self.chdman_harddisk_chs_c_line_edit, default_if_empty=None, allow_none_if_empty_and_default_is_none=True)
        config.settings.CHDMAN_HD_CHS_H = self._get_int_from_lineedit(self.chdman_harddisk_chs_h_line_edit, default_if_empty=None, allow_none_if_empty_and_default_is_none=True)
        config.settings.CHDMAN_HD_CHS_S = self._get_int_from_lineedit(self.chdman_harddisk_chs_s_line_edit, default_if_empty=None, allow_none_if_empty_and_default_is_none=True)
        if self.chdman_harddisk_template_check_box: config.settings.CHDMAN_HD_USE_TEMPLATE = self.chdman_harddisk_template_check_box.isChecked()
        config.settings.CHDMAN_HD_TEMPLATE_PATH = self._get_str_from_lineedit(self.chdman_harddisk_template_line_edit, default_if_empty=None, allow_none_if_empty_and_default_is_none=True)

        if self.chdman_raw_hunksize_check_box: config.settings.CHDMAN_RAW_USE_CUSTOM_HUNKS = self.chdman_raw_hunksize_check_box.isChecked()
        config.settings.CHDMAN_RAW_HUNKS = self._get_int_from_lineedit(self.chdman_raw_hunksize_line_edit, config.DEFAULT_SETTINGS["CHDMAN_RAW_HUNKS"])
        if self.chdman_raw_compression_check_box: config.settings.CHDMAN_RAW_USE_CUSTOM_COMPRESSION = self.chdman_raw_compression_check_box.isChecked()
        config.settings.CHDMAN_RAW_COMPRESSION_TYPES = self._get_str_from_lineedit(self.chdman_raw_compression_line_edit, config.DEFAULT_SETTINGS["CHDMAN_RAW_COMPRESSION_TYPES"])

        if self.chdman_verify_fix_checkbox: config.settings.CHDMAN_VERIFY_FIX = self.chdman_verify_fix_checkbox.isChecked()
        
        if self.dolphintool_rvz_blocksize_combo_box: config.settings.DOLPHINTOOL_RVZ_BLOCKSIZE = self.dolphintool_rvz_blocksize_combo_box.currentData()
        if self.dolphintool_rvz_compression_combo_box: config.settings.DOLPHINTOOL_RVZ_COMPRESSION_TYPE = self.dolphintool_rvz_compression_combo_box.currentData()
        if self.dolphintool_rvz_level_spin_box: config.settings.DOLPHINTOOL_RVZ_COMPRESSION_LEVEL = self.dolphintool_rvz_level_spin_box.value()
        
        if self.dolphintool_wia_compression_combo_box: config.settings.DOLPHINTOOL_WIA_COMPRESSION_TYPE = self.dolphintool_wia_compression_combo_box.currentData()
        if self.dolphintool_wia_level_spin_box: config.settings.DOLPHINTOOL_WIA_COMPRESSION_LEVEL = self.dolphintool_wia_level_spin_box.value()

        if self.dolphintool_gcz_blocksize_combo_box: config.settings.DOLPHINTOOL_GCZ_BLOCKSIZE = self.dolphintool_gcz_blocksize_combo_box.currentData()
        
        config.save_app_settings() # This now calls config.settings.save()
        
        super().accept() 

    def reject(self):
        super().reject()
