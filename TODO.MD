# Retro Converter Tool - TODO & Progress
This document tracks theremaining tasks, and future plans for the Retro Retro Converter Tool, featuring a Qt6 GUI.

## I. Ongoing / Partially Completed Tasks
+ Backend Logging & Error Display (Refinement Needed):
    + Status: Mechanism is largely in place.
    + Next: Thorough testing across all conversion routines and error conditions to ensure all tool outputs (stdout/stderr) and internal messages are captured comprehensively and displayed clearly and promptly in the GUI log. Consider if any specific errors warrant a dialog box in addition to a log message.
+ Further testing with all tools to make sure they work as expected.

## III. Next Steps / Remaining Tasks
+ Implement "Get info from media" & "Verify media" Job Types:
    + Define these new jobs and their associated media types in menu_definitions.py.
    + Create new corresponding functions in conversions.py (e.g., get_media_info_routine, verify_media_routine).
        + These functions will execute tools like ```chdman info```.
        + They should capture and return the text output from these tools.
    + Update gui_worker.py:
        + The ConversionWorker will need to handle jobs that return text instead of creating files.
        + Decide how to display this text output to the user (e.g., append to the main log, show in a separate read-only QTextEdit dialog, or a new dedicated area in the GUI if these jobs are frequently used) or saved to a file.
        + Ensure the "Output Folder" section in the GUI is correctly disabled/hidden when these jobs are selected.

+ Packaging/Distribution:
    + Plan and implement application packaging using tools like PyInstaller or cx_Freeze to create standalone executables for target platforms (e.g., Windows).
    + Ensure all dependencies (PySide6, backend modules) and external tools (7za.exe, chdman.exe, etc.) are correctly included in the distribution package.

+ UI Polish & Features:
    + Allow for multiple conversions to happen at the same time
    + Drag and Drop: Allow adding files/folders by dragging them onto the file table.
    + Persistent Settings: Use QSettings to save and load user preferences (window size/position, last used folders, checkbox states, selected job/media types) between sessions.
    + Theming: Light/dark theme options.

+ Expand OS to macos and linux

+ New Feature Ideas:
    + Queue Management (pause, resume, reorder).
    + Plugin System for new formats/tools.
    + .m3u creator