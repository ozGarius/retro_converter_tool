# converter.py (Launcher Script)
import os
import sys
import argparse  # Use argparse for better argument handling

# --- Path Setup & Module Import ---
try:
    # Get the directory where this script (converter.py) resides
    main_script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to the convert_tools directory
    convert_tools_path = os.path.join(main_script_dir, 'convert_tools')

    # Check if convert_tools directory exists
    if not os.path.isdir(convert_tools_path):
        print(f"\033[91mERROR: The directory '{convert_tools_path}' does not exist.\033[0m")
        print("Ensure 'converter.py' is in the same directory as the 'convert_tools' folder.")
        raise FileNotFoundError("convert_tools directory not found")

    # Add the convert_tools directory *directly* to sys.path
    if convert_tools_path not in sys.path:
        sys.path.insert(0, convert_tools_path)

    # Import modular components
    from convert_tools import gui, config, utils, cli

except (ImportError, FileNotFoundError) as e:
    # Construct the expected path again for the error message
    main_script_dir_error = os.path.dirname(os.path.abspath(__file__))
    convert_tools_path_error = os.path.join(main_script_dir_error, 'convert_tools')
    print(f"\033[91mERROR: Failed setup or import from '{convert_tools_path_error}'.\033[0m")
    print("Ensure 'config.py', 'utils.py', 'conversions.py', 'cli.py', 'gui.py' (eventually),")
    print("and '__init__.py' (empty file) are inside the 'convert_tools' folder,")
    print("and 'converter.py' is in the directory containing 'convert_tools'.")
    print(f"\nDetails: {e}")
    input("\nPress Enter to exit.")
    sys.exit(1)
except Exception as e:
    print("\033[91mERROR: An unexpected error occurred during setup.\033[0m")
    print(f"Details: {e}")
    input("\nPress Enter to exit.")
    sys.exit(1)

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="Consolidated File Converter Tool.")
parser.add_argument('--gui', action='store_true', help='Launch the Graphical User Interface.')
parser.add_argument('input_path', nargs='?', default=None, help='Optional input file/folder path for CLI mode.')
# Add other potential CLI arguments here if needed in the future

# Parse arguments, but ignore unknown ones if running from an IDE or double-clicked
# This prevents errors if Windows passes unexpected arguments on double-click
args, unknown = parser.parse_known_args()

# --- Initial Checks ---
# Perform these once before launching either interface
print("Performing initial checks...")
checks_passed = True
if not utils.check_tools_exist(config.ESSENTIAL_TOOLS):
    checks_passed = False
if config.COPY_LOCALLY and not os.path.exists(config.MAIN_TEMP_DIR):
    try:
        os.makedirs(config.MAIN_TEMP_DIR)
        print(f"\033[92mCreated main temp directory: \"{config.MAIN_TEMP_DIR}\"\033[0m")
    except OSError as e:
        print(f"\033[91mERROR: Failed to create main temporary directory {config.MAIN_TEMP_DIR}: {e}\033[0m")
        checks_passed = False

if not checks_passed:
    input("Initial checks failed. Press Enter to exit.")
    sys.exit(1)
print("Initial checks passed.")

# --- Launch Mode Decision ---
if args.gui:
    print("Launching GUI...")
    try:
        # --- Placeholder for GUI launch ---
        # import gui  # Import gui module here
        gui.run_gui()
        # --- End Placeholder ---
    except ImportError:
        print("\033[91mERROR: Failed to import the 'gui' module.\033[0m")
        print("Ensure 'gui.py' exists in the 'convert_tools' directory.")
        input("Press Enter to exit.")
        sys.exit(1)
    except Exception as e:
        print("\033[91mERROR: Failed to launch GUI.\033[0m")
        print(f"Details: {e}")
        input("Press Enter to exit.")
        sys.exit(1)
else:
    print("Launching Command-Line Interface (CLI)...")
    # Pass the input path argument (if provided) to the CLI runner
    cli.run_cli(input_path_from_args=args.input_path)
