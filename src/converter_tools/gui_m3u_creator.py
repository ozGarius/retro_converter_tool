import os
import sys
import re
import shutil # Import shutil

try:
    from PySide6.QtWidgets import (
        QDialog, QListWidget, QListWidgetItem, QLineEdit, QPushButton, QCheckBox,
        QDialogButtonBox, QLabel, QFileDialog, QMessageBox, QVBoxLayout, QWidget
    )
    from PySide6.QtCore import Qt, Signal, QUrl, QMimeData, QModelIndex
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtGui import QDragEnterEvent, QDropEvent
except ImportError:
    print("PySide6 not found. Basic UI elements might not work.", file=sys.stderr)
    # Dummy classes
    class QDialog: pass; class QListWidget: pass; class QListWidgetItem: pass;
    class QLineEdit: pass; class QPushButton: pass; class QCheckBox: pass;
    class QDialogButtonBox:
        StandardButtonOk = 0x00000400
        StandardButton = type("StandardButton", (), {"Ok": StandardButtonOk})
        Ok = StandardButtonOk
        accepted = Signal(); rejected = Signal();
        def button(self, role): return None
    class QLabel: pass;
    class QFileDialog:
        Option = type("Option", (), {"ShowDirsOnly": 1, "DontUseNativeDialog": 2})
        @staticmethod
        def getExistingDirectory(parent, caption, directory="", options=None): return ""
        @staticmethod
        def getSaveFileName(parent, caption, directory="", filter="", selectedFilter=None, options=None): return "", ""
    class QMessageBox:
        Information = 0; Warning = 1; Critical = 2; Question =3;
        Yes = 0x00004000; No = 0x00010000;
        StandardButton = type("StandardButton", (), {"Yes": Yes, "No": No, "Ok": 0x00000400, "Cancel": 0x00400000})
        @staticmethod
        def critical(parent, title, text, buttons=StandardButton.Ok, defaultButton=None): pass
        @staticmethod
        def warning(parent, title, text, buttons=StandardButton.Ok, defaultButton=None): pass
        @staticmethod
        def information(parent, title, text, buttons=StandardButton.Ok, defaultButton=None): pass
        @staticmethod
        def question(parent, title, text, buttons=(StandardButton.Yes | StandardButton.No), defaultButton=StandardButton.No): return QMessageBox.No
    class QVBoxLayout: pass; class QWidget: pass;
    class Qt: class WindowFlags: pass; class DropAction: pass; class ItemDataRole: UserRole = 1000;
               class ItemFlag: ItemIsSelectable = 1; ItemIsEnabled = 32; ItemIsDragEnabled = 4;
               class CheckState: pass;
    class Signal: def __init__(self, *args): pass;
    class QUrl: pass; class QMimeData: pass; class QUiLoader: pass;
    class QDragEnterEvent: pass; class QDropEvent: pass; class QModelIndex: pass;

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
        self.ui = None
        self.playlist_name_manually_edited = False

        if ui_file_path is None:
            ui_file_path = DEFAULT_UI_FILE_PATH
        loader = QUiLoader()
        if not os.path.exists(ui_file_path):
            QMessageBox.critical(self, "UI File Error", f"Could not find the UI file: {ui_file_path}")
            self._create_fallback_ui(); return
        try:
            loaded_ui = loader.load(ui_file_path, self)
            if not loaded_ui:
                err_str = loader.errorString() if hasattr(loader, 'errorString') else "Unknown QUiLoader error"
                QMessageBox.critical(self, "UI Load Error", f"loader.load() failed for {ui_file_path}\nError: {err_str}")
                self._create_fallback_ui(); return
            self.ui = loaded_ui
        except Exception as e:
            QMessageBox.critical(self, "UI Load Error Exception", f"Could not load UI file: {ui_file_path}\nException: {e}")
            self._create_fallback_ui(); return

        self.setAcceptDrops(True)
        try:
            self.playlistNameLineEdit = self.ui.findChild(QLineEdit, "playlistNameLineEdit")
            self.fileListWidget = self.ui.findChild(QListWidget, "fileListWidget")
            self.addFilesButton = self.ui.findChild(QPushButton, "addFilesButton")
            self.removeSelectedButton = self.ui.findChild(QPushButton, "removeSelectedButton")
            self.moveFilesCheckBox = self.ui.findChild(QCheckBox, "moveFilesCheckBox")
            self.hiddenFolderCheckBox = self.ui.findChild(QCheckBox, "hiddenFolderCheckBox")
            self.warningLabel = self.ui.findChild(QLabel, "warningLabel")
            self.buttonBox = self.ui.findChild(QDialogButtonBox, "buttonBox")
            critical_elements = {"playlistNameLineEdit": self.playlistNameLineEdit, "fileListWidget": self.fileListWidget,"addFilesButton": self.addFilesButton, "removeSelectedButton": self.removeSelectedButton,"moveFilesCheckBox": self.moveFilesCheckBox, "hiddenFolderCheckBox": self.hiddenFolderCheckBox,"warningLabel": self.warningLabel, "buttonBox": self.buttonBox,}
            missing_elements = [name for name, el in critical_elements.items() if el is None]
            if missing_elements: self.ui = None; raise NameError(f"UI elements not found: {', '.join(missing_elements)}.")
        except NameError as e: QMessageBox.critical(self, "UI Element Error", str(e)); self._create_fallback_ui(); return
        except Exception as e: self.ui = None; QMessageBox.critical(self, "Unexpected UI Linkage Error", f"An error linking UI: {e}"); self._create_fallback_ui(); return

        if not self.windowTitle() and hasattr(self.ui, 'windowTitle') and self.ui.windowTitle(): self.setWindowTitle(self.ui.windowTitle())
        elif not self.windowTitle(): self.setWindowTitle("M3U Playlist Creator")

        self.hiddenFolderCheckBox.setEnabled(False); self.warningLabel.setVisible(False)
        self.fileListWidget.setDragEnabled(True); self.fileListWidget.setDropIndicatorShown(True)
        self.fileListWidget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.fileListWidget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.addFilesButton.clicked.connect(self._add_files)
        self.removeSelectedButton.clicked.connect(self._remove_selected_files)

        if self.playlistNameLineEdit: self.playlistNameLineEdit.textChanged.connect(self._on_playlist_name_text_changed)
        if self.fileListWidget and self.fileListWidget.model(): self.fileListWidget.model().rowsMoved.connect(self._on_list_reordered)

        if self.buttonBox:
            ok_std_button_val = getattr(QDialogButtonBox.StandardButton, 'Ok', None)
            if ok_std_button_val is None:
                 ok_std_button_val = getattr(QDialogButtonBox, 'Ok', None)

            if ok_std_button_val is not None:
                 ok_button = self.buttonBox.button(ok_std_button_val)
                 if ok_button: ok_button.setText("Create M3U Playlist")
            self.buttonBox.accepted.connect(self.accept)

        # Connect moveFilesCheckBox toggled signal
        if hasattr(self, 'moveFilesCheckBox') and self.moveFilesCheckBox:
            self.moveFilesCheckBox.toggled.connect(self._on_move_files_toggled)

    def _create_fallback_ui(self):
        if self.ui is not None:
             if hasattr(self.ui, 'hide'): self.ui.hide()
        self.ui = None
        print("Creating fallback UI for M3UCreatorWindow.", file=sys.stderr)
        self.setWindowTitle("M3U Creator (UI Load Failed)")
        current_layout = self.layout()
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
