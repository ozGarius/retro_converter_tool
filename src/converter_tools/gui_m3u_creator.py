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
    print("PySide6 not found. Using dummy classes for parsing.", file=sys.stderr)

    # --- Begin Dummy PySide6 Classes ---

    class Signal:
        def __init__(self, *args):
            pass

        # Add connect, disconnect, emit if needed by any calling code, e.g.
        # def connect(self, slot): pass
        # def disconnect(self, slot): pass
        # def emit(self, *args): pass

    class QObject: # Base for many Qt classes, useful for dummying
        def __init__(self, parent=None):
            self.parent = parent
        def signalsBlocked(self): # Used by playlistNameLineEdit
            return False
        def blockSignals(self, block: bool): # Used by playlistNameLineEdit
            pass
        def findChild(self, type, name): # Used by self.ui
            return None
        def menuBar(self): # Used by self.ui (if it were a QMainWindow)
            return None # Or a dummy MenuBar instance
        def windowTitle(self): # Used by self
            return ""
        def setWindowTitle(self, title): # Used by self
            pass
        # Add objectName, setObjectName if needed

    class QWidget(QObject): # Many UI elements are QWidgets
        def __init__(self, parent=None):
            super().__init__(parent)
            self._layout = None # For dummy setLayout/layout
            self._visible = True
            self._enabled = True

        def setLayout(self, layout):
            self._layout = layout

        def layout(self):
            return self._layout

        def show(self):
            self._visible = True

        def hide(self):
            self._visible = False

        def setVisible(self, visible:bool):
            self._visible = visible

        def setEnabled(self, enabled:bool):
            self._enabled = enabled

        def mapToGlobal(self, point): # If context menus were dummied
            return point

        def rect(self): # If sizes were needed
            return (0,0,100,30) # x,y,w,h

        def styleSheet(self): return ""
        def setStyleSheet(self, sheet): pass
        def update(self): pass
        def repaint(self): pass
        def font(self): return None # Dummy QFont
        def setFont(self, font): pass
        def close(self): pass
        def deleteLater(self): pass


    class QDialog(QWidget):
        Accepted = 1
        Rejected = 0
        def __init__(self, parent=None):
            super().__init__(parent)
            self.accepted = Signal()
            self.rejected = Signal()
            self._result = QDialog.Rejected

        def exec(self): # exec_ was for older Qt/PyQt
            self.show()
            # In a real dummy event loop, this would block
            return self._result

        def accept(self):
            self._result = QDialog.Accepted
            self.accepted.emit()
            self.close()

        def reject(self):
            self._result = QDialog.Rejected
            self.rejected.emit()
            self.close()

        def setResult(self, res):
            self._result = res

        def done(self, res):
            self.setResult(res)
            self.close()

    class QListWidgetItem:
        def __init__(self, text=None, listview=None):
            self._text = text if text is not None else ""
            self._data = {}
            self._flags = 0 # Dummy flags

        def text(self):
            return self._text

        def setText(self, text):
            self._text = text

        def data(self, role):
            return self._data.get(role)

        def setData(self, role, value):
            self._data[role] = value

        def flags(self):
            return self._flags

        def setFlags(self, flags):
            self._flags = flags

    class QListWidget(QWidget):
        class DragDropMode:
            NoDragDrop = 0
            DragOnly = 1
            DropOnly = 2
            DragDrop = 3
            InternalMove = 4

        def __init__(self, parent=None):
            super().__init__(parent)
            self._items = []
            self.itemDoubleClicked = Signal(QListWidgetItem) # Example signal
            self._model = QStandardItemModel() # Dummy model

        def addItem(self, item_or_text):
            if isinstance(item_or_text, QListWidgetItem):
                self._items.append(item_or_text)
            else:
                self._items.append(QListWidgetItem(str(item_or_text)))

        def item(self, row):
            return self._items[row] if 0 <= row < len(self._items) else None

        def count(self):
            return len(self._items)

        def selectedItems(self): # Simplified: returns all for dummy
            return list(self._items)

        def takeItem(self, row):
            if 0 <= row < len(self._items):
                return self._items.pop(row)
            return None

        def row(self, item):
            try: return self._items.index(item)
            except ValueError: return -1

        def model(self): # Returns a dummy model
            return self._model

        def setDragEnabled(self, enable): pass
        def setDropIndicatorShown(self, enable): pass
        def setDragDropMode(self, mode): pass
        def setDefaultDropAction(self, action): pass
        def clear(self): self._items = []


    class QLineEdit(QWidget):
        def __init__(self, content="", parent=None):
            super().__init__(parent)
            self._text = content
            self.textChanged = Signal(str) # Takes string
            self.editingFinished = Signal()

        def text(self):
            return self._text

        def setText(self, text):
            new_text = str(text)
            if self._text != new_text:
                self._text = new_text
                self.textChanged.emit(self._text)

        def clear(self):
            self.setText("")

        def strip(self): # Not a real QLineEdit method, but used in app code
            return self._text.strip()


    class QPushButton(QWidget): # QAbstractButton is the true parent
        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self._text = text
            self.clicked = Signal() # No arguments for clicked usually

        def setText(self, text):
            self._text = text

        def text(self):
            return self._text

    class QCheckBox(QWidget): # QAbstractButton is the true parent
        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self._text = text
            self._checked = False
            self.toggled = Signal(bool) # Takes boolean

        def isChecked(self):
            return self._checked

        def setChecked(self, checked_bool):
            is_changing = self._checked != bool(checked_bool)
            self._checked = bool(checked_bool)
            if is_changing:
                self.toggled.emit(self._checked)

        def text(self): return self._text
        def setText(self, text): self._text = text


    class QDialogButtonBox(QWidget):
        class StandardButton: # Nested class for enum
            NoButton = 0x00000000
            Ok = 0x00000400
            Save = 0x00000800
            SaveAll = 0x00001000
            Open = 0x00002000
            Yes = 0x00004000
            No = 0x00010000
            Abort = 0x00040000
            Retry = 0x00080000
            Ignore = 0x00100000
            Close = 0x00200000
            Cancel = 0x00400000
            Discard = 0x00800000
            Help = 0x01000000
            Apply = 0x02000000
            Reset = 0x04000000
            RestoreDefaults = 0x08000000

        # Make aliases available directly on QDialogButtonBox for convenience
        Ok = StandardButton.Ok; Cancel = StandardButton.Cancel; Yes = StandardButton.Yes; No = StandardButton.No

        def __init__(self, parent=None):
            super().__init__(parent)
            self.accepted = Signal()
            self.rejected = Signal()
            self._buttons = {} # Store dummy buttons

        def button(self, role_or_button): # role is StandardButton value
            # This dummy just returns a new QPushButton if not found.
            # A more complex dummy might store buttons added via addStandardButton.
            if role_or_button not in self._buttons:
                 self._buttons[role_or_button] = QPushButton(f"DummyBtn_{role_or_button}")
            return self._buttons[role_or_button]

        def setStandardButtons(self, buttons_bitmask): pass # For dummy
        def addButton(self, text_or_button, role=None): pass # For dummy


    class QLabel(QWidget):
        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self._text = text

        def setText(self, text):
            self._text = str(text)

        def text(self):
            return self._text

        def setVisible(self, visible): # Already in QWidget dummy
            super().setVisible(visible)


    class QFileDialog(QDialog): # Inherits from QDialog for exec()
        class Option: # Nested class for QFileDialog.Option
            ShowDirsOnly = 1
            DontResolveSymlinks = 2
            DontConfirmOverwrite = 4
            DontUseNativeDialog = 8 # Value might vary, example
            ReadOnly = 16
            HideNameFilterDetails = 32

        def __init__(self, parent=None, caption="", directory="", filter=""):
            super().__init__(parent)
            self.setWindowTitle(caption)
            self._directory = directory
            self._filter = filter
            self._selected_files = []

        @staticmethod
        def getExistingDirectory(parent=None, caption="", directory="", options=Option.ShowDirsOnly):
            # This dummy would need user input in a real test, or return a fixed path
            print(f"Dummy QFileDialog.getExistingDirectory called (parent={parent}, caption='{caption}', dir='{directory}')")
            return "/dummy/selected/directory"

        @staticmethod
        def getSaveFileName(parent=None, caption="", directory="", filter="", selectedFilter=None, options=0):
            print(f"Dummy QFileDialog.getSaveFileName called (parent={parent}, caption='{caption}', dir='{directory}')")
            return ("/dummy/save/file.m3u", "M3U Playlist Files (*.m3u *.m3u8)")

        @staticmethod
        def getOpenFileNames(parent=None, caption="", directory="", filter="", selectedFilter=None, options=0):
            print(f"Dummy QFileDialog.getOpenFileNames called (parent={parent}, caption='{caption}', dir='{directory}')")
            return (["/dummy/path/file1.txt", "/dummy/path/file2.img"], "All Files (*.*)")

        def filesSelected(self): # Not a real method, but to simulate
            return self._selected_files


    class QMessageBox(QDialog): # Inherits from QDialog for exec()
        # Use StandardButton values from QDialogButtonBox for consistency
        NoButton = QDialogButtonBox.StandardButton.NoButton
        Ok = QDialogButtonBox.StandardButton.Ok
        Save = QDialogButtonBox.StandardButton.Save
        # ... copy all required buttons from QDialogButtonBox.StandardButton
        Yes = QDialogButtonBox.StandardButton.Yes
        No = QDialogButtonBox.StandardButton.No
        Abort = QDialogButtonBox.StandardButton.Abort
        Retry = QDialogButtonBox.StandardButton.Retry
        Ignore = QDialogButtonBox.StandardButton.Ignore
        Close = QDialogButtonBox.StandardButton.Close
        Cancel = QDialogButtonBox.StandardButton.Cancel
        Discard = QDialogButtonBox.StandardButton.Discard
        Help = QDialogButtonBox.StandardButton.Help
        Apply = QDialogButtonBox.StandardButton.Apply
        Reset = QDialogButtonBox.StandardButton.Reset
        RestoreDefaults = QDialogButtonBox.StandardButton.RestoreDefaults

        # Icon enum
        NoIcon = 0
        Information = 1 # Value might vary
        Warning = 2     # Value might vary
        Critical = 3    # Value might vary
        Question = 4    # Value might vary

        # For static methods, parent is the first arg
        @staticmethod
        def critical(parent, title, text, buttons=Ok, defaultButton=NoButton):
            print(f"DUMMY QMessageBox.CRITICAL: '{title}' - '{text}'")
            # In a test, one might want to simulate a button press
            return buttons # Or a specific button if interaction is needed for tests

        @staticmethod
        def warning(parent, title, text, buttons=Ok, defaultButton=NoButton):
            print(f"DUMMY QMessageBox.WARNING: '{title}' - '{text}'")
            return buttons

        @staticmethod
        def information(parent, title, text, buttons=Ok, defaultButton=NoButton):
            print(f"DUMMY QMessageBox.INFORMATION: '{title}' - '{text}'")
            return buttons

        @staticmethod
        def question(parent, title, text, buttons=(Yes | No), defaultButton=No):
            print(f"DUMMY QMessageBox.QUESTION: '{title}' - '{text}'")
            # This dummy needs to return one of the button values passed in `buttons`
            if buttons & defaultButton: return defaultButton
            if buttons & QMessageBox.Yes: return QMessageBox.Yes # Default to Yes if No not specified
            return QMessageBox.No # Fallback

    class QVBoxLayout(QObject): # QLayout is QObject, not QWidget
        def __init__(self, parent_or_widget=None): # Can take a parent QWidget
            super().__init__(parent_or_widget if not isinstance(parent_or_widget, QWidget) else None)
            if isinstance(parent_or_widget, QWidget):
                parent_or_widget.setLayout(self)
            self._widgets = []
        def addWidget(self, widget):
            self._widgets.append(widget)
        def insertWidget(self, index, widget):
            self._widgets.insert(index, widget)
        # Add other layout methods if needed: addLayout, addStretch, etc.

    class QStandardItemModel(QObject): # For fileListWidget.model()
        def __init__(self, parent=None):
            super().__init__(parent)
            self.rowsMoved = Signal(QModelIndex, int, int, QModelIndex, int)
            # Other signals: itemChanged, rowsInserted, etc.

    class Qt:
        class WindowFlags: # Empty for dummy
            pass
        class DropAction: # Used by fileListWidget.setDefaultDropAction
            CopyAction = 1
            MoveAction = 2
            LinkAction = 4
            IgnoreAction = 0
        class ItemDataRole:
            UserRole = 1000 # Or Qt.UserRole if Qt was fully dummied
        class ItemFlag:
            NoItemFlags = 0
            ItemIsSelectable = 1
            ItemIsEditable = 2
            ItemIsDragEnabled = 4
            ItemIsDropEnabled = 8
            ItemIsUserCheckable = 16
            ItemIsEnabled = 32
            ItemIsTristate = 64
        class CheckState:
            Unchecked = 0
            PartiallyChecked = 1
            Checked = 2
        # Other Qt enums if needed (e.g. AlignmentFlag, Key, etc.)
        # For Qt.UserRole if directly used (instead of ItemDataRole.UserRole)
        UserRole = ItemDataRole.UserRole


    class QUrl:
        def __init__(self, url_string=""):
            self._url_string = url_string
            self._is_local = url_string.startswith("file:")
        def isLocalFile(self):
            return self._is_local
        def toLocalFile(self):
            if self._is_local:
                # Simplified, real parsing is more complex (file:///path, file:/path)
                prefix = "file://"
                if self._url_string.startswith(prefix):
                    path = self._url_string[len(prefix):]
                    if sys.platform.startswith("win") and path.startswith("/"): # "file:///C:/path"
                        path = path[1:] # Remove leading / for C:/
                    return path
            return self._url_string # Fallback

    class QMimeData:
        def __init__(self):
            self._urls = []
            self._text = ""
        def hasUrls(self):
            return bool(self._urls)
        def urls(self):
            return self._urls
        def setUrls(self, urls_list_of_qurl): # Takes list of QUrl
            self._urls = urls_list_of_qurl
        def text(self): return self._text
        def setText(self, text): self._text = text
        def hasText(self): return bool(self._text)
        # Other formats: hasHtml, html, etc.

    class QUiLoader:
        def __init__(self):
            self._error_string = ""
        def load(self, ui_file_path_or_qfile, parentWidget=None):
            # This dummy cannot actually load .ui files.
            # It needs to return a QWidget-like object for self.ui to be assigned.
            # For testing, it could return a pre-defined dummy widget structure.
            # If ui_file_path_or_qfile is specific, can return specific dummy.
            print(f"DUMMY QUiLoader.load('{ui_file_path_or_qfile}') called.")
            # For the app to proceed, it must return an object that has findChild.
            # A simple QWidget (or our dummy QObject/QWidget) can work if findChild is dummied there.

            # If the main code does `self.ui = loader.load(...)` and then `self.ui.findChild(...)`,
            # this dummy load must return something that has `findChild`.
            # Simplest is to return a QWidget/QObject that has a dummy findChild.
            # The dummy QObject already has findChild.

            # Check if the ui_file_path exists for a more realistic dummy
            if isinstance(ui_file_path_or_qfile, str) and not os.path.exists(ui_file_path_or_qfile):
                self._error_string = f"UI file not found: {ui_file_path_or_qfile}"
                return None # Simulate load failure

            # Return a generic QObject/QWidget that can act as self.ui
            # The calling code will then use self.ui.findChild to get actual elements.
            # Our dummy QObject.findChild returns None, so the main code's error handling
            # for missing UI elements will trigger. This is acceptable for a basic dummy.
            return QWidget() # Or QObject() if QWidget has too many methods to dummy

        def errorString(self):
            return self._error_string

    class QDragEnterEvent: # QDropEvent and QDragMoveEvent are similar
        def __init__(self, mime_data=None):
            self._mime_data = mime_data if mime_data else QMimeData()
            self._accepted = False
        def mimeData(self):
            return self._mime_data
        def acceptProposedAction(self):
            self._accepted = True
        def ignore(self):
            self._accepted = False
        # pos(), proposedAction(), possibleActions(), etc.

    class QDropEvent(QDragEnterEvent): # Similar structure
        def __init__(self, mime_data=None):
            super().__init__(mime_data)
        # dropAction(), setDropAction()

    class QModelIndex: # Used as type hint for rowsMoved signal
        def __init__(self):
            pass
        # isValid(), row(), column(), parent(), data(), etc.

    # --- End Dummy PySide6 Classes ---
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
        print(f"M3UCreatorWindow: Attempting to load UI from: {ui_file_path}") # DEBUG

        loader = QUiLoader()

        if not os.path.exists(ui_file_path):
            print(f"M3UCreatorWindow: UI file NOT FOUND at: {ui_file_path}") # DEBUG
            QMessageBox.critical(self, "UI File Error", f"Could not find the UI file: {ui_file_path}")
            self._create_fallback_ui(); return

        try:
            print(f"M3UCreatorWindow: Loading UI file...") # DEBUG
            loaded_ui = loader.load(ui_file_path, self)
            print(f"M3UCreatorWindow: loader.load() result type: {type(loaded_ui)}") # DEBUG
            if hasattr(loader, 'errorString') and loader.errorString(): # Check if errorString is not empty
                print(f"M3UCreatorWindow: loader.errorString(): '{loader.errorString()}'") # DEBUG

            if not loaded_ui:
                print(f"M3UCreatorWindow: loader.load() returned None or falsy value.") # DEBUG
                err_str = loader.errorString() if hasattr(loader, 'errorString') and loader.errorString() else "Unknown QUiLoader error (loaded_ui is None)"
                QMessageBox.critical(self, "UI Load Error", f"loader.load() failed for {ui_file_path}\nError: {err_str}")
                self._create_fallback_ui(); return
            self.ui = loaded_ui
            print(f"M3UCreatorWindow: self.ui assigned, type: {type(self.ui)}") # DEBUG
        except Exception as e:
            print(f"M3UCreatorWindow: Exception during loader.load(): {e}") # DEBUG
            QMessageBox.critical(self, "UI Load Error Exception", f"Could not load UI file: {ui_file_path}\nException: {e}")
            self._create_fallback_ui(); return

        self.setAcceptDrops(True)

        try:
            print("M3UCreatorWindow: Finding child widgets...") # DEBUG
            self.playlistNameLineEdit = self.ui.findChild(QLineEdit, "playlistNameLineEdit")
            print(f"M3UCreatorWindow: playlistNameLineEdit found: {self.playlistNameLineEdit is not None}") # DEBUG

            self.fileListWidget = self.ui.findChild(QListWidget, "fileListWidget")
            print(f"M3UCreatorWindow: fileListWidget found: {self.fileListWidget is not None}") # DEBUG

            self.addFilesButton = self.ui.findChild(QPushButton, "addFilesButton")
            print(f"M3UCreatorWindow: addFilesButton found: {self.addFilesButton is not None}") # DEBUG

            self.removeSelectedButton = self.ui.findChild(QPushButton, "removeSelectedButton")
            print(f"M3UCreatorWindow: removeSelectedButton found: {self.removeSelectedButton is not None}") # DEBUG

            self.moveFilesCheckBox = self.ui.findChild(QCheckBox, "moveFilesCheckBox")
            print(f"M3UCreatorWindow: moveFilesCheckBox found: {self.moveFilesCheckBox is not None}") # DEBUG

            self.hiddenFolderCheckBox = self.ui.findChild(QCheckBox, "hiddenFolderCheckBox")
            print(f"M3UCreatorWindow: hiddenFolderCheckBox found: {self.hiddenFolderCheckBox is not None}") # DEBUG

            self.warningLabel = self.ui.findChild(QLabel, "warningLabel")
            print(f"M3UCreatorWindow: warningLabel found: {self.warningLabel is not None}") # DEBUG

            self.buttonBox = self.ui.findChild(QDialogButtonBox, "buttonBox")
            print(f"M3UCreatorWindow: buttonBox found: {self.buttonBox is not None}") # DEBUG

            critical_elements = {"playlistNameLineEdit": self.playlistNameLineEdit, "fileListWidget": self.fileListWidget,"addFilesButton": self.addFilesButton, "removeSelectedButton": self.removeSelectedButton,"moveFilesCheckBox": self.moveFilesCheckBox, "hiddenFolderCheckBox": self.hiddenFolderCheckBox,"warningLabel": self.warningLabel, "buttonBox": self.buttonBox,}
            missing_elements = [name for name, el in critical_elements.items() if el is None]
            if missing_elements:
                print(f"M3UCreatorWindow: Missing critical UI elements: {missing_elements}") # DEBUG
                self.ui = None; raise NameError(f"UI elements not found: {', '.join(missing_elements)}.")
        except NameError as e: QMessageBox.critical(self, "UI Element Error", str(e)); self._create_fallback_ui(); return
        except Exception as e: self.ui = None; QMessageBox.critical(self, "Unexpected UI Linkage Error", f"An error linking UI: {e}"); self._create_fallback_ui(); return

        if not self.windowTitle() and hasattr(self.ui, 'windowTitle') and self.ui.windowTitle(): self.setWindowTitle(self.ui.windowTitle())
        elif not self.windowTitle(): self.setWindowTitle("M3U Playlist Creator")

        self.hiddenFolderCheckBox.setEnabled(False); self.warningLabel.setVisible(False)
        self.fileListWidget.setDragEnabled(True); self.fileListWidget.setDropIndicatorShown(True)
        self.fileListWidget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.fileListWidget.setDefaultDropAction(Qt.DropAction.MoveAction)
        # self.addFilesButton.clicked.connect(self._add_files) # Old connection
        if hasattr(self, 'addFilesButton') and self.addFilesButton: # Check if button exists
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

        # Debug prints for key widget properties (visibility, size) - BEFORE adjustSize
        if self.playlistNameLineEdit: # Assuming self.playlistNameLineEdit could be None if UI setup failed
            print(f"M3UCreatorWindow __init__ before adjustSize: playlistNameLineEdit.isVisible(): {self.playlistNameLineEdit.isVisible()}, .size(): {self.playlistNameLineEdit.size().width()}x{self.playlistNameLineEdit.size().height()}")
        if self.fileListWidget:
            print(f"M3UCreatorWindow __init__ before adjustSize: fileListWidget.isVisible(): {self.fileListWidget.isVisible()}, .size(): {self.fileListWidget.size().width()}x{self.fileListWidget.size().height()}")
        print(f"M3UCreatorWindow __init__ before adjustSize: self.isVisible(): {self.isVisible()} (dialog itself), .size(): {self.size().width()}x{self.size().height()}")

        self.adjustSize() # THE FIX: Add this line

        print(f"M3UCreatorWindow __init__ after adjustSize: self.isVisible(): {self.isVisible()}, .size(): {self.size().width()}x{self.size().height()}")
    # --- End of the main try block in __init__ ---
    # The except blocks and _create_fallback_ui calls follow this.
    # Note: The actual except blocks are part of the __init__ method structure and are not shown here for brevity,
    # but the self.adjustSize() call and its surrounding prints are within the main try, before those excepts.

    def _create_fallback_ui(self):
        print(">>> M3UCreatorWindow: _create_fallback_ui() CALLED <<<") # DEBUG
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
