# Converter Tool - TODO & Progress
This document tracks the development progress, remaining tasks, and future plans for the Oz Converter Tool, featuring a Qt6 GUI.

## I. Completed Milestones & Major Features
The following significant features and refactoring efforts have been implemented:

+ Major GUI Redesign (from Screenshot):
    + UI loaded from .ui file (main_window.ui).
    + New layout with distinct sections (Job, Input files, Output Folder) using QGroupBox.
    * Dynamic Job/Media Type selection logic.
    + Dynamic updates for Input/Output file type labels and the main action button text.
    + Comprehensive Output Folder selection logic, including "Output in same folder" and conditional visibility.
    + New Output Section Checkboxes: "Overwrite existing files," "Delete input files after completing job," "Output in same folder."
    + Interactive "Select input file types" button with a checkable menu for filtering.
    + Interactive "Select output file type" button with a menu to choose the primary output format.

+ Backend Refinements:
    + Standardized logging in utils.py and conversions.py using _emit_or_print for GUI and console.
    + Archive Handling: Compression routines in conversions.py now auto-extract supported input archives.
    + Flexible Dolphin Output: compress_dolphin_routine in conversions.py supports multiple output formats (RVZ, GCZ, VIA) based on GUI selection.
    + Explicit Output Directory: utils.process_file and utils.move_files now correctly handle user-specified output locations.
    + File Overwrite Logic: utils.py respects the "Overwrite existing files" setting.

+ GUI Functionality & Polish:
    + Table Right-Click Context Menu: Implemented for file list management (select all, clear selection, remove, clear all).
    + Thread Cancellation/Stopping: ConversionWorker can be requested to stop, and closeEvent handles this.
    + Auto-selecting newly added files in the table.
    + Table rows visually enabled/disabled based on active input filters.
    + Corrected file path and type display when adding folders.
    + Improved application exit behavior.
    + Adjusted table header spacing for a cleaner look.

+ Restructured cli:
    + Remove the audio portion as it's not part of the project anymore.
    + cli menu should be restructured in Compress and Extract and should follow the flow of the gui:
        1. Choose one of the compress function, extract functions or convert function
        2. Choose the type of input file
        3. Choose the input file/folder
        4. Choose the type of output file and the options (ex. overwrite, delete input on successfull covertion, copy locally)
        5. Choose an output folder if not output in the same folder

## II. Ongoing / Partially Completed Tasks
1. Robust Error Handling (General):
    + Status: Basic try-except blocks are in place in utils.py and ConversionWorker.
    + Next:
        + Implement more specific error detection (e.g., insufficient disk space before starting a job, specific exit codes from command-line tools if they provide them).
        + Refine how critical errors are presented to the user (e.g., when to use a QMessageBox vs. just the log).

2. Backend Logging & Error Display (Refinement Needed):
    + Status: Mechanism is largely in place.
    + Next: Thorough testing across all conversion routines and error conditions to ensure all tool outputs (stdout/stderr) and internal messages are captured comprehensively and displayed clearly and promptly in the GUI log. Consider if any specific errors warrant a dialog box in addition to a log message.

## III. Next Steps / Remaining Tasks
1. Implement "Get info from media" & "Verify media" Job Types:
    + Define these new jobs and their associated media types in menu_definitions.py.
        + output_ext will likely be None or [].
        + requires_output_folder will be False.
    + Create new corresponding functions in conversions.py (e.g., get_media_info_routine, verify_media_routine).
        + These functions will execute tools like chdman info or chdman verify -i <input>.
        + They should capture and return the text output from these tools.
    + Update gui.py:
        + The ConversionWorker will need to handle jobs that return text instead of creating files.
        + Decide how to display this text output to the user (e.g., append to the main log, show in a separate read-only QTextEdit dialog, or a new dedicated area in the GUI if these jobs are frequently used).
        + Ensure the "Output Folder" section in the GUI is correctly disabled/hidden when these jobs are selected.

2. Refine "Extract Archive to Folder" Functionality:
    + Current: extract_archive_to_folder_routine in conversions.py extracts files to the temp_dir.
    + Needed: utils.process_file needs to be enhanced to correctly handle the case where format_out is None or empty (signifying a folder output).
        + It should move the entire contents of the temp_dir (where the archive was extracted) to the final_output_destination_base.
        + Consider creating a subfolder within final_output_destination_base named after the original archive (e.g., output_folder/my_archive_files/). utils.move_files might need adaptation or a new helper for this directory content move.

3. Packaging/Distribution:
    + Plan and implement application packaging using tools like PyInstaller or cx_Freeze to create standalone executables for target platforms (e.g., Windows).
    + Ensure all dependencies (PySide6, backend modules) and external tools (7za.exe, chdman.exe, etc.) are correctly included in the distribution package.

## IV. Deferred / Out of Scope (For Current Phase)
Audio Conversion Options: Removed from conversions.py as per recent decision.

## V. Potential Future Enhancements (Lower Priority / From Original TODO)
+ UI Polish & Features:
    + Progress Indication: Add a QProgressBar (overall or per-file) for long conversions.
    + Drag and Drop: Allow adding files/folders by dragging them onto the file table.
    + Persistent Settings: Use QSettings to save and load user preferences (window size/position, last used folders, checkbox states, selected job/media types) between sessions.
    + Advanced Filtering/Sorting in Table: More options for the file list.
    + Theming: Light/dark theme options.

+ Backend Enhancements:
    + External Configuration File: Move tool paths and default options from config.py to an INI, JSON, or YAML file for easier user modification.

+ New Feature Ideas:
    + Batch Renaming.
    + Conversion Presets.
    + Queue Management (pause, resume, reorder).
    + Plugin System for new formats/tools.
    + Metadata Integration.

## VI. Testing Strategy (Ongoing)
Continue with a comprehensive testing approach:
1. Component Testing: Test individual functions, especially new ones in conversions.py and utils.py.
2. GUI Interaction Testing (Manual):
    + Thoroughly test all UI elements: job/media selection, file adding (single, folder, recursive), filtering, table interactions (selection, context menu), output options, settings dialog.
    + Verify dynamic UI updates (labels, button states, button text).
3. Conversion Execution Testing:
    + Test all defined job/media type combinations with valid sample files.
    + Verify correct output files, output locations, and handling of overwrite/delete options.
    + Confirm log messages are accurate and complete.
4. Error Condition Testing (Manual):
    + Invalid/corrupted input files.
    + Missing external tools (temporarily rename one to test).
    + Permissions issues (non-writable output/temp directories).
    + Edge cases (paths with spaces, very large files, empty input folders).
5. Cross-Platform Testing (If Applicable): Test on all target OS.
6. Performance Testing: Test with a large number of files.
    + This updated TODO list should provide a clear roadmap for the next stages of development!