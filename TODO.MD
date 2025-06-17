# TODO List for Oz Converters

## Completed Tasks (Session: 2024-07-23)

*   **Debug Mode Enhancements**:
    *   [x] Logging to `app_debug_YYYYMMDD_HHMMSS.log` in `./logs/` (configurable via `LOG_DIRECTORY` setting).
    *   [x] Logs include timestamps, level, module, function name, and message. Captures commands, stdout/stderr, and internal errors.
    *   [x] User prompt before temp folder cleanup when debug mode is enabled.
*   **User Interface Memory**:
    *   [x] Last used directory is persisted for file/folder dialogs (GUI & CLI) via `LAST_USED_DIRECTORY` setting.
*   **Concurrent Job Processing (UI & Settings Only)**:
    *   [x] "Jobs" menu added to GUI with "Concurrent Jobs" submenu.
    *   [x] Options for 1 to CPU count (max 10) concurrent jobs, with current value (default 2) from `CONCURRENT_JOBS` setting checked.
    *   [x] Preference saved in `converter_settings.json` and reflected in the status bar.
    *   (Note: Actual concurrent processing logic is pending).
*   **About Dialog**:
    *   [x] Comprehensive About dialog added to GUI ("Help" > "About").
    *   [x] Displays app name ("Oz Converters"), version ("1.1.0"), copyright, and Python version.
    *   [x] Dynamically lists "Tools and Libraries Used" and "Third-Party Licenses" by parsing `README.MD`.
    *   [x] Includes a clickable GitHub repository link.
*   **README.md Content for About Dialog**:
    *   [x] Ensured `README.MD` contains `### Tools and Libraries Used` and `### Third-Party Licenses` sections for the About Dialog.
*   **Initial Settings for New Features**:
    *   [x] Added `LOG_DIRECTORY` (default: `./logs/`) to `config.py`.
    *   [x] Added `LAST_USED_DIRECTORY` (default: `None`) to `config.py`.
    *   [x] Added `CONCURRENT_JOBS` (default: `2`) to `config.py`.

## Recently Resolved (Prior to this session)
*   **GDI File Parsing Bug:** Fixed issue where dependent files for .gdi formats (especially with quoted filenames containing spaces) were not correctly identified and copied to the temporary directory. This has been fully resolved.
*   **Cue File Parsing Bug:** Ensured dependent files for .cue files are correctly identified and copied (this was part of the same fix series as GDI).

## Ongoing / Partially Completed Tasks (from before this session)
*   **Backend Logging & Error Display (Refinement Needed)**:
    *   Status: Mechanism is largely in place (enhanced this session with file logging).
    *   Next: Ongoing testing across all conversion routines and error conditions to ensure all tool outputs and internal messages are captured and displayed clearly. Consider if any specific errors warrant a dialog box in addition to a log message.
*   **Further testing with all tools** to make sure they work as expected.

## Pending Tasks (Major Features)

*   **Core Functionality**:
    *   [ ] Implement actual parallel/concurrent job processing logic based on the "Concurrent Jobs" setting.
*   **Distribution & CI/CD**:
    *   [ ] Configure PyInstaller (or alternative like cx_Freeze, Nuitka) for single executable compilation.
        *   [ ] Test on target OS (Windows, macOS, Linux).
        *   [ ] Optimize for file size.
    *   [ ] Set up GitHub Actions workflow:
        *   [ ] Trigger on releases, tags, manual dispatch.
        *   [ ] Build for multiple OS.
        *   [ ] Run tests (once available) before building.
        *   [ ] Create executable artifacts and attach to GitHub releases.
        *   [ ] Implement version numbering from git tags.
*   **Testing**:
    *   [ ] Write comprehensive unit tests for new backend functionality (logging, settings, utils functions).
    *   [ ] Write integration tests for job processing (especially once concurrency is added).
    *   [ ] Write/expand UI tests for dialogs, new menu interactions, and overall GUI flow.
*   **"Get info from media" & "Verify media" Job Types**:
    *   [ ] Define these new jobs and their associated media types in `menu_definitions.py`.
    *   [ ] Create new corresponding functions in `conversions.py`.
    *   [ ] Update `gui_worker.py` to handle text-based results from these jobs.
    *   [ ] Determine how to display text output (GUI log, dialog, dedicated area).
    *   [ ] Ensure "Output Folder" UI is correctly disabled/hidden.
*   **UI Polish & Features (from original list)**:
    *   [ ] UI Settings Persistence: Use QSettings (or similar) for UI-specific preferences (window size/position, checkbox states beyond what's in `config.settings.json`, selected job/media types if desired).
    *   [ ] Drag and Drop: Allow adding files/folders by dragging them onto the file table.
    *   [ ] Theming: Light/dark theme options.
*   **Error Handling (General Review)**:
    *   [ ] Review and enhance user-friendly error messages for all features.
    *   [ ] Ensure graceful degradation if features fail (e.g., README parsing for About dialog).
*   **Documentation**:
    *   [ ] Update `README.MD` to reflect all new features, settings, and how to use them (separate from the About dialog content).
    *   [ ] Document the CLI interface and its new features.
*   **OS Compatibility**:
    *   [ ] Expand testing and ensure full support for macOS and Linux (beyond initial PyInstaller builds).

## III. New Far Future Ideas (from original list):
*   Queue Management (pause, resume, reorder).
*   Plugin System for new formats/tools.
*   .m3u creator

---
(Existing content below this line was not present in the provided TODO.MD, so this acts as a clean end.)
