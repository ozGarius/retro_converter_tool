import os
import sys
import argparse

# --- Path Setup & Module Import ---
# Get the directory of the current script (src/converter.py), which is .../src/
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent of the current script's directory (which is .../converter/ - the project root)
project_root_dir = os.path.dirname(current_script_dir)
# Insert the project root directory into sys.path
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

try:
    # Imports are now relative to the project root, so we prepend 'src.'
    from src.converter_tools import gui
    from src.converter_tools import config
    from src.converter_tools import utils
    from src.converter_tools import cli

except (ImportError, FileNotFoundError) as e:
    # converter_tools_path is no longer defined in this scope, adjust error message or remove
    print(f"\033[91mERROR: Failed setup or import of 'converter_tools' modules.\033[0m")
    print("Ensure 'config.py', 'utils.py', 'conversions.py', 'cli.py', 'gui.py',")
    print("'gui_main_window.py', 'gui_settings.py', 'gui_worker.py',")
    print("and '__init__.py' (empty file) are inside the 'converter_tools' folder,")
    print("and 'converter.py' is in the directory containing 'converter_tools'.")
    print(f"\nDetails: {e}")
    input("\nPress Enter to exit.")
    sys.exit(1)
except Exception as e:
    print("\033[91mERROR: An unexpected error occurred during setup.\033[0m")
    print(f"Details: {e}")
    input("\nPress Enter to exit.")
    sys.exit(1)

# --- Argument Parsing (Modified) ---
parser = argparse.ArgumentParser(description="Retro Converter Tool.")
parser.add_argument('--cli', action='store_true', help='Launch the Command-Line Interface instead of the GUI.')
parser.add_argument('input_path', nargs='?', default=None, help='Optional input file/folder path (used with --cli).')

# Parse arguments
args, unknown = parser.parse_known_args()

# --- Initial Checks (Remain the same) ---
print("Performing initial checks...")
checks_passed = True
if not utils.check_tools_exist(config.ESSENTIAL_TOOLS):
    checks_passed = False
if config.settings.COPY_LOCALLY and not os.path.exists(config.settings.MAIN_TEMP_DIR):
    try:
        os.makedirs(config.settings.MAIN_TEMP_DIR)
        print(f"\033[92mCreated main temp directory: \"{config.settings.MAIN_TEMP_DIR}\"\033[0m")
    except OSError as e:
        print(f"\033[91mERROR: Failed to create main temporary directory {config.settings.MAIN_TEMP_DIR}: {e}\033[0m")
        checks_passed = False

if not checks_passed:
    input("Initial checks failed. Press Enter to exit.")
    sys.exit(1)
print("Initial checks passed.")

# --- Launch Mode Decision (Modified) ---
if args.cli:
    print("Launching Command-Line Interface (CLI)...")
    cli.run_cli(input_path_from_args=args.input_path)
else:
    print("Launching GUI...")
    gui.run_gui()
