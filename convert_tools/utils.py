# -*- coding: utf-8 -*-
# /convert_tools/utils.py (Error Handling Enhancements)

import os
import subprocess
import shutil
import glob
import time
import tempfile
import config
import re

try:  # Attempt to import send2trash, but don't make it a hard requirement
    import send2trash
except ImportError:
    send2trash = None  # If not found, we'll fall back

ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _emit_or_print(message, signal=None, fallback_color_code=None, is_error=False):
    """
    Emits a message via a Qt signal if provided, otherwise prints to console.
    Optionally formats the fallback print message with a color code.
    If is_error is True, uses a default error color if no color_code is given.
    """
    color_map = {
        "red": "\033[91m",
        "green": "\033[92m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "black": "\033[30m",  # Standard black (often appears dark gray)

        "bright_red": "\033[1;91m",
        "bright_green": "\033[1;92m",
        "bright_blue": "\033[1;94m",
        "bright_yellow": "\033[1;93m",
        "bright_magenta": "\033[1;95m",
        "bright_cyan": "\033[1;96m",
        "bright_white": "\033[1;97m",

        "bold_red": "\033[1;31m",  # Bold red (standard intensity)
        "italic_green": "\033[3;92m",  # Italic green
        "underline_blue": "\033[4;94m",  # Underline blue
    }

    if signal:
        signal.emit(message)
    else:
        color_code = None
        if fallback_color_code:
            try:
                color_code = color_map.get(fallback_color_code.lower())
                if color_code is None:
                    color_code = fallback_color_code
            except AttributeError:
                print("Invalid color input. Printing without color.")
                color_code = None
        if color_code:
            print(f"{color_code}{message}\033[0m")
        elif is_error:
            print(f"\033[91m{message}\033[0m")
        else:
            # Default to green for non-error, non-specified color console output
            print(f"\033[92m{message}\033[0m")


def strip_ansi_codes(text):
    if not text:
        return ""
    try:
        return ANSI_ESCAPE_RE.sub('', text)
    except Exception:
        return text


def check_tools_exist(tools_list):
    missing_tools = [tool for tool in tools_list if not os.path.exists(tool)]
    if missing_tools:
        print("\033[91mERROR: Missing required tools:\033[0m")
        for tool in missing_tools:
            print(f"- {tool}")
        print("\033[91mEnsure 'convert_tools' folder is in the same directory and contains all executables.\033[0m")
        print(f"\033[91mExpected tools directory: {config.TOOLS_DIR}\033[0m")
        return False
    return True


def get_free_disk_space_gb(path):
    """
    Returns the free disk space in GB for the drive that path is on.
    Returns None if it can't determine the free space.
    """
    try:
        # For Python 3.3+
        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024**3)
        return free_gb
    except AttributeError:  # shutil.disk_usage not available (older Python) or other OS error
        _emit_or_print("shutil.disk_usage not available to check disk space.", is_error=True)  # Log to console
        return None  # Or implement a platform-specific fallback if needed
    except Exception as e:
        _emit_or_print(f"Error checking disk space for {path}: {e}", is_error=True)
        return None


def run_command(command, cwd=None, output_signal=None, error_signal=None, known_error_codes=None):  # Added known_error_codes
    """
    Runs an external command, captures its output, emits output/errors via signals,
    and returns True on success, False on failure.
    known_error_codes: A dictionary mapping exit codes to specific error messages.
    """
    command_str = ' '.join(command)
    _emit_or_print(f">> Running: {command_str}", output_signal, fallback_color_code="\033[92m")

    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace'
        )
        stdout_clean = strip_ansi_codes(result.stdout.strip())
        if stdout_clean:
            log_msg = f"--- STDOUT ---\n{stdout_clean}\n--------------"
            _emit_or_print(log_msg, output_signal)

        stderr_clean = strip_ansi_codes(result.stderr.strip())
        if stderr_clean:
            log_msg = f"--- STDERR ---\n{stderr_clean}\n--------------"
            _emit_or_print(log_msg, error_signal, is_error=True)

        if result.returncode != 0:
            err_msg = f"ERROR: Command failed (code {result.returncode})"
            if known_error_codes and result.returncode in known_error_codes:
                err_msg += f": {known_error_codes[result.returncode]}"
            else:
                # Append stderr to the generic error message if not already part of a known code's message
                # and if stderr provides more context than just the return code.
                if stderr_clean and stderr_clean not in err_msg:  # Avoid duplicating stderr if it was already in a known_error_codes message
                    err_msg += f"\nTool Output (stderr):\n{stderr_clean}"

            _emit_or_print(err_msg, error_signal, is_error=True)
            return False
        return True
    except FileNotFoundError:
        err_msg = f"ERROR: Command not found: {command[0]}"
        _emit_or_print(err_msg, error_signal, is_error=True)
        return False
    except Exception as e:
        err_msg = f"ERROR: Unexpected error running command: {e}"
        _emit_or_print(err_msg, error_signal, is_error=True)
        return False


def create_temp_dir(base_name, output_signal=None, error_signal=None):
    original_dir_of_input_file = os.path.dirname(base_name)
    file_name_part = os.path.splitext(os.path.basename(base_name))[0]
    temp_dir_prefix = f"{file_name_part}_"
    temp_dir_suffix = "_temp"

    if not config.COPY_LOCALLY:
        temp_base_for_this_file = os.path.join(original_dir_of_input_file, "_processing_temps_")
        msg = f"Temp folder for this file will be inside: \"{temp_base_for_this_file}\" (COPY_LOCALLY=False)"
    else:
        temp_base_for_this_file = config.MAIN_TEMP_DIR
        msg = f"Temp folder for this file will be inside: \"{temp_base_for_this_file}\" (COPY_LOCALLY=True)"

    _emit_or_print(msg, output_signal, fallback_color_code="\033[92m")

    if not os.path.exists(temp_base_for_this_file):
        try:
            os.makedirs(temp_base_for_this_file)
            msg_created = f"Created base for temp storage: \"{temp_base_for_this_file}\""
            _emit_or_print(msg_created, output_signal, fallback_color_code="\033[92m")
        except OSError as e:
            err_msg = f"ERROR: Failed to create base temporary directory {temp_base_for_this_file}: {e}"
            _emit_or_print(err_msg, error_signal, is_error=True)
            return None
    try:
        temp_dir = tempfile.mkdtemp(prefix=temp_dir_prefix, suffix=temp_dir_suffix, dir=temp_base_for_this_file)
        msg_actual = f"Created actual temp folder: \"{temp_dir}\""
        _emit_or_print(msg_actual, output_signal, fallback_color_code="\033[92m")
        return temp_dir
    except OSError as e:
        err_msg = f"ERROR: Failed to create temp directory in {temp_base_for_this_file}: {e}"
        _emit_or_print(err_msg, error_signal, is_error=True)
        return None
    except Exception as e:
        err_msg = f"ERROR: Unexpected error creating temp directory: {e}"
        _emit_or_print(err_msg, error_signal, is_error=True)
        return None


def move_files(src_dir, dest_dir_base, pattern, output_signal=None, error_signal=None, allow_overwrite=False):
    msg = f">> Moving files matching \"{pattern}\" from \"{src_dir}\" to \"{dest_dir_base}\" (Overwrite: {allow_overwrite})"
    _emit_or_print(msg, output_signal, fallback_color_code="\033[92m")

    moved_any_successfully = False
    try:
        abs_src_dir = os.path.abspath(src_dir)
        # Search only in the root of src_dir for the specific pattern, not recursively within temp subfolders unless intended.
        # If the pattern is like "*.chd", and files are directly in src_dir, recursive=False is better.
        # For now, assuming pattern can include wildcards that might require recursive if temp structure is complex.
        # If outputs are always flat in temp_dir, `glob.glob(os.path.join(abs_src_dir, pattern))` is enough.
        # The current glob with recursive=True and '**' handles files in subdirs of temp_dir.
        files_to_move = glob.glob(os.path.join(abs_src_dir, '**', pattern), recursive=True)
        files_to_move = [f for f in files_to_move if os.path.isfile(f)]

        if not files_to_move:
            warn_msg = f"WARNING: No files found matching pattern \"{pattern}\" in \"{abs_src_dir}\"."
            _emit_or_print(warn_msg, error_signal, fallback_color_code="yellow")
            return False

        if not os.path.exists(dest_dir_base):
            os.makedirs(dest_dir_base)
            _emit_or_print(f"Created destination directory: \"{dest_dir_base}\"", output_signal, fallback_color_code="green")

        for file_path in files_to_move:
            # relative_path_to_file is how the file is named/structured within temp relative to temp's root
            relative_path_to_file = os.path.relpath(file_path, abs_src_dir)
            # initial_dest_file_path is where we intend to move it, preserving subfolder structure from temp if any
            initial_dest_file_path = os.path.join(dest_dir_base, relative_path_to_file)

            current_dest_file_path = initial_dest_file_path
            dest_file_subdir = os.path.dirname(current_dest_file_path)

            try:
                if not os.path.exists(dest_file_subdir):
                    os.makedirs(dest_file_subdir)
                    _emit_or_print(f"Created destination sub-directory: \"{dest_file_subdir}\"", output_signal, fallback_color_code="green")

                if os.path.exists(current_dest_file_path):
                    if allow_overwrite:
                        warn_msg_overwrite = f"WARNING: Destination \"{current_dest_file_path}\" exists. Overwriting."
                        _emit_or_print(warn_msg_overwrite, error_signal, fallback_color_code="yellow")
                        try:
                            if os.path.isdir(current_dest_file_path):
                                shutil.rmtree(current_dest_file_path)
                            else:
                                os.remove(current_dest_file_path)
                        except OSError as e_rm:
                            err_msg_rm = f"ERROR: Failed to remove existing destination {current_dest_file_path} for overwrite: {e_rm}. Skipping."
                            _emit_or_print(err_msg_rm, error_signal, is_error=True)
                            continue
                    else:
                        # Implement renaming logic
                        _emit_or_print(f"INFO: Destination \"{current_dest_file_path}\" exists. Attempting to rename.", output_signal, fallback_color_code="cyan")
                        # Get the base name and extension of the intended destination filename
                        dest_filename = os.path.basename(initial_dest_file_path)
                        name_base, name_ext = os.path.splitext(dest_filename)
                        count = 1
                        while True:
                            new_filename_candidate = f"{name_base}_{count}{name_ext}"
                            potential_new_dest_path = os.path.join(dest_file_subdir, new_filename_candidate)
                            if not os.path.exists(potential_new_dest_path):
                                current_dest_file_path = potential_new_dest_path
                                _emit_or_print(f"INFO: Renaming output to: \"{current_dest_file_path}\"", output_signal, fallback_color_code="cyan")
                                break
                            count += 1
                            if count > 999:  # Safety break to prevent infinite loop for extreme cases
                                err_msg_rename_limit = f"ERROR: Could not find an available sequentially numbered name for \"{dest_filename}\" after 999 attempts. Skipping."
                                _emit_or_print(err_msg_rename_limit, error_signal, is_error=True)
                                continue  # Skip this file

                # Proceed with the move to current_dest_file_path (which might be original or renamed)
                shutil.move(file_path, current_dest_file_path)
                # Use os.path.basename for the display of what was moved from source,
                # and current_dest_file_path for the full destination path.
                move_msg_indiv = f"Moved \"{os.path.basename(file_path)}\" to \"{current_dest_file_path}\""
                _emit_or_print(move_msg_indiv, output_signal, fallback_color_code="green")
                moved_any_successfully = True
            except Exception as e_move:
                # Use relative_path_to_file in error if it's about the source, or current_dest_file_path if about dest
                err_msg_move_indiv = f"ERROR: Failed to move \"{os.path.basename(file_path)}\" to \"{current_dest_file_path}\": {e_move}"
                _emit_or_print(err_msg_move_indiv, error_signal, is_error=True)

        return moved_any_successfully
    except Exception as e_prep:
        err_msg_prep = f"ERROR: Preparing to move files: {e_prep}"
        _emit_or_print(err_msg_prep, error_signal, is_error=True)
        return False


def cleanup(temp_path, original_file_path=None, output_signal=None, error_signal=None):
    if temp_path and os.path.exists(temp_path):
        retries = 3
        while retries > 0:
            try:
                shutil.rmtree(temp_path)
                _emit_or_print(f"Removed temporary directory: \"{temp_path}\"", output_signal)
                break
            except OSError as e:
                retries -= 1
                err_msg = f"Failed to remove temp directory {temp_path}: {e}"
                if retries == 0:
                    _emit_or_print(f"ERROR: {err_msg} after multiple attempts.", error_signal, is_error=True)
                else:
                    _emit_or_print(f"WARNING: {err_msg}, retrying...", error_signal, fallback_color_code="\033[93m")
                    time.sleep(0.5)
            except Exception as e_unexpected_rm:
                _emit_or_print(f"ERROR: Unexpected error removing temp dir {temp_path}: {e_unexpected_rm}", error_signal, is_error=True)
                break

    if config.DELETE_SOURCE_ON_SUCCESS and original_file_path and os.path.exists(original_file_path):
        files_to_delete = [original_file_path]
        base_name, ext = os.path.splitext(original_file_path)
        if ext.lower() == '.cue':
            bin_pattern = f"{base_name}*.bin"
            cue_dir = os.path.dirname(original_file_path)
            associated_bins = glob.glob(os.path.join(cue_dir, bin_pattern))
            for bin_file in associated_bins:
                if os.path.exists(bin_file) and bin_file not in files_to_delete:
                    files_to_delete.append(bin_file)
                    _emit_or_print(f">> Found associated file for deletion: \"{os.path.basename(bin_file)}\"", output_signal, fallback_color_code="\033[92m")

        for file_to_delete_path in files_to_delete:
            if not os.path.exists(file_to_delete_path):
                continue
            _emit_or_print(f">> Attempting to send to Recycle Bin/Trash: \"{original_file_path}\"", output_signal, fallback_color_code="\033[92m")
            deleted_successfully_to_recycle = False

            if send2trash:
                try:
                    send2trash.send2trash(original_file_path)
                    _emit_or_print(f"Source file \"{os.path.basename(original_file_path)}\" sent to Recycle Bin/Trash.", output_signal)
                    deleted_successfully_to_recycle = True
                except Exception as e_s2t:
                    _emit_or_print(f"WARNING: send2trash failed for \"{original_file_path}\": {e_s2t}. Trying next method.", error_signal, fallback_color_code="\033[93m")
            else:
                _emit_or_print("INFO: send2trash library not available. Trying next method.", output_signal, fallback_color_code="\033[96m")

            if not deleted_successfully_to_recycle and os.path.exists(config.TOOL_RECYCLE):
                _emit_or_print(f">> Attempting to use recycle.exe for \"{original_file_path}\"", output_signal, fallback_color_code="\033[92m")
                recycle_success = run_command(
                    [config.TOOL_RECYCLE, '-f', original_file_path],
                    output_signal=output_signal, error_signal=error_signal
                )
                if recycle_success:
                    _emit_or_print(f"Source file \"{os.path.basename(original_file_path)}\" sent to Recycle Bin via recycle.exe.", output_signal)
                    deleted_successfully_to_recycle = True
                else:
                    _emit_or_print(f"WARNING: recycle.exe failed for \"{original_file_path}\". Trying next method.", error_signal, fallback_color_code="\033[93m")
            elif not deleted_successfully_to_recycle:
                _emit_or_print(f"INFO: recycle.exe not found at {config.TOOL_RECYCLE} or not needed. Trying next method.", output_signal, fallback_color_code="\033[96m")

            if not deleted_successfully_to_recycle:
                _emit_or_print(f"WARNING: All Recycle Bin/Trash methods failed or unavailable. Attempting permanent delete for \"{original_file_path}\".", error_signal, fallback_color_code="\033[93m")
                try:
                    os.remove(original_file_path)
                    _emit_or_print(f"Source file \"{os.path.basename(original_file_path)}\" permanently deleted using os.remove.", output_signal, fallback_color_code="\033[93m")
                except OSError as remove_e:
                    err_msg_del = f"ERROR: Failed to permanently delete source {original_file_path} using os.remove: {remove_e}"
                    _emit_or_print(err_msg_del, error_signal, is_error=True)
    return


def extract_archive(archive_path, output_dir, output_signal=None, error_signal=None):
    msg = f">> Extracting: \"{os.path.basename(archive_path)}\" to \"{output_dir}\""
    _emit_or_print(msg, output_signal, fallback_color_code="\033[92m")
    command = [config.TOOL_7ZA, 'x', archive_path, f'-o{output_dir}', '-y']
    return run_command(command, output_signal=output_signal, error_signal=error_signal)


def process_file(file_path, conversion_func, format_out, format_out2=None,
                 output_signal=None, error_signal=None, explicit_output_dir=None, allow_overwrite=False,
                 target_format_from_worker=None, stage_reporter=None):  # Added stage_reporter
    """
    Processes a single file: sets up temp dir, copies if needed, runs conversion,
    moves output, and cleans up.
    Args:
        ...
        stage_reporter (callable, optional): A function to call to report progress stages.
                                            It expects one argument: stage_description (str).
    """
    original_dir_of_input_file = os.path.dirname(file_path)
    file_name_base = os.path.basename(file_path)
    name_part, _ = os.path.splitext(file_name_base)

    # Determine the final base directory for output files
    final_output_destination_base = explicit_output_dir if explicit_output_dir else original_dir_of_input_file

    # Ensure the final output destination base directory exists
    if not os.path.exists(final_output_destination_base):
        try:
            os.makedirs(final_output_destination_base)
            _emit_or_print(f"Created final output destination directory: \"{final_output_destination_base}\"", output_signal, fallback_color_code="\033[92m")
        except OSError as e:
            err_msg = f"ERROR: Failed to create final output dir {final_output_destination_base}: {e}."
            _emit_or_print(err_msg, error_signal, is_error=True)
            return False # Cannot proceed if output dir cannot be made

    # --- Stage 1: Preparation ---
    if stage_reporter:
        stage_reporter("Preparing")

    temp_path_for_this_file = create_temp_dir(file_path, output_signal=output_signal, error_signal=error_signal)
    if temp_path_for_this_file is None:
        # Error already logged by create_temp_dir
        return False

    path_to_process_in_temp = file_path  # Default to original path if not copying locally
    if config.COPY_LOCALLY:
        msg_copy = f">> Copying \"{file_name_base}\" to \"{temp_path_for_this_file}\""
        _emit_or_print(msg_copy, output_signal, fallback_color_code="\033[92m")
        try:
            target_copy_path = os.path.join(temp_path_for_this_file, file_name_base)
            if os.path.isdir(file_path):  # Handle copying directories if input is a folder
                shutil.copytree(file_path, target_copy_path, dirs_exist_ok=True)
            else:
                shutil.copy2(file_path, target_copy_path)
            path_to_process_in_temp = target_copy_path
        except Exception as e:
            err_msg_copy = f"ERROR: Failed to copy \"{file_name_base}\" to \"{temp_path_for_this_file}\": {e}"
            _emit_or_print(err_msg_copy, error_signal, is_error=True)
            cleanup(temp_path_for_this_file, output_signal=output_signal, error_signal=error_signal)
            return False
    else:
        _emit_or_print(f">> Processing \"{file_name_base}\" with outputs to temp. (COPY_LOCALLY=False)", output_signal, fallback_color_code="\033[92m")

    # --- Stage 2: Conversion ---
    if stage_reporter:
        stage_reporter("Converting")

    # Prepare arguments for the conversion function
    conversion_args = {
        "processing_path": path_to_process_in_temp,
        "temp_dir": temp_path_for_this_file, # The conversion function writes its output here
        "name": name_part, # Base name for output files
        "output_signal": output_signal,
        "error_signal": error_signal
    }
    # Conditionally add target_format_from_worker if the conversion function expects it
    # This relies on the conversion functions being designed to accept **kwargs or specific named args
    if target_format_from_worker and hasattr(conversion_func, '__code__') and 'target_format_from_worker' in conversion_func.__code__.co_varnames:
        conversion_args["target_format_from_worker"] = target_format_from_worker
    
    conversion_successful = conversion_func(**conversion_args)

    # --- Stage 3: Finalization ---
    if stage_reporter:
        stage_reporter("Finalizing")

    if conversion_successful:
        primary_move_ok = False
        # Determine the primary output extension that was actually used/targeted by the conversion
        effective_format_out = target_format_from_worker if target_format_from_worker and hasattr(conversion_func, '__code__') and 'target_format_from_worker' in conversion_func.__code__.co_varnames else format_out

        if effective_format_out: # If there's a primary output file expected (not just folder extraction)
            # The pattern should match what the conversion function actually produced in temp_dir
            # Usually it's name_part + effective_format_out
            # expected_primary_output_name = f"{name_part}.{effective_format_out}"
            # Search for the primary output file(s) in the temp_dir (could be in subdirs if conversion_func creates them)
            found_primary_in_temp = glob.glob(os.path.join(temp_path_for_this_file, '**', f"*.{effective_format_out}"), recursive=True)
            found_primary_in_temp = [f for f in found_primary_in_temp if os.path.isfile(f)]


            if not found_primary_in_temp:
                err_msg_missing = f"ERROR: Expected primary output (*.{effective_format_out}) not found in temp for \"{file_name_base}\"."
                _emit_or_print(err_msg_missing, error_signal, is_error=True)
                primary_move_ok = False # Critical if primary output is missing
            else:
                # Move the primary output file(s)
                # The pattern for move_files should be specific to the expected output in temp_dir.
                # If conversion_func guarantees output is flat in temp_dir: `f"{name_part}.{effective_format_out}"`
                # If it can be nested, `f"*.{effective_format_out}"` with recursive search in move_files is okay.
                if move_files(temp_path_for_this_file, final_output_destination_base, f"*.{effective_format_out}",
                              output_signal, error_signal, allow_overwrite):
                    primary_move_ok = True
                else:
                    # move_files logs its own errors if it fails to move *any* matched file.
                    # This specific error is if move_files indicated no success (e.g., all skipped or error on all).
                    err_msg_move_fail = f"ERROR: Primary output (*.{effective_format_out}) for \"{file_name_base}\" was not moved (skipped or error)."
                    _emit_or_print(err_msg_move_fail, error_signal, is_error=True)
                    primary_move_ok = False


            # Handle secondary output files (e.g., .bin for .cue) if primary move was okay
            if primary_move_ok and format_out2:
                if not move_files(temp_path_for_this_file, final_output_destination_base, f"*.{format_out2}",
                                  output_signal, error_signal, allow_overwrite):
                    # This might be a warning rather than a critical failure if primary is okay
                    warn_msg_move2 = f"WARNING: Secondary output (*.{format_out2}) move failed or files skipped for \"{file_name_base}\"."
                    _emit_or_print(warn_msg_move2, error_signal, fallback_color_code="\033[93m")
            
            # Special handling for GDI: move .bin and .raw files if .gdi was moved
            if effective_format_out == 'gdi' and primary_move_ok:
                # These patterns assume they are flat in temp_dir or move_files handles recursion
                move_files(temp_path_for_this_file, final_output_destination_base, "*.bin", output_signal, error_signal, allow_overwrite)
                move_files(temp_path_for_this_file, final_output_destination_base, "*.raw", output_signal, error_signal, allow_overwrite)

        else: # Case where format_out is None or empty (e.g., "Extract archive to folder")
            if conversion_func.__name__ == "extract_archive_to_folder_routine":
                # The temp_path_for_this_file *is* the extracted content.
                # We need to move its *contents* to the final destination.
                _emit_or_print(f">> Moving extracted contents from \"{temp_path_for_this_file}\" to \"{final_output_destination_base}\"", output_signal, fallback_color_code="\033[92m")
                # Create a subfolder in the destination named after the archive
                archive_output_folder = os.path.join(final_output_destination_base, name_part) # e.g., output_dir/myarchive_files
                if not os.path.exists(archive_output_folder):
                    os.makedirs(archive_output_folder)
                
                all_moved_ok = True
                for item_name in os.listdir(temp_path_for_this_file):
                    s_item = os.path.join(temp_path_for_this_file, item_name)
                    d_item = os.path.join(archive_output_folder, item_name)
                    try:
                        if os.path.exists(d_item):
                            if allow_overwrite:
                                if os.path.isdir(d_item): shutil.rmtree(d_item)
                                else: os.remove(d_item)
                            else:
                                _emit_or_print(f"Skipping existing item in destination: {d_item}", error_signal, fallback_color_code="\033[93m")
                                continue # Skip this item
                        shutil.move(s_item, d_item)
                    except Exception as e_move_item:
                        _emit_or_print(f"ERROR moving extracted item {item_name}: {e_move_item}", error_signal, is_error=True)
                        all_moved_ok = False
                primary_move_ok = all_moved_ok # Success depends on all items moving
            else:
                # If format_out is None but it's not extract_archive_to_folder, assume success if conversion_func was successful
                # (e.g. for info/verify jobs that don't produce files)
                 primary_move_ok = True


        if primary_move_ok: # If primary output (or folder contents) handled successfully
            cleanup(temp_path_for_this_file, file_path if config.DELETE_SOURCE_ON_SUCCESS else None, output_signal, error_signal)
            return True
        else: # If primary output move failed or was missing
            cleanup(temp_path_for_this_file, output_signal=output_signal, error_signal=error_signal) # Cleanup temp, but don't delete source
            return False
    else: # Conversion failed
        cleanup(temp_path_for_this_file, output_signal=output_signal, error_signal=error_signal) # Cleanup temp, don't delete source
        return False


def process_input(input_path, conversion_func, formats_in, format_out, format_out2=None):
    # CLI specific logic, uses print directly for its top-level messages
    if isinstance(formats_in, str):
        formats_in = [formats_in]
    formats_in = [f.lower() for f in formats_in]
    # effective_format_out_cli = format_out.lower() if format_out else None

    if os.path.isdir(input_path):
        # ... (CLI folder processing logic as in utils_py_log_helper) ...
        # When calling process_file for CLI:
        # process_file(file_path_item, conversion_func, effective_format_out_cli, format_out2,
        #              allow_overwrite=False, # CLI defaults to no overwrite
        #              target_format_from_worker=effective_format_out_cli)
        pass
    elif os.path.isfile(input_path):
        # ... (CLI file processing logic as in utils_py_log_helper) ...
        # process_file(input_path, conversion_func, effective_format_out_cli, format_out2,
        #              allow_overwrite=False,
        #              target_format_from_worker=effective_format_out_cli)
        pass
    # ... (rest of CLI process_input as in utils_py_log_helper) ...
    pass


def print_help(formats_in, format_out, format_out2=None):  # For CLI
    # ... (remains unchanged) ...
    pass
