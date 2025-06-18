import os
import sys
import re
import shutil # Import shutil

from PySide6.QtWidgets import (
    QDialog, QListWidget, QListWidgetItem, QLineEdit, QPushButton, QCheckBox,
    QDialogButtonBox, QLabel, QFileDialog, QMessageBox, QVBoxLayout, QWidget
)
from PySide6.QtCore import Qt, Signal, QUrl, QMimeData, QModelIndex
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QDragEnterEvent, QDropEvent

try:
    from . import utils
except ImportError:
    if __name__ != '__main__':
        print("Could not import '.utils'. Some features might be unavailable.", file=sys.stderr)
    utils = None

UI_FILE_NAME = "m3u_creator_dialog.ui"
DEFAULT_UI_FILE_PATH = os.path.join(os.path.dirname(__file__), "assets", "qt", UI_FILE_NAME)

class M3UCreatorWindow(QDialog):
    def __init__(self, parent=None, ui_file_path=None):
        super().__init__(parent)
        self.ui_content_widget = None # Initialize
        self.playlist_name_manually_edited = False

        if ui_file_path is None:
            ui_file_path = DEFAULT_UI_FILE_PATH
        print(f"M3UCreatorWindow: Attempting to load UI from: {ui_file_path}") # DEBUG

        loader = QUiLoader()

        if not os.path.exists(ui_file_path):
            print(f"M3UCreatorWindow: UI file NOT FOUND at: {ui_file_path}") # DEBUG
            QMessageBox.critical(self, "UI File Error", f"Could not find the UI file: {ui_file_path}")
            self._create_fallback_ui(); return

        try:
            print(f"M3UCreatorWindow: Loading UI file...") # DEBUG
            # Load the QWidget container, parenting it to self (the QDialog)
            self.ui_content_widget = loader.load(ui_file_path, self)
            print(f"M3UCreatorWindow: loader.load() result type: {type(self.ui_content_widget)}") # DEBUG
            if hasattr(loader, 'errorString') and loader.errorString():
                print(f"M3UCreatorWindow: loader.errorString(): '{loader.errorString()}'") # DEBUG

            if not self.ui_content_widget:
                print(f"M3UCreatorWindow: loader.load() returned None or falsy value.") # DEBUG
                err_str = loader.errorString() if hasattr(loader, 'errorString') and loader.errorString() else "Unknown QUiLoader error (loaded_ui is None)"
                QMessageBox.critical(self, "UI Load Error", f"loader.load() failed for {ui_file_path}\nError: {err_str}")
                self._create_fallback_ui(); return
            print(f"M3UCreatorWindow: self.ui_content_widget assigned, type: {type(self.ui_content_widget)}") # DEBUG

            # Set up layout for the QDialog (self)
            main_dialog_layout = QVBoxLayout(self) # Apply layout to self
            main_dialog_layout.addWidget(self.ui_content_widget)
            # self.setLayout(main_dialog_layout) # Already done by QVBoxLayout(self)

        except Exception as e:
            print(f"M3UCreatorWindow: Exception during loader.load() or layout setup: {e}") # DEBUG
            QMessageBox.critical(self, "UI Load Error Exception", f"Could not load UI file: {ui_file_path}\nException: {e}")
            self._create_fallback_ui(); return

        self.setAcceptDrops(True) # This is for the QDialog itself

        try:
            print("M3UCreatorWindow: Finding child widgets on self.ui_content_widget...") # DEBUG
            self.playlistNameLineEdit = self.ui_content_widget.findChild(QLineEdit, "playlistNameLineEdit")
            print(f"M3UCreatorWindow: playlistNameLineEdit found: {self.playlistNameLineEdit is not None}") # DEBUG

            self.fileListWidget = self.ui_content_widget.findChild(QListWidget, "fileListWidget")
            print(f"M3UCreatorWindow: fileListWidget found: {self.fileListWidget is not None}") # DEBUG

            self.addFilesButton = self.ui_content_widget.findChild(QPushButton, "addFilesButton")
            print(f"M3UCreatorWindow: addFilesButton found: {self.addFilesButton is not None}") # DEBUG

            self.removeSelectedButton = self.ui_content_widget.findChild(QPushButton, "removeSelectedButton")
            print(f"M3UCreatorWindow: removeSelectedButton found: {self.removeSelectedButton is not None}") # DEBUG

            self.moveFilesCheckBox = self.ui_content_widget.findChild(QCheckBox, "moveFilesCheckBox")
            print(f"M3UCreatorWindow: moveFilesCheckBox found: {self.moveFilesCheckBox is not None}") # DEBUG

            self.hiddenFolderCheckBox = self.ui_content_widget.findChild(QCheckBox, "hiddenFolderCheckBox")
            print(f"M3UCreatorWindow: hiddenFolderCheckBox found: {self.hiddenFolderCheckBox is not None}") # DEBUG

            self.warningLabel = self.ui_content_widget.findChild(QLabel, "warningLabel")
            print(f"M3UCreatorWindow: warningLabel found: {self.warningLabel is not None}") # DEBUG

            self.buttonBox = self.ui_content_widget.findChild(QDialogButtonBox, "buttonBox")
            print(f"M3UCreatorWindow: buttonBox found: {self.buttonBox is not None}") # DEBUG

            critical_elements = {"playlistNameLineEdit": self.playlistNameLineEdit, "fileListWidget": self.fileListWidget,"addFilesButton": self.addFilesButton, "removeSelectedButton": self.removeSelectedButton,"moveFilesCheckBox": self.moveFilesCheckBox, "hiddenFolderCheckBox": self.hiddenFolderCheckBox,"warningLabel": self.warningLabel, "buttonBox": self.buttonBox,}
            missing_elements = [name for name, el in critical_elements.items() if el is None]
            if missing_elements:
                print(f"M3UCreatorWindow: Missing critical UI elements on ui_content_widget: {missing_elements}") # DEBUG
                self.ui_content_widget = None # Mark main content as failed
                QMessageBox.critical(self, "UI Element Error", f"Critical UI elements not found in UI file: {', '.join(missing_elements)}")
                self._create_fallback_ui(); return
        except Exception as e: # Catch other errors during findChild etc.
            print(f"M3UCreatorWindow: Exception during findChild or critical element check: {e}") # DEBUG
            self.ui_content_widget = None # Mark main content as failed
            QMessageBox.critical(self, "Unexpected UI Linkage Error", f"An error occurred while linking UI elements: {e}")
            self._create_fallback_ui(); return

        # Set window title directly on the QDialog
        self.setWindowTitle("M3U Playlist Creator")

        self.hiddenFolderCheckBox.setEnabled(False); self.warningLabel.setVisible(False)
        self.fileListWidget.setDragEnabled(True); self.fileListWidget.setDropIndicatorShown(True)
        self.fileListWidget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.fileListWidget.setDefaultDropAction(Qt.DropAction.MoveAction)
        # self.addFilesButton.clicked.connect(self._add_files) # Old connection
        if hasattr(self, 'addFilesButton') and self.addFilesButton: # Check if button exists
            self.addFilesButton.clicked.connect(self._add_files)
        self.removeSelectedButton.clicked.connect(self._remove_selected_files)

        if self.playlistNameLineEdit:
            self.playlistNameLineEdit.textChanged.connect(self._on_playlist_name_text_changed)
        if self.fileListWidget and self.fileListWidget.model():
            self.fileListWidget.model().rowsMoved.connect(self._on_list_reordered)

        if self.buttonBox:
            # Attempt to get the Ok button using the StandardButton enum value
            # PySide6 QDialogButtonBox.Ok should be QDialogButtonBox.StandardButton.Ok
            ok_button_enum = getattr(QDialogButtonBox, 'Ok', None) # Direct access if aliased (dummy might do this)
            if ok_button_enum is None and hasattr(QDialogButtonBox, 'StandardButton'): # Standard enum access
                ok_button_enum = getattr(QDialogButtonBox.StandardButton, 'Ok', None)

            if ok_button_enum is not None:
                ok_button = self.buttonBox.button(ok_button_enum)
                if ok_button:
                    ok_button.setText("Create M3U Playlist")
            else: # Fallback for safety, though should not happen with real Qt or good dummies
                print("M3UCreatorWindow: Warning - Could not determine QDialogButtonBox.Ok enum value.", file=sys.stderr)

            self.buttonBox.accepted.connect(self.accept)
            self.buttonBox.rejected.connect(self.reject)

        if hasattr(self, 'moveFilesCheckBox') and self.moveFilesCheckBox:
            self.moveFilesCheckBox.toggled.connect(self._on_move_files_toggled)

        # Debug prints for key widget properties (visibility, size) - BEFORE setMinimumSize and adjustSize
        if self.playlistNameLineEdit:
            print(f"M3UCreatorWindow __init__ before setMinimumSize: playlistNameLineEdit.isVisible(): {self.playlistNameLineEdit.isVisible()}, .size(): {self.playlistNameLineEdit.size().width()}x{self.playlistNameLineEdit.size().height()}")
        if self.fileListWidget:
            print(f"M3UCreatorWindow __init__ before setMinimumSize: fileListWidget.isVisible(): {self.fileListWidget.isVisible()}, .size(): {self.fileListWidget.size().width()}x{self.fileListWidget.size().height()}")
        print(f"M3UCreatorWindow __init__ before setMinimumSize: self.isVisible(): {self.isVisible()} (dialog itself), .size(): {self.size().width()}x{self.size().height()}")

        self.setMinimumSize(500, 400) # <--- ADD THIS LINE
        print(f"M3UCreatorWindow __init__ after setMinimumSize: self.minimumSize(): {self.minimumSize().width()}x{self.minimumSize().height()}, self.size(): {self.size().width()}x{self.size().height()}") # DEBUG

        self.adjustSize()

        print(f"M3UCreatorWindow __init__ after adjustSize: self.isVisible(): {self.isVisible()}, .size(): {self.size().width()}x{self.size().height()}")
    # --- End of the main try block in __init__ ---
    # The except blocks and _create_fallback_ui calls follow this.
    # Note: The actual except blocks are part of the __init__ method structure and are not shown here for brevity,
    # but the self.adjustSize() call and its surrounding prints are within the main try, before those excepts.

    def _create_fallback_ui(self):
        print(">>> M3UCreatorWindow: _create_fallback_ui() CALLED <<<") # DEBUG
        if hasattr(self, 'ui_content_widget') and self.ui_content_widget is not None:
             if hasattr(self.ui_content_widget, 'hide'): self.ui_content_widget.hide()
        self.ui_content_widget = None # Clear the problematic UI content widget

        print("Creating fallback UI for M3UCreatorWindow.", file=sys.stderr)
        self.setWindowTitle("M3U Creator (UI Load Failed)")
        current_layout = self.layout() # Get layout of self (QDialog)
        if current_layout is not None: QWidget().setLayout(current_layout)
        fallback_label = QLabel("UI file could not be loaded or is corrupted. Limited functionality.", self)
        fallback_layout = QVBoxLayout(self); fallback_layout.addWidget(fallback_label)
        self.setLayout(fallback_layout); self.resize(350,150)

    def _on_playlist_name_text_changed(self, text):
        if self.playlistNameLineEdit and not self.playlistNameLineEdit.signalsBlocked():
            self.playlist_name_manually_edited = True

    def _update_playlist_name_suggestion(self):
        if not self.playlistNameLineEdit or not self.fileListWidget : return
        if self.playlist_name_manually_edited and self.playlistNameLineEdit.text().strip() != "": return
        if self.fileListWidget.count() > 0:
            first_item_path = self.fileListWidget.item(0).data(Qt.ItemDataRole.UserRole)
            base_name = os.path.splitext(os.path.basename(first_item_path))[0]
            # cleaned_name = self._temporary_clean_filename(base_name)
            if utils and hasattr(utils, 'clean_filename_for_playlist'):
                cleaned_name = utils.clean_filename_for_playlist(base_name)
            else:
                # Fallback if utils or the specific function is not available
                print("Warning: utils.clean_filename_for_playlist not available. Using basic cleaning.", file=sys.stderr)
                # Basic fallback (e.g. just the basename or minimal regex)
                name_temp = re.sub(r'\s*\[.*?\]\s*', '', base_name, flags=re.IGNORECASE) # Minimal clean
                cleaned_name = name_temp.strip() if name_temp else "playlist"
            current_text = self.playlistNameLineEdit.text()
            if current_text != cleaned_name:
                self.playlistNameLineEdit.blockSignals(True)
                self.playlistNameLineEdit.setText(cleaned_name)
                self.playlistNameLineEdit.blockSignals(False)
            self.playlist_name_manually_edited = False
        else:
            if self.playlistNameLineEdit.text() != "":
                self.playlistNameLineEdit.blockSignals(True)
                self.playlistNameLineEdit.clear()
                self.playlistNameLineEdit.blockSignals(False)
            self.playlist_name_manually_edited = False

    def _add_files(self):
        if not self.fileListWidget:
            QMessageBox.warning(self, "UI Error", "File list widget is not available.")
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Add", "", "All Files (*.*)")
        if files:
            self._add_files_to_list(files)

    def _add_files_to_list(self, file_paths: list[str]):
        if not self.fileListWidget: QMessageBox.warning(self, "UI Error", "File list widget is not available."); return
        added_count = 0
        for path in file_paths:
            norm_path = os.path.normpath(path)
            if not os.path.isfile(norm_path): continue
            is_duplicate = False
            for i in range(self.fileListWidget.count()):
                item = self.fileListWidget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == norm_path: is_duplicate = True; break
            if not is_duplicate:
                listItem = QListWidgetItem(); listItem.setText(os.path.basename(norm_path))
                listItem.setData(Qt.ItemDataRole.UserRole, norm_path)
                listItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled)
                self.fileListWidget.addItem(listItem); added_count += 1
        if added_count > 0: self._update_playlist_name_suggestion()

    def _remove_selected_files(self):
        if not self.fileListWidget: QMessageBox.warning(self, "UI Error", "File list widget is not available."); return
        selected_items = self.fileListWidget.selectedItems()
        if not selected_items: return
        for item in selected_items: self.fileListWidget.takeItem(self.fileListWidget.row(item))
        self._update_playlist_name_suggestion()

    def _on_list_reordered(self, parent: QModelIndex, start: int, end: int, destination: QModelIndex, row: int):
        self._update_playlist_name_suggestion()

    def dragEnterEvent(self, event: QDragEnterEvent):
        mime_data = event.mimeData();
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile() and os.path.isfile(os.path.normpath(url.toLocalFile())):
                    event.acceptProposedAction(); return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            paths_to_add = []
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_path = os.path.normpath(url.toLocalFile())
                    if os.path.isfile(file_path): paths_to_add.append(file_path)
            if paths_to_add: self._add_files_to_list(paths_to_add); event.acceptProposedAction(); return
        event.ignore()

    def _on_move_files_toggled(self, checked: bool):
        if hasattr(self, 'hiddenFolderCheckBox') and self.hiddenFolderCheckBox:
            self.hiddenFolderCheckBox.setEnabled(checked)
            if not checked:
                # If the main "move" option is unchecked, also uncheck and disable the "hidden" option
                self.hiddenFolderCheckBox.setChecked(False)

        if hasattr(self, 'warningLabel') and self.warningLabel:
            self.warningLabel.setVisible(checked)

    def accept(self):
        if not all([self.playlistNameLineEdit, self.fileListWidget,
                    self.moveFilesCheckBox, self.hiddenFolderCheckBox, self.buttonBox]):
            QMessageBox.critical(self, "UI Error", "Essential UI components are not available. Cannot proceed.")
            return

        playlist_name = self.playlistNameLineEdit.text().strip()
        if not playlist_name:
            QMessageBox.warning(self, "Input Error", "Playlist name cannot be empty.")
            return

        list_of_file_paths = []
        for i in range(self.fileListWidget.count()):
            item = self.fileListWidget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole):
                list_of_file_paths.append(str(item.data(Qt.ItemDataRole.UserRole)))

        if not list_of_file_paths:
            QMessageBox.warning(self, "Input Error", "No files in the list to create a playlist.")
            return

        move_files_checked = self.moveFilesCheckBox.isChecked()
        hidden_checked = self.hiddenFolderCheckBox.isChecked()

        if move_files_checked:
            yes_button = QMessageBox.StandardButton.Yes
            no_button = QMessageBox.StandardButton.No

            reply = QMessageBox.question(self, "Confirm Move",
                                         "Files will be MOVED from their original locations to a new folder. "
                                         "This action is permanent.\n\nAre you sure you want to continue?",
                                         yes_button | no_button,
                                         no_button)
            if reply == no_button:
                return

        show_dirs_only_option = getattr(QFileDialog.Option, 'ShowDirsOnly', 1)
        if hasattr(QFileDialog.Option, 'DontUseNativeDialog'):
            show_dirs_only_option |= getattr(QFileDialog.Option, 'DontUseNativeDialog', 0)


        base_save_directory = QFileDialog.getExistingDirectory(self, "Select Base Directory for Playlist/Folder", options=show_dirs_only_option)
        if not base_save_directory:
            return

        m3u_file_path = ""
        paths_for_m3u = []

        if move_files_checked:
            new_folder_path = os.path.join(base_save_directory, playlist_name)

            if os.path.exists(new_folder_path):
                if os.path.isfile(new_folder_path) or (os.path.isdir(new_folder_path) and os.listdir(new_folder_path)):
                    QMessageBox.critical(self, "Folder Exists",
                                         f"The path '{new_folder_path}' already exists as a file or non-empty folder. "
                                         "Please choose a different playlist name or base directory.")
                    return

            try:
                os.makedirs(new_folder_path, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Folder Creation Error", f"Could not create folder: {new_folder_path}\nError: {e}")
                return

            if hidden_checked:
                print(f"INFO: Placeholder - Would attempt to make folder hidden: {new_folder_path}")
                if utils and hasattr(utils, 'set_folder_hidden_attribute'):
                    try:
                        utils.set_folder_hidden_attribute(new_folder_path)
                    except Exception as e_hide:
                        QMessageBox.warning(self, "Hiding Failed", f"Could not make folder hidden: {e_hide}")
                elif utils is None:
                     QMessageBox.warning(self, "Hiding Skipped", "Utils module not available for hiding folder.")

            moved_file_basenames = []
            failed_moves = []
            for src_path in list_of_file_paths:
                dest_filename = os.path.basename(src_path)
                dest_path = os.path.join(new_folder_path, dest_filename)
                try:
                    shutil.move(src_path, dest_path)
                    moved_file_basenames.append(dest_filename)
                except Exception as e_move:
                    failed_moves.append(f"{src_path} (Error: {e_move})")

            paths_for_m3u = moved_file_basenames
            m3u_file_path = os.path.join(new_folder_path, playlist_name + ".m3u")

            if failed_moves:
                QMessageBox.warning(self, "Move Errors",
                                    "Some files could not be moved:\n\n" + "\n".join(failed_moves) +
                                    "\n\nThe M3U will only contain successfully moved files.")

        else:
            proposed_m3u_path = os.path.join(base_save_directory, playlist_name + ".m3u")
            selected_m3u_path, _ = QFileDialog.getSaveFileName(self, "Save M3U Playlist As...",
                                                               proposed_m3u_path,
                                                               "M3U Playlist Files (*.m3u *.m3u8)")
            if not selected_m3u_path:
                return
            m3u_file_path = selected_m3u_path
            paths_for_m3u = list_of_file_paths

        if not m3u_file_path:
            QMessageBox.critical(self, "Error", "M3U file path was not determined.")
            return

        try:
            with open(m3u_file_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for p_for_m3u_content in paths_for_m3u:
                    extinf_display_name = os.path.basename(p_for_m3u_content) if os.path.isabs(p_for_m3u_content) else p_for_m3u_content
                    f.write(f"#EXTINF:-1,{extinf_display_name}\n")
                    f.write(f"{p_for_m3u_content}\n")

            QMessageBox.information(self, "Success", f"M3U Playlist '{m3u_file_path}' created successfully.")
            super().accept()

        except Exception as e_write:
            QMessageBox.critical(self, "M3U Write Error", f"Could not write M3U file: {m3u_file_path}\nError: {e_write}")

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = M3UCreatorWindow()
    if dialog.ui is not None:
        dialog.show()
        sys.exit(app.exec())
    elif isinstance(dialog, QDialog) and dialog.layout() is not None:
        print("Showing fallback UI as main UI failed to load.", file=sys.stderr)
        dialog.show()
        sys.exit(app.exec())
    else:
        print("Dialog initialization failed critically. Cannot show window.", file=sys.stderr)
        sys.exit(1)
