# Retro Converter Tool

## Overview

The Retro Converter Tool is a Python-based application designed to simplify the conversion and management of various media formats, particularly focusing on disc images (CD, DVD, GameCube/Wii), hard disk images, and archives. It provides both a Graphical User Interface (GUI) built with PySide6 and a Command-Line Interface (CLI) for flexibility.

The tool leverages external utilities like CHDMAN (for CHD creation/extraction), DolphinTool (for GameCube/Wii formats like RVZ, GCZ, WIA), and 7-Zip (for archive handling) to perform its operations.

**Note:**
* Currently, this tool is primarily designed and tested for **Windows operating systems**, due to its reliance on Windows-specific executables for some external tools (e.g., `.exe` files).
* There will be bugs, not all features have been fully tested yet.


## Features

* **Multiple Job Types**:
    * Compress media to formats like CHD, RVZ, GCZ, WIA.
    * Extract media from formats like CHD to ISO, CUE/BIN, IMG.
    * Get information from media files (e.g., CHD info).
    * Verify media integrity (e.g., CHD verification).
    * Convert between archive formats (e.g., ZIP/RAR to 7Z).
    * Extract archives to folders.
* **Graphical User Interface (GUI)**:
    * User-friendly interface for selecting jobs, media types, and files.
    * Batch processing of multiple files.
    * Dynamic UI updates based on job/media selection.
    * Input file filtering by extension.
    * Output type selection for supported jobs.
    * Configurable output folder options (including output to the same folder as input).
    * Options to overwrite existing files or delete input files upon successful conversion.
    * Detailed logging of operations.
    * Progress bars for ongoing conversions.
    * Cancellable conversion jobs.
    * Configurable settings via a dedicated settings dialog.
* **Command-Line Interface (CLI)**:
    * Supports all core conversion functionalities.
    * Job-based workflow similar to the GUI.
    * Option to specify input paths and other parameters via command-line arguments.
* **Flexible Configuration**:
    * Settings are managed via `converter_settings.json` for easy modification.
    * Customizable paths for external tools.
    * Detailed options for CHDMAN (hunk sizes, compression types, processors) and DolphinTool (block sizes, compression levels/types).
* **Archive Handling**:
    * Automatic extraction of supported input archives (`.7z`, `.zip`, `.rar`, `.gz`) before processing the contained media.
* **Robust File Operations**:
    * Option to copy files locally to a temporary directory before processing (recommended for network drives).
    * Safe deletion of source files (sends to Recycle Bin/Trash where possible).
    * Handles existing output files by overwriting or renaming.

## Future features


## Requirements

* Python 3.x
* PySide6 (`pip install PySide6`)
* `send2trash` (optional, for sending files to Recycle Bin/Trash: `pip install send2trash`)
* External Tools (must be placed in `converter_tools/ext/`):
    * `7za.exe` (7-Zip command-line executable)
    * `chdman.exe` (from MAME tools)
    * `DolphinTool.exe`
    * `maxcso.exe` (for CSO compression, if used)
    * `recycle.exe` (optional, for sending files to Recycle Bin on Windows if `send2trash` is not available or fails)

## Installation / Setup

1.  **Clone or download the project.**
2.  **Install Python 3.x** if you haven't already.
3.  **Install required Python packages**:
    ```bash
    pip install PySide6
    pip install send2trash  # Optional, but recommended
    ```
4.  **Place External Tools**:
    * Create a subdirectory named `ext` inside the `converter_tools` directory.
    * Download or copy the required executable files (`7za.exe`, `chdman.exe`, `DolphinTool.exe`, `maxcso.exe`, `recycle.exe`) into the `converter_tools/ext/` directory.
    * The paths to these tools are defined in `converter_tools/config.py` and can be adjusted if needed, but the default assumes they are in `converter_tools/ext/`.

## Building from Source

To create a standalone executable from the source code, you can use PyInstaller.

1.  **Install PyInstaller**:
    If you haven't already, install PyInstaller using pip. It's also recommended to install it within your project's virtual environment.
    ```bash
    pip install PyInstaller
    ```
    (Note: PyInstaller has been added to `requirements.txt` in this project, so you can also install it by running `pip install -r requirements.txt` in the project root.)

2.  **Run the Build Command**:
    Navigate to the root directory of the project in your terminal and run the following command:
    ```bash
    pyinstaller --onefile --windowed --name converter --icon src/converter_tools/assets/icons/app_icon.ico --add-data "src/converter_tools/assets:converter_tools/assets" --add-data "src/converter_tools/converter_settings.json:converter_tools" src/converter.py
    ```
    This command will:
    * Create a single executable file (`--onefile`).
    * Make it a windowed application, suppressing the console window (`--windowed`).
    * Name the executable `converter.exe` (or `converter` on non-Windows) (`--name converter`).
    * Set the application icon (`--icon src/converter_tools/assets/icons/app_icon.ico`).
    * Bundle necessary assets and the default settings file (`--add-data`).
    * Specify the main script (`src/converter.py`).

3.  **Locate the Executable**:
    After PyInstaller finishes, you will find the executable in a `dist` subdirectory within your project root (e.g., `dist/converter.exe`).

## Usage

The application can be launched from the project's root directory using `converter.py`.

### GUI Mode (Default)

To launch the Graphical User Interface:

```bash
python converter.py
```

#### Using the GUI

* **Select Job Type**: Choose the main operation you want to perform (e.g., "Compress media", "Extract media").
* **Select Media Type**: Based on the job type, select the specific kind of media you are working with (e.g., "CD image", "GameCube/Wii"). This will configure the tool for appropriate input and output formats.
* **Add Files/Folders**:
    * Use "Add Files..." to select individual files.
    * Use "Add Folder..." to add all convertible files from a folder. Check "Recursive" to include subfolders.
* **Filter Input (Optional)**: Click "Select input file types" to refine which of the added files are active for the current job based on their extension.
* **Configure Output**:
    * **Output Folder**:
        * Check "Output in same folder as input" to save converted files alongside their originals.
        * Uncheck it and use "Select Output Folder..." to specify a custom destination.
    * **Output Type**: If the selected job/media type supports multiple output formats (e.g., compressing GameCube/Wii to RVZ, GCZ, or WIA), click "Select output file type" to choose your desired format.
* **Options**:
    * "Overwrite existing files": If checked, existing files in the output location with the same name will be overwritten. Otherwise, new files will be renamed (e.g., `file_1.chd`).
    * "Delete input files after completing job": If checked, original source files will be sent to the Recycle Bin/Trash (or permanently deleted if recycle fails) only if their individual conversion was successful.
* **Start Job**: Click the main action button (e.g., "COMPRESS", "EXTRACT") to begin processing the selected files.
* **Monitor Progress**: View progress bars and detailed logs in the GUI. You can cancel the ongoing job.
* **Settings**: Access `File > Settings...` to configure application behavior, tool parameters, and temporary directory paths. Settings are saved in `converter_tools/converter_settings.json`.

### Command-Line Interface (CLI) Mode

To launch the Command-Line Interface:

```bash
python converter.py --cli
```

You can also provide an input path directly:

```bash
python converter.py --cli /path/to/your/file_or_folder
```

The CLI will guide you through a series of prompts to select the job, media type, input/output files, and processing options.

### Configuration

* **Application Settings**: Most application settings, including paths to external tools and default conversion parameters, are managed in `converter_tools/config.py` and can be overridden by user settings saved in `converter_tools/converter_settings.json` (via the GUI's Settings dialog).
* **Job Definitions**: The available jobs, media types, and their associated input/output formats and conversion functions are defined in `converter_tools/menu_definitions.py`.



### Contributing

Contributions, bug reports, and feature requests are welcome! Please feel free to open an issue or submit a pull request.
(Optional: Add guidelines for development, testing, and submitting changes if you plan for external contributions.)




## License

The Python code for this Retro Converter Tool is licensed under the GNU General Public License, version 2 or any later version (GPLv2+). A copy of the GPLv2 is included in the LICENSE file in the root directory of this project.

This tool utilizes the following external programs, which are licensed under their own terms:

* **CHDMAN**: Part of the MAME project, typically licensed under the GNU General Public License, version 2 or later (GPLv2+). For more details, please refer to the [MAME licensing information](https://www.mamedev.org/टेक्स्ट).
* **DolphinTool**: A command-line utility for the Dolphin Emulator, which is licensed under the GNU General Public License, version 2 or later (GPLv2+). For more details, please refer to the [Dolphin Emulator licensing information](https://dolphin-emu.org/docs/license/).
* **7-Zip (`7za.exe`)**: Licensed under the GNU LGPL license (with some parts under the BSD 3-clause License and unRAR restriction). More info: <https://www.7-zip.org/license.txt>e.
* **MAXCSO**:  Licensed under the ISC License (Copyright (c) 2014, Unknown W. Brackets). The license text is as follows:
    ```
    Permission to use, copy, modify, and/or distribute this software for any
    purpose with or without fee is hereby granted, provided that the above
    copyright notice and this permission notice appear in all copies.

    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
    ```

* **recycle.exe**: A freeware utility. I couldn't find what license it uses.

When distributing this Retro Converter Tool with these external programs, you must comply with their respective licenses.