# converter.py (Main Script)
import os
import sys
import glob

# --- Adjust Python Path ---
try:
    # Get the directory where this script (converter.py) resides
    main_script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to the convert_tools directory
    convert_tools_path = os.path.join(main_script_dir, 'convert_tools')

    # Check if convert_tools directory exists
    if not os.path.isdir(convert_tools_path):
        print(f"\033[91mERROR: The directory '{convert_tools_path}' does not exist.\033[0m")
        raise FileNotFoundError("convert_tools directory not found")

    # Add the convert_tools directory *directly* to sys.path
    # Ensure it's checked first by inserting at index 0
    if convert_tools_path not in sys.path:
        sys.path.insert(0, convert_tools_path)

    # Import modular components directly now
    import config         # Settings and tool paths
    import utils          # Helper functions (run_command, cleanup, etc.)
    import conversions    # Specific conversion routines

except ImportError as e:
    # Construct the expected path again for the error message
    main_script_dir_error = os.path.dirname(os.path.abspath(__file__))
    convert_tools_path_error = os.path.join(main_script_dir_error, 'convert_tools')
    print(f"\033[91mERROR: Failed to import modules from '{convert_tools_path_error}'.\033[0m")
    print(f"Ensure 'config.py', 'utils.py', 'conversions.py', and '__init__.py' (empty file) are inside the 'convert_tools' folder,")
    print(f"and 'converter.py' is in the directory containing 'convert_tools'.")
    print(f"\nImportError Details: {e}")
    input("\nPress Enter to exit.")
    sys.exit(1)
except FileNotFoundError as e:
    # Error already printed above if directory doesn't exist
    input("\nPress Enter to exit.")
    sys.exit(1)
except Exception as e:
    print(f"\033[91mERROR: An unexpected error occurred during path setup or import.\033[0m")
    print(f"Details: {e}")
    input("\nPress Enter to exit.")
    sys.exit(1)


# --- MAIN MENU & EXECUTION ---

def print_menu():
    """Displays the structured main menu."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\033[96m================================================================================\033[0m")
    print(f"\033[96m>> Consolidated File Converter <<\033[0m")
    print(f"\033[96m>> Written by Oz <<\033[0m")
    print(f"\033[96m================================================================================\033[0m")
    print(f"\n\033[94m>> Select a conversion type: <<\033[0m\n")

    # --- UPDATED menu_data with 'conversions.' prefix ---
    # Menu data structure: [Category, [Option Number, Text, [Input Formats], Output Format, Output Format2, Function]]
    menu_data = [
        ["Nintendo GameCube / Nintendo Wii", [
            ['10', "ISO to RVZ", ['iso'], 'rvz', None, conversions.convert_iso_to_rvz_routine],
            ['11', "RVZ to ISO", ['rvz'], 'iso', None, conversions.convert_rvz_to_iso_routine],
            ['12', "7Z/ZIP/RAR to RVZ", ['7z', 'zip', 'rar'], 'rvz', None, conversions.convert_archive_to_rvz_routine],
        ]],
        ["Sony Playstation 1 / Sega Saturn / Sega CD", [
            ['20', "ISO/CUE/IMG to CHD", ['iso', 'cue', 'img'], 'chd', None, conversions.convert_discimage_to_chd_routine],
            ['21', "7Z/ZIP/RAR to CHD", ['7z', 'zip', 'rar'], 'chd', None, conversions.convert_archive_to_chd_routine],
            ['23', "CHD to CUE/BIN", ['chd'], 'cue', 'bin', conversions.convert_chd_to_cuebin_routine],
            ['24', "CHD to ISO", ['chd'], 'iso', None, conversions.convert_chd_to_iso_routine],
        ]],
        ["Sega Dreamcast", [
            ['30', "GDI/CUE to CHD", ['gdi', 'cue'], 'chd', None, conversions.convert_discimage_to_chd_routine],
            ['31', "7Z/ZIP/RAR to CHD", ['7z', 'zip', 'rar'], 'chd', None, conversions.convert_archive_to_chd_routine],
            ['32', "CHD to GDI", ['chd'], 'gdi', None, conversions.convert_chd_to_gdi_routine],
        ]],
        ["Sony Playstation 2", [
            ['40', "ISO to CHD", ['iso'], 'chd', None, conversions.convert_discimage_to_chd_routine],
            ['41', "7Z/ZIP/RAR to CHD", ['7z', 'zip', 'rar'], 'chd', None, conversions.convert_archive_to_chd_routine],
            ['42', "CSO to CHD", ['cso'], 'chd', None, conversions.convert_cso_to_chd_routine],
        ]],
        ["Playstation Portable", [
            ['50', "ISO to CSO", ['iso'], 'cso', None, conversions.convert_iso_to_cso_routine],
            ['51', "7Z/ZIP/RAR to CSO", ['7z', 'zip', 'rar'], 'cso', None, conversions.convert_archive_to_cso_routine],
        ]],
        ["Archiving", [
            ['90', "ZIP/RAR to 7Z", ['zip', 'rar'], '7z', None, conversions.convert_archive_to_7z_routine],
        ]],
        ["Audio", [
            # These still point to None because they are handled specially in the main loop
            ['80', "Audio to Audio (Specify Formats)", [], None, None, None],
            ['81', "Folder to FLAC", [], 'flac', None, None],
        ]],
    ]
    # --- END UPDATED menu_data ---

    formatted_menu = ""
    all_options = {}
    for category, options in menu_data:
        formatted_menu += f"\n\033[93m{category.upper()}:\033[0m\n"
        for option_details in options:
            num, text, fmts_in, fmt_out, fmt_out2, func = option_details
            all_options[num] = option_details[1:] # Store details without number
            option_str = f" \033[92m{num:>3}.\033[0m {text}"
            if func is None and num not in ['80', '81']:
                option_str += " \033[91m(Not Implemented)\033[0m"
            formatted_menu += f"{option_str}\n"

    print(formatted_menu)
    print("-" * 60)
    print(" \033[91m  0.\033[0m Exit")
    print("-" * 60)
    return all_options

def print_main_help(formats_in, format_out, format_out2=None):
    """Prints help message within the main script context."""
    utils.print_help(formats_in, format_out, format_out2) # Call the utils version

def main():
    """Main function to run the converter script."""
    # Initial checks
    if not utils.check_tools_exist(config.ESSENTIAL_TOOLS):
        input("Press Enter to exit.")
        sys.exit(1)
    if config.COPY_LOCALLY and not os.path.exists(config.MAIN_TEMP_DIR):
        try:
            os.makedirs(config.MAIN_TEMP_DIR)
            print(f"\033[92mCreated main temp directory: \"{config.MAIN_TEMP_DIR}\"\033[0m")
        except OSError as e:
            print(f"\033[91mERROR: Failed to create main temporary directory {config.MAIN_TEMP_DIR}: {e}\033[0m")
            input("Press Enter to exit.")
            sys.exit(1)

    while True:
        conversion_options = print_menu()
        choice = input("Enter your choice: ").strip()

        if choice == '0':
            break
        elif choice == '80':
            # Handle Audio to Audio
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\033[96m>> Audio to Audio Converter <<\033[0m\n")
            input_format = input("Enter INPUT audio format (e.g., mp3): ").strip().lower().lstrip('.')
            output_format = input("Enter OUTPUT audio format (e.g., flac): ").strip().lower().lstrip('.')
            if not input_format or not output_format:
                print("\033[91mERROR: Input and output formats must be specified.\033[0m")
                input("\nPress Enter to return...")
                continue
            input_path = input(f"Enter path to folder containing *.{input_format} files: ").strip().strip('"')
            if not os.path.isdir(input_path):
                 print(f"\033[91mERROR: Invalid folder path: \"{input_path}\".\033[0m")
                 input("\nPress Enter to return...")
                 continue
            # Call the audio routine from the conversions module
            conversions.convert_folder_audio_routine(input_path, output_format, input_format)
            input("\nPress Enter to return...")
            continue

        elif choice == '81':
            # Handle Folder to FLAC
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\033[96m>> Folder to FLAC Converter <<\033[0m\n")
            input_path = input("Enter path to folder: ").strip().strip('"')
            if not os.path.isdir(input_path):
                 print(f"\033[91mERROR: Invalid path: \"{input_path}\". Please provide a folder path.\033[0m")
                 input("\nPress Enter to return...")
                 continue
            # Call the audio routine from the conversions module
            conversions.convert_folder_audio_routine(input_path, 'flac')
            input("\nPress Enter to return...")
            continue

        elif choice in conversion_options:
            # Handle standard conversions
            option_text, formats_in, format_out, format_out2, conversion_func = conversion_options[choice]
            if conversion_func is None:
                print(f"\033[91mERROR: Conversion '{option_text}' (Choice {choice}) is not implemented yet.\033[0m")
                input("\nPress Enter to return...")
                continue

            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\033[96m>> {option_text} <<\033[0m\n")
            print(f"\033[93m Settings: CopyLocally={config.COPY_LOCALLY}, DeleteSource={config.DELETE_SOURCE_ON_SUCCESS}\033[0m")
            # Add other relevant settings display if needed

            input_formats_str = ", ".join([f"*.{f}" for f in formats_in])
            input_path = input(f"Enter path to file(s)/folder ({input_formats_str}): ").strip().strip('"')

            if not os.path.exists(input_path):
                 print(f"\033[91mERROR: Invalid path: \"{input_path}\".\033[0m")
                 print_main_help(formats_in, format_out, format_out2)
                 input("\nPress Enter to return...")
                 continue

            # Use the process_input function from utils module, passing the conversion function
            # (which is now referenced via the conversions module, e.g., conversions.convert_iso_to_rvz_routine)
            utils.process_input(input_path, conversion_func, formats_in, format_out, format_out2)
            input("\nPress Enter to return...")

        else:
            print("\033[91mInvalid choice. Please try again.\033[0m")
            input("Press Enter to continue.")

    print("\n\033[96m>> Exiting converter. <<\033[0m")

if __name__ == "__main__":
    # Argument handling (optional, could be enhanced)
    if len(sys.argv) > 1:
        print(f"\033[93mCommand-line arguments detected: {' '.join(sys.argv[1:])}\033[0m")
        print(f"\033[93mNote: Arguments are ignored. Please use the interactive menu.\033[0m")
        input("Press Enter to continue to the menu...")

    main()
