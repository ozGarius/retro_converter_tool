## Oz Converter Tool - Qt6 GUI Development Plan

This document outlines the next steps, potential enhancements, and testing procedures for the Qt6-based GUI of the converter tool.

### I. Remaining Essential Tasks

These items are crucial for achieving the core functionality intended for the GUI version:

1.  **Backend Logging Refactoring (CRITICAL):**
    * **Task:** Modify `utils.run_command`, `utils.process_file`, and all functions in `conversions.py` to capture stdout/stderr from external tools instead of printing directly.
    * **Goal:** Return captured output/errors so the `ConversionWorker` thread in `gui.py` can emit them via signals to populate the GUI's log `QTextEdit` accurately. This is essential for user feedback during conversions.
    * **Status:** `utils.py` and `conversions.py` have been refactored to support signals, but the `ConversionWorker` in `gui.py` still needs the final integration step (calling the refactored `utils.process_file` correctly).

2.  **Table Right-Click Menu:**
    * **Task:** Implement a context menu (right-click) for the `QTableWidget` in `gui.py`.
    * **Goal:** Allow users to select one or more rows and remove the corresponding files from the list (`self.table_data` and the `QTableWidget`).

3.  **Handle Audio Conversion Options (Menu 80/81):**
    * **Task:** Decide how to integrate the "Audio to Audio" and "Folder to FLAC" options into the GUI.
    * **Goal:** These currently require extra user input (formats for 80) or operate differently (folder input for 81). They might need a separate dialog or section in the GUI, distinct from the standard file-type-based conversion flow. The current GUI logic skips these.

4.  **Robust Error Handling:**
    * **Task:** Enhance error handling throughout the process.
    * **Goal:** Catch and report errors more gracefully (e.g., file permissions issues during copy/move/delete, disk space limitations, corrupt input files detected by tools, tools crashing unexpectedly). Display informative messages to the user via the GUI (dialogs or status bar/log).

5.  **Thread Cancellation/Stopping (Recommended):**
    * **Task:** Implement a mechanism to safely request the `ConversionWorker` thread to stop.
    * **Goal:** Allow users to cancel an ongoing batch conversion process without abruptly killing the application. This requires adding a flag checked within the worker's loop and potentially signalling external processes to terminate if possible. Update the `closeEvent` to use this mechanism.

6.  **Packaging/Distribution:**
    * **Task:** Plan how the application will be packaged for end-users.
    * **Goal:** Use tools like PyInstaller or cx_Freeze to create standalone executables for target platforms (e.g., Windows), ensuring all dependencies (PySide6, backend modules) and external tools (`7za.exe`, `chdman.exe`, etc.) are included correctly.

### II. Potential Improvements

These items would enhance the usability and functionality of the existing features:

* **GUI Enhancements:**
    * **Progress Indication:** Add a progress bar (either overall or potentially per-file in the table) to give better visual feedback during long conversions.
    * **Drag and Drop:** Allow users to drag files and folders directly onto the table widget to add them.
    * **Persistent Settings:** Use `QSettings` to save and load user preferences (like window size/position, settings dialog choices) between sessions.
    * **Table Customization:** Allow users to show/hide or reorder table columns.
    * **Advanced Filtering/Sorting:** Add more options for sorting the file list (e.g., by size, date) or filtering beyond just the file type.
    * **Theming:** Ensure consistent look and feel, potentially offering light/dark theme options if desired.
* **Backend Enhancements:**
    * **Configuration File:** Move tool paths and potentially default options from `config.py` to an external configuration file (e.g., INI, JSON, YAML) for easier modification by users without editing code.
    * **More Granular Error Reporting:** Modify conversion routines to return more specific error codes or messages based on the output of the external tools.

### III. New Ideas / Future Features

These are potential new capabilities to consider for future versions:

* **Batch Renaming:** Option to automatically rename output files based on patterns or metadata after successful conversion.
* **Conversion Presets:** Allow users to save and load specific combinations of settings and conversion types.
* **Queue Management:** Implement features to pause, resume, or reorder files within the conversion queue.
* **Plugin System:** Design a system to allow adding new conversion formats or tools via plugins without modifying the core code.
* **Metadata Integration:** For relevant formats (like audio, potentially some disc images), read/write metadata tags.

### IV. Testing Strategy

A thorough testing process is vital to ensure stability and correctness:

1.  **Component Testing (Manual/Unit):**
    * Test `utils.py` functions independently where possible (e.g., path normalization, temporary directory creation/cleanup logic).
    * Test individual conversion routines in `conversions.py` (potentially mocking `utils.run_command` to isolate logic).
2.  **GUI Interaction Testing (Manual):**
    * **File Loading:** Add single/multiple files, add folders (recursive/non-recursive), add mixed content, add already listed files, clear list. Test drag and drop if implemented.
    * **Table Interaction:** Select/deselect rows (single/multiple), sort columns, test right-click removal (if implemented).
    * **Filtering/Selection:** Select different file types in the dropdown, verify correct rows are enabled/disabled and checked/unchecked. Verify manual checking is prevented for disabled rows. Verify conversion dropdown populates correctly. Verify blank selection behavior.
    * **Settings Dialog:** Open dialog, change all settings, click Save, verify changes are reflected (e.g., in log messages for `COPY_LOCALLY`), reopen to confirm persistence (if `QSettings` implemented). Test Cancel button. Test validation (e.g., invalid temp path).
    * **Conversion Execution:** Run each defined conversion type with valid input files. Verify successful completion, correct output files, and informative log messages. Test converting multiple files.
    * **Log Output:** Verify log visibility toggle, clear log button. Check log content for clarity, completeness (including tool stdout/stderr), and correct error formatting.
    * **UI State:** Verify UI elements are correctly disabled during conversion and re-enabled afterwards. Test cancelling (if implemented).
    * **Window Behavior:** Test resizing (table column stretching, log area expansion), test minimum window size constraint.
3.  **Error Condition Testing (Manual):**
    * **Invalid Inputs:** Try converting corrupted or incorrect file types.
    * **Tool Errors:** Simulate external tool failures (e.g., temporarily rename `chdman.exe`) and verify errors are reported.
    * **Permissions:** Test with files/folders the application might not have read/write access to. Test scenarios where the temp directory or output directory is not writable.
    * **Edge Cases:** Use paths with spaces or special characters. Test with very large files. Test with empty input folders. Test source deletion/local copy options thoroughly.
4.  **Cross-Platform Testing (If Applicable):**
    * Run and test the application on all target operating systems (Windows, macOS, Linux) to catch platform-specific issues (path separators, tool compatibility, UI rendering).
5.  **Performance Testing:**
    * Test adding and converting a large number of files to check for performance bottlenecks or excessive memory usage.

This plan provides a roadmap for completing and refining the Qt6 GUI. Remember to prioritize the essential tasks, especially the backend logging refactoring, to get a fully functional baseline.