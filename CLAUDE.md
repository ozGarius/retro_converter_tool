# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Retro Converter Tool is a Python-based media conversion application that handles disc images (CD, DVD, GameCube/Wii), hard disk images, and archives. It provides both a GUI (PySide6) and CLI interface for converting between various formats using external tools like CHDMAN, DolphinTool, and 7-Zip.

## Development Setup

1. **Environment setup**:
   ```bash
   pip install -r requirements.txt
   ```
   This installs PySide6, Send2Trash, and PyInstaller.

2. **External tools**: Place required executables in `converter_tools/ext/`:
   - `7za.exe` (7-Zip command-line)
   - `chdman.exe` (MAME tools)
   - `DolphinTool.exe`
   - `maxcso.exe`
   - `recycle.exe` (optional)

## Running the Application

- **GUI mode**: `python src/converter.py`
- **CLI mode**: `python src/converter.py --cli`
- **CLI with input**: `python src/converter.py --cli /path/to/file`

## Building

Create standalone executable with PyInstaller:
```bash
pyinstaller --onefile --windowed --name converter --icon src/converter_tools/assets/icons/app_icon.ico --add-data "src/converter_tools/assets:converter_tools/assets" --add-data "src/converter_tools/converter_settings.json:converter_tools" src/converter.py
```

## Architecture

The codebase is structured around a job-based conversion system:

- **`src/converter.py`**: Main entry point with argument parsing
- **`src/converter_tools/`**: Core application modules
  - `config.py`: Configuration management and default settings
  - `menu_definitions.py`: Job types, media types, and conversion function mappings
  - `conversions.py`: Actual conversion implementations using external tools
  - `gui.py`, `gui_main_window.py`, `gui_settings.py`: PySide6 GUI components
  - `cli.py`: Command-line interface implementation
  - `worker_process.py`: Multiprocessing for conversion jobs
  - `utils.py`: Utility functions for file operations
  - `shared_logic.py`: Common logic between GUI and CLI

## Key Concepts

1. **Job-based workflow**: Operations are defined as jobs (compress, extract, etc.) with specific media types
2. **External tool integration**: The app wraps command-line tools rather than implementing conversions natively
3. **Multiprocessing**: Conversions run in separate processes to avoid blocking the UI
4. **Settings persistence**: User settings stored in `converter_tools/converter_settings.json`
5. **Archive support**: Automatic extraction of compressed input files before processing

## Configuration

- Application settings are managed in `config.py` with user overrides in `converter_settings.json`
- Job definitions and supported formats are configured in `menu_definitions.py`
- External tool paths are configurable but default to `converter_tools/ext/`

## Import Structure

The project uses absolute imports from the project root (e.g., `from src.converter_tools import config`). The main script adds the project root to `sys.path` to enable this pattern.