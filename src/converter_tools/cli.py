# converter_tools/cli.py
"""
Contains the command-line interface logic for the converter tool,
restructured to follow a job-based flow similar to the GUI.
"""

import os
import sys

try:
    from . import config # Adjusted for potential package structure
    from .config import save_app_settings # Specific import
    from . import utils
    from . import conversions
    from . import menu_definitions
except ImportError: # Fallback for direct script run or different structure
    import config
    from config import save_app_settings
    import utils
    import conversions
    import menu_definitions
except Exception as e: # Catch any other import error during the initial setup
    # Attempt to use utils._emit_or_print if utils was imported, otherwise plain print
    if 'utils' in locals() and hasattr(utils, '_emit_or_print'):
        utils._emit_or_print(f"ERROR: cli.py failed to import modules: {e}", is_error=True)
    else:
        print(f"ERROR: cli.py failed to import modules: {e}")
    sys.exit(1)


def get_user_choice(prompt, options, allow_exit=True, show_numbers=True):
    """Generic helper to get a numbered choice from the user."""
    while True:
        print(prompt)
        for i, option_text in enumerate(options):
            if show_numbers:
                print(f"  {i + 1}. {option_text}")
            else:
                print(f"  - {option_text}")
        if allow_exit:
            print("  0. Back / Exit to Main Menu")

        choice_str = input("Enter your choice: ").strip()
        if not choice_str.isdigit():
            utils._emit_or_print("Invalid input. Please enter a number.", is_error=True)
            continue

        choice = int(choice_str)
        if allow_exit and choice == 0:
            return None  # Indicates back/exit

        # Adjust for 1-based indexing if numbers are shown
        actual_choice_index = choice - 1 if show_numbers else choice

        if 0 <= actual_choice_index < len(options):
            return options[actual_choice_index]  # Return the chosen option string or object
        else:
            utils._emit_or_print("Invalid choice number. Please try again.", is_error=True)


def get_yes_no_input(prompt, default_yes=True):
    """Gets a yes/no input from the user."""
    default_indicator = "(Y/n)" if default_yes else "(y/N)"
    while True:
        choice = input(f"{prompt} {default_indicator}: ").strip().lower()
        if not choice:  # User pressed Enter
            return default_yes
        if choice in ['y', 'yes']:
            return True
        if choice in ['n', 'no']:
            return False
        utils._emit_or_print("Invalid input. Please enter 'y' or 'n'.", is_error=True)


def run_cli(input_path_from_args=None):
    """Runs the main command-line interface loop with a job-based flow."""

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        utils._emit_or_print("=================================================", fallback_color_code="\033[96m")
        utils._emit_or_print(">> Converter Tool - Command Line Interface     <<", fallback_color_code="\033[96m")
        utils._emit_or_print("=================================================", fallback_color_code="\033[96m")

        # 1. Choose Job Type
        job_names = [job["job_name"] for job in menu_definitions.JOB_DEFINITIONS]
        if not job_names:
            utils._emit_or_print("ERROR: No jobs defined in menu_definitions.py. Exiting.", is_error=True)
            return

        selected_job_name = get_user_choice("\nSelect a Job Type:", job_names)
        if selected_job_name is None:
            break  # Exit CLI

        selected_job_details = next((job for job in menu_definitions.JOB_DEFINITIONS if job["job_name"] == selected_job_name), None)
        if not selected_job_details:  # Should not happen if get_user_choice works
            utils._emit_or_print("Internal error: Selected job not found.", is_error=True)
            continue

        # 2. Choose Media Type
        media_type_names = [media["media_name"] for media in selected_job_details.get("media_types", [])]
        if not media_type_names:
            utils._emit_or_print(f"No media types defined for job '{selected_job_name}'. Please check menu_definitions.py.", is_error=True)
            input("Press Enter to continue...")
            continue

        selected_media_name = get_user_choice(f"\nSelect Media Type for '{selected_job_name}':", media_type_names)
        if selected_media_name is None:
            continue  # Back to job selection

        selected_media_type_details = next((media for media in selected_job_details.get("media_types", []) if media["media_name"] == selected_media_name), None)
        if not selected_media_type_details:
            utils._emit_or_print("Internal error: Selected media type not found.", is_error=True)
            continue

        utils._emit_or_print(f"\n--- Job: {selected_job_name} | Media: {selected_media_name} ---", fallback_color_code="\033[93m")

        # 3. Get Input Path
        input_ext_display = ", ".join([f".{ext}" for ext in selected_media_type_details.get("input_ext", ["*"])])
        current_input_path_cli = None # Initialize
        while True:
            suggestion_path_cli = ""
            if config.settings.LAST_USED_DIRECTORY and os.path.isdir(config.settings.LAST_USED_DIRECTORY):
                suggestion_path_cli = config.settings.LAST_USED_DIRECTORY

            prompt_text_cli = f"Enter path to input file/folder (expects {input_ext_display})"
            if suggestion_path_cli:
                prompt_text_cli += f" [press Enter for: {suggestion_path_cli}]"

            input_path_str = input(f"{prompt_text_cli}: ").strip().strip('"')

            if not input_path_str and suggestion_path_cli: # User pressed Enter and suggestion exists
                current_input_path_cli = suggestion_path_cli
                utils._emit_or_print(f"Using suggested path: {current_input_path_cli}", fallback_color_code="cyan")
            else:
                current_input_path_cli = input_path_str

            if not current_input_path_cli:
                utils._emit_or_print("Input path cannot be empty.", is_error=True)
                continue
            if not os.path.exists(current_input_path_cli):
                utils._emit_or_print(f"ERROR: Path not found: \"{current_input_path_cli}\"", is_error=True)
                retry_path = get_yes_no_input("Try again?", default_yes=True)
                if not retry_path:
                    current_input_path_cli = None  # Signal to go back
                    break
                else:
                    continue  # Retry input path

            # Save the directory of the valid input path
            path_to_save_for_cli = current_input_path_cli
            if os.path.isfile(current_input_path_cli):
                path_to_save_for_cli = os.path.dirname(current_input_path_cli)

            if os.path.isdir(path_to_save_for_cli):
                config.settings.LAST_USED_DIRECTORY = os.path.normpath(path_to_save_for_cli)
                save_app_settings()

            # Basic type check (can be more robust)
            if os.path.isfile(current_input_path_cli):
                file_ext = os.path.splitext(current_input_path_cli)[1].lower().lstrip('.')
                # Ensure selected_media_type_details.get("input_ext", []) is not empty before 'in' check
                valid_input_exts_for_media = selected_media_type_details.get("input_ext", [])
                if valid_input_exts_for_media and file_ext not in valid_input_exts_for_media:
                    utils._emit_or_print(f"Warning: File extension '.{file_ext}' does not match expected types ({input_ext_display}).", fallback_color_code="\033[93m")
                    confirm_proceed = get_yes_no_input("Proceed anyway?", default_yes=False)
                    if not confirm_proceed:
                        continue  # Retry input path
            break  # Path is valid or user chose to proceed

        if current_input_path_cli is None:
            continue  # Back to media type selection

        # 4. Choose Output File Type (if applicable)
        target_format_out = None
        possible_output_exts = selected_media_type_details.get("output_ext", [])
        if isinstance(possible_output_exts, list) and len(possible_output_exts) > 1:
            chosen_output_ext = get_user_choice("\nSelect Output File Type:", possible_output_exts)
            if chosen_output_ext is None:
                continue  # Back
            target_format_out = chosen_output_ext
        elif isinstance(possible_output_exts, list) and len(possible_output_exts) == 1:
            target_format_out = possible_output_exts[0]
        elif isinstance(possible_output_exts, str):
            target_format_out = possible_output_exts
        # If output_ext is empty or None (e.g. for extract archive to folder), target_format_out remains None

        # Determine secondary output format based on primary selection
        target_format_out2 = None
        if target_format_out:
            possible_secondary_outputs = selected_media_type_details.get("output_ext_secondary")
            if isinstance(possible_primary_outputs := selected_media_type_details.get("output_ext"), list) and target_format_out in possible_primary_outputs:
                idx = possible_primary_outputs.index(target_format_out)
                if isinstance(possible_secondary_outputs, list) and idx < len(possible_secondary_outputs):
                    target_format_out2 = possible_secondary_outputs[idx]
                elif isinstance(possible_secondary_outputs, str) and idx == 0:  # If secondary is string, applies to first primary
                    target_format_out2 = possible_secondary_outputs

        utils._emit_or_print(f"Selected output format: .{target_format_out if target_format_out else 'Folder'}" + (f" (+ .{target_format_out2})" if target_format_out2 else ""), fallback_color_code="\033[92m")

        # 5. Processing Options
        utils._emit_or_print("\n--- Processing Options ---", fallback_color_code="\033[93m")
        # Changed default_yes for allow_overwrite_cli as OVERWRITE_EXISTING is not a defined setting.
        allow_overwrite_cli = get_yes_no_input("Overwrite existing output files?", default_yes=False)
        delete_input_cli = get_yes_no_input("Delete input files after successful job?", default_yes=config.settings.DELETE_SOURCE_ON_SUCCESS)
        copy_locally_cli = get_yes_no_input("Copy files locally for processing (recommended for network drives)?", default_yes=config.settings.COPY_LOCALLY)

        # Temporarily set config for this run (careful if other parts of app use config concurrently)
        # A better way might be to pass these as direct arguments to process_file if it supported them all.
        original_config_delete = config.settings.DELETE_SOURCE_ON_SUCCESS
        original_config_copy = config.settings.COPY_LOCALLY
        config.settings.DELETE_SOURCE_ON_SUCCESS = delete_input_cli
        config.settings.COPY_LOCALLY = copy_locally_cli

        # 6. Choose Output Folder
        explicit_output_dir = None
        requires_output_folder = selected_media_type_details.get("requires_output_folder", False)

        if requires_output_folder:
            output_in_same_folder = get_yes_no_input("\nOutput to same folder as input?", default_yes=True)
            if not output_in_same_folder:
                while True:
                    output_suggestion_cli = ""
                    if config.settings.LAST_USED_DIRECTORY and os.path.isdir(config.settings.LAST_USED_DIRECTORY):
                        output_suggestion_cli = config.settings.LAST_USED_DIRECTORY

                    output_prompt_cli = "Enter custom output folder path"
                    if output_suggestion_cli:
                        output_prompt_cli += f" [press Enter for: {output_suggestion_cli}]"

                    output_folder_path_str = input(f"{output_prompt_cli}: ").strip().strip('"')

                    if not output_folder_path_str and output_suggestion_cli: # User pressed Enter
                        output_folder_path_str = output_suggestion_cli
                        utils._emit_or_print(f"Using suggested output path: {output_folder_path_str}", fallback_color_code="cyan")

                    if not output_folder_path_str:
                        utils._emit_or_print("Output folder path cannot be empty.", is_error=True)
                        continue

                    # Basic check, can be made more robust
                    # Check if parent of the potential new dir exists, or if the path itself is an existing dir
                    potential_parent = os.path.dirname(os.path.abspath(output_folder_path_str))
                    if not os.path.isdir(output_folder_path_str) and not os.path.isdir(potential_parent):
                        utils._emit_or_print(f"Parent directory for '{output_folder_path_str}' does not seem valid, or path is not an existing directory.", is_error=True)
                        if not get_yes_no_input("Continue with this path anway (it might be created)?", default_yes=False):
                            continue

                    explicit_output_dir = os.path.normpath(output_folder_path_str)

                    # Save last used directory if a valid custom output folder is provided
                    if explicit_output_dir and os.path.isdir(explicit_output_dir): # Check if it's a dir or becomes one
                         config.settings.LAST_USED_DIRECTORY = explicit_output_dir
                         save_app_settings()
                    elif explicit_output_dir: # If it's not a dir yet, but path is accepted, save its parent
                        parent_of_explicit_output_dir = os.path.dirname(explicit_output_dir)
                        if os.path.isdir(parent_of_explicit_output_dir):
                           config.settings.LAST_USED_DIRECTORY = parent_of_explicit_output_dir
                           save_app_settings()

                    break

        # 7. Execute Conversion
        conversion_func_name = selected_media_type_details.get("conversion_func_name")
        conversion_func = getattr(conversions, conversion_func_name, None)

        if not callable(conversion_func):
            utils._emit_or_print(f"ERROR: Conversion function '{conversion_func_name}' not found or not callable.", is_error=True)
        else:
            utils._emit_or_print(f"\nStarting job: {selected_job_name} - {selected_media_name} for '{os.path.basename(current_input_path_cli)}'...", fallback_color_code="\033[96m")
            # Call utils.process_file directly
            # Note: utils.process_file uses config.DELETE_SOURCE_ON_SUCCESS and config.COPY_LOCALLY internally.
            # We pass allow_overwrite directly.
            # target_format_from_worker is the chosen primary output extension.
            utils.process_file(
                current_input_path_cli, # Use the potentially updated input_path
                conversion_func,
                target_format_out,  # This is the primary output format for moving
                target_format_out2,  # This is the secondary output format for moving
                explicit_output_dir=explicit_output_dir,
                allow_overwrite=allow_overwrite_cli,
                target_format_from_worker=target_format_out  # This is passed to conversion_func if it needs it
            )

        # Restore original config values
        config.DELETE_SOURCE_ON_SUCCESS = original_config_delete
        config.COPY_LOCALLY = original_config_copy

        input("\nPress Enter to return to the main menu...")

    utils._emit_or_print("\nExiting converter CLI.", fallback_color_code="\033[96m")


if __name__ == '__main__':
    # This allows running cli.py directly for testing
    # Ensure paths are set up if run this way
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Assuming converter_tools is in project_root
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if script_dir not in sys.path:  # Ensure converter_tools itself is also in path for its imports
        sys.path.insert(0, script_dir)

    # Re-import with adjusted path if necessary for direct run
    # try:
    #     import config
    #     import utils
    #     import conversions
    #     import menu_definitions
    # except ImportError:
    #     print("Error: Could not re-import necessary modules for direct CLI run. Ensure paths are correct.")
    #     sys.exit(1)

    run_cli()
