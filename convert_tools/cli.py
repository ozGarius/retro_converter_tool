# convert_tools/cli.py
"""
Contains the command-line interface logic for the converter tool.
Uses updated menu definitions.
"""

import os
import sys
import glob

# Import modular components from the same directory
try:
    import config         # Settings and tool paths
    import utils          # Helper functions (run_command, cleanup, etc.)
    import conversions    # Specific conversion routines
    import menu_definitions # Centralized menu data
except ImportError as e:
    print(f"\033[91mERROR: cli.py failed to import sibling modules.\033[0m")
    print(f"Ensure all module files are present in the 'convert_tools' directory.")
    print(f"Details: {e}")
    sys.exit(1)


# --- CLI Menu & Interaction ---

def print_menu():
    """Displays the structured command-line menu using definitions."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\033[96m================================================================================\033[0m")
    print(f"\033[96m>> Consolidated File Converter (Command Line Interface) <<\033[0m")
    print(f"\033[96m>> Written by Oz <<\033[0m")
    print(f"\033[96m================================================================================\033[0m")
    print(f"\n\033[94m>> Select a conversion type: <<\033[0m\n")

    # Get menu data and CLI map from the central definition
    menu_data, cli_options_map = menu_definitions.get_cli_menu_data()

    formatted_menu = ""
    for category, options in menu_data:
        formatted_menu += f"\n\033[93m{category.upper()}:\033[0m\n"
        for option_details in options:
            # Unpack details for display (index 0 is num, 1 is cli_text, 6 is func)
            num, cli_text, _, _, _, _, func = option_details
            option_str = f" \033[92m{num:>3}.\033[0m {cli_text}" # Use cli_text
            # Check if function is None for non-special cases
            if func is None and num not in ['80', '81']:
                option_str += " \033[91m(Not Implemented)\033[0m"
            formatted_menu += f"{option_str}\n"

    print(formatted_menu)
    print("-" * 60)
    print(" \033[91m  0.\033[0m Exit")
    print("-" * 60)
    # Return the map needed for the CLI loop
    return cli_options_map

def print_cli_help(formats_in, format_out, format_out2=None):
    """Prints help message within the CLI context."""
    input_formats_str = ", ".join([f"*.{f}" for f in formats_in]) if formats_in else "N/A"
    output_formats_str = f"*.{format_out}" if format_out else "N/A"
    if format_out2:
        output_formats_str += f" / *.{format_out2}"

    print(f"\n\033[94m-------------------- HELP --------------------\033[0m")
    print(f"\033[96m Usage: Enter the full path to the file or folder you want to convert.\033[0m")
    print(f"\033[96m Input : {input_formats_str}\033[0m")
    print(f"\033[96m Output: {output_formats_str}\033[0m")
    print(f"\033[94m----------------------------------------------\033[0m")


def run_cli(input_path_from_args=None):
    """Runs the main command-line interface loop."""
    while True:
        # Get options map by calling print_menu which now reads from definitions
        conversion_options = print_menu() # This map now uses 'text' for cli_text
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
            conversions.convert_folder_audio_routine(input_path, 'flac')
            input("\nPress Enter to return...")
            continue

        elif choice in conversion_options:
            # Handle standard conversions using the map returned by print_menu
            details = conversion_options[choice]
            option_text = details['text'] # Use 'text' which maps to cli_text
            formats_in = details['formats_in']
            format_out = details['format_out']
            format_out2 = details['format_out2']
            conversion_func = details['func']

            if conversion_func is None:
                print(f"\033[91mERROR: Conversion '{option_text}' (Choice {choice}) is not implemented yet.\033[0m")
                input("\nPress Enter to return...")
                continue

            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\033[96m>> {option_text} <<\033[0m\n")
            print(f"\033[93m Settings: CopyLocally={config.COPY_LOCALLY}, DeleteSource={config.DELETE_SOURCE_ON_SUCCESS}\033[0m")

            input_formats_str = ", ".join([f"*.{f}" for f in formats_in]) if formats_in else "N/A"

            current_input_path = None
            if input_path_from_args:
                print(f"Using input path from argument: {input_path_from_args}")
                current_input_path = input_path_from_args
                input_path_from_args = None
            else:
                current_input_path = input(f"Enter path to file(s)/folder ({input_formats_str}): ").strip().strip('"')


            if not os.path.exists(current_input_path):
                 print(f"\033[91mERROR: Invalid path: \"{current_input_path}\".\033[0m")
                 print_cli_help(formats_in, format_out, format_out2)
                 input("\nPress Enter to return...")
                 continue

            utils.process_input(current_input_path, conversion_func, formats_in, format_out, format_out2)
            input("\nPress Enter to return...")

        else:
            print("\033[91mInvalid choice. Please try again.\033[0m")
            input("Press Enter to continue.")

    print("\n\033[96m>> Exiting converter CLI. <<\033[0m")

