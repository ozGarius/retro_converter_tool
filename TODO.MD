# Retro Converter Tool - TODO & Progress
This document tracks the remaining tasks, and future plans for the Retro Converter Tool, featuring a Qt6 GUI.

## Recently Resolved
*   **GDI File Parsing Bug:** Fixed issue where dependent files for .gdi formats (especially with quoted filenames containing spaces) were not correctly identified and copied to the temporary directory. This has been fully resolved.
*   **Cue File Parsing Bug:** Ensured dependent files for .cue files are correctly identified and copied (this was part of the same fix series as GDI).

## I. Ongoing / Partially Completed Tasks
+ Backend Logging & Error Display (Refinement Needed):
    + Status: Mechanism is largely in place.
    + Next: Thorough testing across all conversion routines and error conditions to ensure all tool outputs (stdout/stderr) and internal messages are captured comprehensively and displayed clearly and promptly in the GUI log. Consider if any specific errors warrant a dialog box in addition to a log message.
+ Further testing with all tools to make sure they work as expected.

## II. Next Steps / Remaining Tasks

+ Debug Mode Enhancement (Priority 1):
    + Controlled by a setting (already partially in `config.settings.DEBUG_MODE`).
    + When enabled, prompt you with "Continue with cleanup?" dialog before temp folder cleanup.
    + Generate .log file containing timestamps, commands, outputs/results, and errors.
    + Log file naming: `app_debug_YYYYMMDD_HHMMSS.log`.
    + Save logs to user-configurable directory (default: `./logs/`, backend setting `LOG_DIRECTORY` added).

+ Implement "Get info from media" & "Verify media" Job Types:
    + Define these new jobs and their associated media types in menu_definitions.py.
    + Create new corresponding functions in conversions.py (e.g., get_media_info_routine, verify_media_routine).
        + These functions will execute commands like `chdman info`.
        + They should capture and return the text output from these commands.
    + Update gui_worker.py:
        + The system will need to handle jobs that return text instead of creating files.
        + Decide how to display this text output to you (e.g., append to the main log, show in a separate read-only QTextEdit dialog, or a new dedicated area in the GUI if these jobs are frequently used) or saved to a file.
        + Ensure the "Output Folder" section in the GUI is correctly disabled/hidden when these jobs are selected.

+ Concurrent Job Processing (Priority 2):
    + Add "Jobs" menu to main window menu bar.
    + Submenu: "Concurrent Jobs" with options 1-10 (or user input).
    + Default setting: 2 concurrent jobs (needs a new setting in `AppSettings`).
    + Save your preference.
    + Display active job count in status bar.
    + Consider adding progress indicators for each active job.

+ About Dialog (Priority 3):
    + Application name and version.
    + Copyright information.
    + Brief description.
    + Third-party licenses section.
    + Tools/libraries used (Python version, major dependencies).
    + GitHub repository link (clickable).
    + "Check for Updates" button (optional).
    + Use standard dialog framework.

+ Packaging/Distribution (Single Executable Compilation - Priority 4):
    + Create standalone executable distribution (PyInstaller recommended, alternatives: cx_Freeze, Nuitka).
    + Single file executable preferred.
    + Include all dependencies (PySide6, etc.) and external tools.
    + Test on target OS.
    + Consider file size optimization.

+ GitHub Actions Automation (Priority 4):
    + Automated build pipeline triggered on releases, tags, manual dispatch.
    + Build for multiple OS (Windows, macOS, Linux).
    + Run tests before building.
    + Create executable artifacts.
    + Attach binaries to GitHub releases.
    + Include version numbering from git tags.

+ Expand OS to macos and linux

## UI Polish & Features:
+ Persistent Settings:
    + Backend: Settings persistence in `config.py` has been refactored using an `AppSettings` class, improving robustness. Foundational support for `LOG_DIRECTORY` and `LAST_USED_DIRECTORY` has been added.
    + GUI: Still need to use QSettings (or similar) to save and load UI-specific user preferences (window size/position, last used input/output folders (see `LAST_USED_DIRECTORY`), checkbox states, selected job/media types) between sessions.
+ User Interface Memory: Remember last used input/output directory (backend support via `LAST_USED_DIRECTORY` in `config.settings`).
+ Drag and Drop: Allow adding files/folders by dragging them onto the file table.
+ Theming: Light/dark theme options.

## III. New Far Future Ideas:
+ Queue Management (pause, resume, reorder).
+ Plugin System for new formats/tools.
+ .m3u creator