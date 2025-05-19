# converter_tools/gui.py (Launcher Script - Revised)

import sys
import os

# --- Path Setup ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import the actual run_gui function from gui_main_window.py
# This makes it available as converter_tools.gui.run_gui() for converter.py
try:
    from .gui_main_window import run_gui as actual_run_gui # Rename to avoid conflict
except ImportError as e:
    print(f"FATAL ERROR: Could not import 'run_gui' from 'gui_main_window'.")
    print(f"Ensure 'gui_main_window.py' exists in the '{script_dir}' directory.")
    print(f"Python's sys.path: {sys.path}")
    print(f"Details: {e}")
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if not app: app = QApplication(sys.argv)
        QMessageBox.critical(None, "Import Error", 
                             f"Failed to load GUI components from 'gui_main_window.py'.\n\nDetails: {e}\n\n"
                             f"Please check installation and file integrity.")
    except Exception as qe:
        print(f"Could not show GUI error message: {qe}")
    sys.exit(1)
except Exception as e_unexpected:
    print(f"FATAL UNEXPECTED ERROR during import: {e_unexpected}")
    sys.exit(1)

def run_gui():
    """
    Public function to launch the GUI.
    This is called by converter.py.
    """
    print("DEBUG (gui.py launcher): Calling actual_run_gui() from gui_main_window...")
    actual_run_gui()
    print("DEBUG (gui.py launcher): actual_run_gui() has completed. Application should be closing.")

if __name__ == "__main__":
    # This block is executed if gui.py is run directly as a script.
    print("DEBUG (gui.py launcher): Running GUI directly from __main__...")
    run_gui() # Call the wrapper function
    print("DEBUG (gui.py launcher): run_gui() has completed in __main__. Python should be exiting now.")
