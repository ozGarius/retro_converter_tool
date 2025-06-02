# -*- coding: utf-8 -*-
# /converter_tools/utils.py (Error Handling Enhancements & Direct File Check with Pause)

import os
import subprocess
import shutil
import glob
import time
import tempfile
import config
import re

try:
    import send2trash
except ImportError:
    send2trash = None

ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _emit_or_print(message, signal=None, fallback_color_code=None, is_error=False):
    """
    Emits a message via a Qt signal if provided, otherwise prints to console.
    Optionally formats the fallback print message with a color code.
    If is_error is True, uses a default error color if no color_code is given.
    """
    color_map = {
        "red": "\033[91m", "green": "\033[92m", "blue": "\033[94m",
        "yellow": "\033[93m", "magenta": "\033[95m", "cyan": "\033[96m",
        "white": "\033[97m]", "black": "\033[30m",
        "bright_red": "\033[1;91m", "bright_green": "\033[1;92m", "bright_blue": "\033[1;94m",
        "bright_yellow": "\033[1;93m", "bright_magenta": "\033[1;95m", "bright_cyan": "\033[1;96m",
        "bright_white": "\033[1;97m", "bold_red": "\033[1;31m", "italic_green": "\033[3;92m",
        "underline_blue": "\033[4;94m",
    }

    if signal:
        signal.emit(message)
    else:
        color_code_to_use = None
        if fallback_color_code:
            color_code_to_use = color_map.get(
                fallback_color_code.lower(), fallback_color_code)

        if color_code_to_use:
            print(f"{color_code_to_use}{message}\033[0m")
        elif is_error:
            print(f"\033[91m{message}\033[0m")  # Default error color
        else:
            print(f"\033[92m{message}\033[0m")  # Default success/info color


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
        _emit_or_print("ERROR: Missing required tools:", is_error=True)
        for tool in missing_tools:
            _emit_or_print(f"- {tool}", is_error=True)
        _emit_or_print(
            "Ensure 'converter_tools' folder is in the same directory and contains all executables.", is_error=True)
        _emit_or_print(
            f"Expected tools directory: {config.TOOLS_DIR}", is_error=True)
        return False
    return True


def get_free_disk_space_gb(path):
    try:
        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024**3)
        return free_gb
    except AttributeError:
        _emit_or_print(
            "shutil.disk_usage not available to check disk space.", is_error=True)
        return None
    except Exception as e:
        _emit_or_print(
            f"Error checking disk space for {path}: {e}", is_error=True)
        return None


def run_command(command, cwd=None, output_signal=None, error_signal=None, known_error_codes=None):
    command_str = ' '.join(command)
    _emit_or_print(f">> Running: {command_str}",
                   output_signal, fallback_color_code="green")

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
            elif stderr_clean and stderr_clean not in err_msg:
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


def create_temp_dir(base_name_of_input_file, output_signal=None, error_signal=None):
    original_dir_of_input_file = os.path.dirname(base_name_of_input_file)
    file_name_part_for_prefix = os.path.splitext(
        os.path.basename(base_name_of_input_file))[0]
    temp_dir_prefix = f"{file_name_part_for_prefix}_"
    temp_dir_suffix = "_temp"

    if not config.COPY_LOCALLY:
        temp_base_for_this_file = os.path.join(
            original_dir_of_input_file, "_processing_temps_")
        msg = f"Temp folder for this file will be inside: \"{temp_base_for_this_file}\" (COPY_LOCALLY=False)"
    else:
        temp_base_for_this_file = config.MAIN_TEMP_DIR
        msg = f"Temp folder for this file will be inside: \"{temp_base_for_this_file}\" (COPY_LOCALLY=True)"
    _emit_or_print(msg, output_signal, fallback_color_code="green")

    if not os.path.exists(temp_base_for_this_file):
        try:
            os.makedirs(temp_base_for_this_file)
            _emit_or_print(
                f"Created base for temp storage: \"{temp_base_for_this_file}\"", output_signal, fallback_color_code="green")
        except OSError as e:
            _emit_or_print(
                f"ERROR: Failed to create base temporary directory {temp_base_for_this_file}: {e}", error_signal, is_error=True)
            return None
    try:
        temp_dir = tempfile.mkdtemp(
            prefix=temp_dir_prefix, suffix=temp_dir_suffix, dir=temp_base_for_this_file)
        _emit_or_print(
            f"Created actual temp folder: \"{temp_dir}\"", output_signal, fallback_color_code="green")
        return temp_dir
    except Exception as e:
        _emit_or_print(
            f"ERROR: Failed to create temp directory in {temp_base_for_this_file}: {e}", error_signal, is_error=True)
        return None


def move_files(src_dir, dest_dir_base, pattern, output_signal=None, error_signal=None, allow_overwrite=False):
    _emit_or_print(f">> Moving files matching \"{pattern}\" from \"{src_dir}\" to \"{dest_dir_base}\" (Overwrite: {allow_overwrite})",
                   output_signal, fallback_color_code="green")
    moved_any_successfully = False
    try:
        abs_src_dir = os.path.abspath(src_dir)
        files_to_move = glob.glob(os.path.join(
            abs_src_dir, '**', pattern), recursive=True)
        files_to_move = [f for f in files_to_move if os.path.isfile(f)]

        if not files_to_move:
            _emit_or_print(f"WARNING: No files found matching pattern \"{pattern}\" in \"{abs_src_dir}\" or its subdirectories.",
                           error_signal, fallback_color_code="yellow")
            return False

        if not os.path.exists(dest_dir_base):
            os.makedirs(dest_dir_base)
            _emit_or_print(
                f"Created destination directory: \"{dest_dir_base}\"", output_signal, fallback_color_code="green")

        for file_path in files_to_move:
            relative_path_to_file = os.path.relpath(file_path, abs_src_dir)
            initial_dest_file_path = os.path.join(
                dest_dir_base, relative_path_to_file)
            current_dest_file_path = initial_dest_file_path
            dest_file_subdir = os.path.dirname(current_dest_file_path)

            try:
                if not os.path.exists(dest_file_subdir):
                    os.makedirs(dest_file_subdir)

                if os.path.exists(current_dest_file_path):
                    if allow_overwrite:
                        _emit_or_print(f"WARNING: Destination \"{current_dest_file_path}\" exists. Overwriting.",
                                       error_signal, fallback_color_code="yellow")
                        try:
                            if os.path.isdir(current_dest_file_path):
                                shutil.rmtree(current_dest_file_path)
                            else:
                                os.remove(current_dest_file_path)
                        except OSError as e_rm:
                            _emit_or_print(f"ERROR: Failed to remove existing destination {current_dest_file_path} for overwrite: {e_rm}. Skipping.",
                                           error_signal, is_error=True)
                            continue
                    else:
                        dest_filename_base, dest_filename_ext = os.path.splitext(
                            os.path.basename(initial_dest_file_path))
                        count = 1
                        while True:
                            new_filename = f"{dest_filename_base}_{count}{dest_filename_ext}"
                            potential_new_dest_path = os.path.join(
                                dest_file_subdir, new_filename)
                            if not os.path.exists(potential_new_dest_path):
                                current_dest_file_path = potential_new_dest_path
                                _emit_or_print(
                                    f"INFO: Renaming output to: \"{current_dest_file_path}\"", output_signal, fallback_color_code="cyan")
                                break
                            count += 1
                            if count > 999:
                                _emit_or_print(f"ERROR: Could not find an available sequentially numbered name for \"{initial_dest_file_path}\" after 999 attempts. Skipping.",
                                               error_signal, is_error=True)
                                continue

                shutil.move(file_path, current_dest_file_path)
                _emit_or_print(f"Moved \"{os.path.basename(file_path)}\" to \"{current_dest_file_path}\"",
                               output_signal, fallback_color_code="green")
                moved_any_successfully = True
            except Exception as e_move:
                _emit_or_print(f"ERROR: Failed to move \"{os.path.basename(file_path)}\" to \"{current_dest_file_path}\": {e_move}",
                               error_signal, is_error=True)
        return moved_any_successfully
    except Exception as e_prep:
        _emit_or_print(
            f"ERROR: Preparing to move files: {e_prep}", error_signal, is_error=True)
        return False


def cleanup(temp_path, original_file_path=None, output_signal=None, error_signal=None):
    if temp_path and os.path.exists(temp_path):
        retries = 3
        while retries > 0:
            try:
                shutil.rmtree(temp_path)
                _emit_or_print(
                    f"Removed temporary directory: \"{temp_path}\"", output_signal)
                break
            except OSError as e:
                retries -= 1
                err_msg = f"Failed to remove temp directory {temp_path}: {e}"
                if retries == 0:
                    _emit_or_print(
                        f"ERROR: {err_msg} after multiple attempts.", error_signal, is_error=True)
                else:
                    _emit_or_print(
                        f"WARNING: {err_msg}, retrying...", error_signal, fallback_color_code="yellow")
                    time.sleep(0.5)
            except Exception as e_unexpected_rm:
                _emit_or_print(
                    f"ERROR: Unexpected error removing temp dir {temp_path}: {e_unexpected_rm}", error_signal, is_error=True)
                break

    if config.DELETE_SOURCE_ON_SUCCESS and original_file_path and os.path.exists(original_file_path):
        files_to_delete = [original_file_path]
        base_name, ext = os.path.splitext(original_file_path)
        if ext.lower() == '.cue':
            bin_pattern = f"{re.escape(base_name)}*.bin"
            cue_dir = os.path.dirname(original_file_path)
            associated_bins = glob.glob(os.path.join(cue_dir, bin_pattern))
            for bin_file in associated_bins:
                if os.path.exists(bin_file) and bin_file.lower().startswith(base_name.lower()) and bin_file.lower().endswith(".bin"):
                    if bin_file not in files_to_delete:
                        files_to_delete.append(bin_file)
                        _emit_or_print(
                            f">> Found associated file for deletion: \"{os.path.basename(bin_file)}\"", output_signal, fallback_color_code="green")

        for file_to_delete_path in files_to_delete:
            if not os.path.exists(file_to_delete_path):
                continue

            _emit_or_print(
                f">> Attempting to send to Recycle Bin/Trash: \"{os.path.basename(file_to_delete_path)}\"", output_signal, fallback_color_code="green")
            deleted_successfully_to_recycle = False
            if send2trash:
                try:
                    send2trash.send2trash(file_to_delete_path)
                    _emit_or_print(
                        f"Source file \"{os.path.basename(file_to_delete_path)}\" sent to Recycle Bin/Trash.", output_signal)
                    deleted_successfully_to_recycle = True
                except Exception as e_s2t:
                    _emit_or_print(
                        f"WARNING: send2trash failed for \"{file_to_delete_path}\": {e_s2t}. Trying next method.", error_signal, fallback_color_code="yellow")

            if not deleted_successfully_to_recycle and os.name == 'nt' and os.path.exists(config.TOOL_RECYCLE):
                _emit_or_print(
                    f">> Attempting to use recycle.exe for \"{file_to_delete_path}\"", output_signal, fallback_color_code="green")
                recycle_success = run_command(
                    [config.TOOL_RECYCLE, '-f', file_to_delete_path], output_signal=output_signal, error_signal=error_signal)
                if recycle_success:
                    _emit_or_print(
                        f"Source file \"{os.path.basename(file_to_delete_path)}\" sent to Recycle Bin via recycle.exe.", output_signal)
                    deleted_successfully_to_recycle = True
                else:
                    _emit_or_print(
                        f"WARNING: recycle.exe failed for \"{file_to_delete_path}\". Trying permanent delete.", error_signal, fallback_color_code="yellow")

            if not deleted_successfully_to_recycle:
                _emit_or_print(
                    f"WARNING: Recycle Bin/Trash methods failed or unavailable. Attempting permanent delete for \"{file_to_delete_path}\".", error_signal, fallback_color_code="yellow")
                try:
                    os.remove(file_to_delete_path)
                    _emit_or_print(
                        f"Source file \"{os.path.basename(file_to_delete_path)}\" permanently deleted.", output_signal, fallback_color_code="yellow")
                except OSError as remove_e:
                    _emit_or_print(
                        f"ERROR: Failed to permanently delete source {file_to_delete_path}: {remove_e}", error_signal, is_error=True)


def extract_archive(archive_path, output_dir, output_signal=None, error_signal=None):
    _emit_or_print(f">> Extracting: \"{os.path.basename(archive_path)}\" to \"{output_dir}\"",
                   output_signal, fallback_color_code="green")
    command = [config.TOOL_7ZA, 'x', archive_path, f'-o{output_dir}', '-y']
    return run_command(command, output_signal=output_signal, error_signal=error_signal)


def process_file(file_path, conversion_func, format_out, format_out2=None,
                 output_signal=None, error_signal=None, explicit_output_dir=None, allow_overwrite=False,
                 target_format_from_worker=None, stage_reporter=None, file_progress_reporter=None):
    original_dir_of_input_file = os.path.dirname(file_path)
    file_name_base_with_ext = os.path.basename(file_path)
    name_part, _ = os.path.splitext(file_name_base_with_ext)

    final_output_destination_base = explicit_output_dir if explicit_output_dir else original_dir_of_input_file
    if not os.path.exists(final_output_destination_base):
        try:
            os.makedirs(final_output_destination_base)
        except OSError as e:
            _emit_or_print(
                f"ERROR: Failed to create final output dir {final_output_destination_base}: {e}.", error_signal, is_error=True)
            return False

    if stage_reporter:
        stage_reporter("Preparing")
    temp_path_for_this_file = create_temp_dir(
        file_path, output_signal=output_signal, error_signal=error_signal)
    if temp_path_for_this_file is None:
        return False

    path_to_process_in_temp = file_path
    if config.COPY_LOCALLY:
        _emit_or_print(f">> Copying \"{file_name_base_with_ext}\" to \"{temp_path_for_this_file}\"",
                       output_signal, fallback_color_code="green")
        try:
            target_copy_path = os.path.join(
                temp_path_for_this_file, file_name_base_with_ext)
            if os.path.isdir(file_path):
                shutil.copytree(file_path, target_copy_path,
                                dirs_exist_ok=True)
            else:
                shutil.copy2(file_path, target_copy_path)
            path_to_process_in_temp = target_copy_path

            # Check for .cue or .gdi files to copy dependencies
            _, file_ext = os.path.splitext(file_path)
            file_ext = file_ext.lower()

            dependencies_to_copy = []
            if file_ext == '.cue':
                dependencies_to_copy = _get_cue_dependencies(file_path)
            elif file_ext == '.gdi':
                dependencies_to_copy = _get_gdi_dependencies(file_path)

            for dep_path in dependencies_to_copy:
                dep_filename = os.path.basename(dep_path)
                temp_dep_dest_path = os.path.join(temp_path_for_this_file, dep_filename)
                try:
                    if not os.path.exists(dep_path):
                        _emit_or_print(f"WARNING: Dependent file \"{dep_filename}\" not found at \"{dep_path}\". Skipping copy.", 
                                       error_signal, fallback_color_code="yellow")
                        continue # Skip to next dependency

                    _emit_or_print(f">> Copying dependent file \"{dep_filename}\" to \"{temp_dep_dest_path}\"", 
                                   output_signal, fallback_color_code="green")
                    shutil.copy2(dep_path, temp_dep_dest_path)
                except Exception as dep_e:
                    _emit_or_print(f"ERROR: Failed to copy dependent file \"{dep_filename}\" to temp: {dep_e}", 
                                   error_signal, is_error=True)
                    # Decide if this error should halt the entire process.
                    # For now, we log and continue, the main conversion might fail later.

        except Exception as e:
            _emit_or_print(
                f"ERROR: Failed to copy \"{file_name_base_with_ext}\" or its dependencies to temp: {e}", error_signal, is_error=True)
            cleanup(temp_path_for_this_file,
                    output_signal=output_signal, error_signal=error_signal)
            return False
    else:
        _emit_or_print(f">> Processing \"{file_name_base_with_ext}\" with outputs to temp. (COPY_LOCALLY=False)",
                       output_signal, fallback_color_code="green")

    if stage_reporter:
        stage_reporter("Converting")
    if file_progress_reporter:
        file_progress_reporter(33)  # Conversion starting
    conversion_args = {
        "processing_path": path_to_process_in_temp,
        "temp_dir": temp_path_for_this_file,
        "name": name_part,
        "output_signal": output_signal,
        "error_signal": error_signal
    }
    if target_format_from_worker and hasattr(conversion_func, '__code__') and 'target_format_from_worker' in conversion_func.__code__.co_varnames:
        conversion_args["target_format_from_worker"] = target_format_from_worker
    conversion_successful = conversion_func(**conversion_args)

    # *** ADDED PAUSE FOR DEBUGGING ***
    # if output_signal is None: # Assuming CLI mode if no output_signal
    # _emit_or_print(
    #     f"\n--- PAUSED FOR DEBUGGING (process_file after conversion_func for '{file_name_base_with_ext}') ---", fallback_color_code="magenta")
    # _emit_or_print(
    #     f"Conversion successful reported by function: {conversion_successful}", fallback_color_code="magenta")
    # _emit_or_print(
    #     f"Temp directory is: {temp_path_for_this_file}", fallback_color_code="magenta")
    # _emit_or_print("You can now inspect the temp directory.",
    #                fallback_color_code="magenta")
    # input("Press Enter to continue...")
    # *** END OF ADDED PAUSE ***

    if stage_reporter:
        stage_reporter("Finalizing")
    if file_progress_reporter:
        file_progress_reporter(66)  # Finalizing stage
    if conversion_successful:
        primary_move_ok = False
        effective_format_out = target_format_from_worker if target_format_from_worker and \
            hasattr(conversion_func, '__code__') and \
            'target_format_from_worker' in conversion_func.__code__.co_varnames else format_out

        if effective_format_out:
            expected_primary_output_filename = f"{name_part}.{effective_format_out}"
            expected_primary_output_full_path = os.path.join(
                temp_path_for_this_file, expected_primary_output_filename)

            found_primary_in_temp = []
            if os.path.isfile(expected_primary_output_full_path):
                found_primary_in_temp.append(expected_primary_output_full_path)
                _emit_or_print(
                    f"DEBUG_UTIL: Successfully located expected primary output: {expected_primary_output_full_path}", output_signal)
            else:
                _emit_or_print(
                    f"DEBUG_UTIL: Direct check os.path.isfile failed for: {expected_primary_output_full_path}", error_signal, is_error=True)
                all_files_in_temp_root = glob.glob(
                    os.path.join(temp_path_for_this_file, "*"))
                _emit_or_print(
                    f"DEBUG_UTIL: Contents of temp root '{temp_path_for_this_file}': {all_files_in_temp_root}", output_signal)

                original_glob_results = glob.glob(os.path.join(
                    temp_path_for_this_file, '**', f"*.{effective_format_out}"), recursive=True)
                _emit_or_print(
                    f"DEBUG_UTIL: Original glob '**/ *.{effective_format_out}' found: {original_glob_results}", output_signal)

            if not found_primary_in_temp:
                err_msg_missing = f"ERROR: Expected primary output ('{expected_primary_output_filename}') not found in temp dir '{temp_path_for_this_file}' for input \"{file_name_base_with_ext}\"."
                _emit_or_print(err_msg_missing, error_signal, is_error=True)
                primary_move_ok = False
            else:
                if move_files(temp_path_for_this_file, final_output_destination_base, expected_primary_output_filename,
                              output_signal, error_signal, allow_overwrite):
                    primary_move_ok = True
                else:
                    _emit_or_print(f"ERROR: Primary output ('{expected_primary_output_filename}') for \"{file_name_base_with_ext}\" was not moved.",
                                   error_signal, is_error=True)
                    primary_move_ok = False

            if primary_move_ok and format_out2:
                if not move_files(temp_path_for_this_file, final_output_destination_base, f"*.{format_out2}",
                                  output_signal, error_signal, allow_overwrite):
                    _emit_or_print(f"WARNING: Secondary output (*.{format_out2}) move failed or files skipped for \"{file_name_base_with_ext}\".",
                                   error_signal, fallback_color_code="yellow")

            if effective_format_out == 'gdi' and primary_move_ok:
                move_files(temp_path_for_this_file, final_output_destination_base,
                           "*.bin", output_signal, error_signal, allow_overwrite)
                move_files(temp_path_for_this_file, final_output_destination_base,
                           "*.raw", output_signal, error_signal, allow_overwrite)

        else:
            if conversion_func.__name__ == "extract_archive_to_folder_routine":
                archive_output_folder = os.path.join(
                    final_output_destination_base, name_part)
                if not os.path.exists(archive_output_folder):
                    os.makedirs(archive_output_folder)

                all_moved_ok = True
                for item_name in os.listdir(temp_path_for_this_file):
                    s_item = os.path.join(temp_path_for_this_file, item_name)
                    d_item = os.path.join(archive_output_folder, item_name)
                    try:
                        if os.path.exists(d_item):
                            if allow_overwrite:
                                if os.path.isdir(d_item):
                                    shutil.rmtree(d_item)
                                else:
                                    os.remove(d_item)
                            else:
                                _emit_or_print(
                                    f"Skipping existing item in destination: {d_item}", error_signal, fallback_color_code="yellow")
                                continue
                        shutil.move(s_item, d_item)
                    except Exception as e_move_item:
                        _emit_or_print(
                            f"ERROR moving extracted item {item_name}: {e_move_item}", error_signal, is_error=True)
                        all_moved_ok = False
                primary_move_ok = all_moved_ok
            else:
                primary_move_ok = True

        if primary_move_ok:
            if file_progress_reporter:
                file_progress_reporter(100)  # Complete
            cleanup(temp_path_for_this_file,
                    file_path if config.DELETE_SOURCE_ON_SUCCESS else None, output_signal, error_signal)
            return True
        else:
            cleanup(temp_path_for_this_file,
                    output_signal=output_signal, error_signal=error_signal)
            return False
    else:
        cleanup(temp_path_for_this_file, output_signal=output_signal,
                error_signal=error_signal)
        return False


def process_input(input_path, conversion_func, formats_in, format_out, format_out2=None):
    pass


def print_help(formats_in, format_out, format_out2=None):
    _emit_or_print(
        "CLI Help Text Placeholder - Retain your original help text here.", fallback_color_code="cyan")
    pass


def _get_cue_dependencies(cue_file_path):
    """
    Parses a .cue file and returns a list of absolute paths to dependent files.
    """
    dependencies = []
    cue_dir = os.path.dirname(cue_file_path)

    try:
        with open(cue_file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith("FILE"):
                    # Try to extract filename using regex, handling quotes
                    match = re.search(r'FILE\s+"?([^"]+)"?\s+\w+', line)
                    if match:
                        filename = match.group(1)
                        # Construct absolute path
                        abs_path = os.path.join(cue_dir, filename)
                        dependencies.append(os.path.normpath(abs_path))
                    else:
                        # Fallback for lines that might not have quotes but are valid
                        parts = line.split(maxsplit=2)
                        if len(parts) > 1:
                            # Remove potential surrounding quotes manually if regex failed
                            filename = parts[1].strip('"')
                            abs_path = os.path.join(cue_dir, filename)
                            dependencies.append(os.path.normpath(abs_path))
                        else:
                            _emit_or_print(f"Could not parse FILE line in CUE: {line}", is_error=True)
                            
    except FileNotFoundError:
        _emit_or_print(f"ERROR: CUE file not found: {cue_file_path}", is_error=True)
        return []
    except IOError as e:
        _emit_or_print(f"ERROR: Could not read CUE file: {cue_file_path} - {e}", is_error=True)
        return []
    except Exception as e:
        _emit_or_print(f"ERROR: Unexpected error processing CUE file: {cue_file_path} - {e}", is_error=True)
        return []
        
    return dependencies


def _get_gdi_dependencies(gdi_file_path):
    """
    Parses a .gdi file and returns a list of absolute paths to dependent track files.
    """
    dependencies = []
    gdi_dir = os.path.dirname(gdi_file_path)

    try:
        with open(gdi_file_path, 'r', encoding='utf-8', errors='replace') as f:
            # The first line usually contains the number of tracks, which we can skip or parse if needed.
            # For now, we'll just iterate through all lines.
            for line in f:
                line = line.strip()
                parts = line.split()
                
                # GDI track lines typically start with a track number (integer)
                # and have the filename as the 5th element (index 4).
                # Example: 1 0 4 2352 track01.bin 0
                if len(parts) >= 5 and parts[0].isdigit():
                    filename = parts[4]
                    # Filenames in GDI are not typically quoted, but we strip them just in case.
                    filename = filename.strip('"') 
                    
                    # Construct absolute path
                    abs_path = os.path.join(gdi_dir, filename)
                    dependencies.append(os.path.normpath(abs_path))
                # Silently ignore lines that don't match the expected format
                # (e.g., the first line with track count, or comments if any)

    except FileNotFoundError:
        _emit_or_print(f"ERROR: GDI file not found: {gdi_file_path}", is_error=True)
        return []
    except IOError as e:
        _emit_or_print(f"ERROR: Could not read GDI file: {gdi_file_path} - {e}", is_error=True)
        return []
    except Exception as e:
        _emit_or_print(f"ERROR: Unexpected error processing GDI file: {gdi_file_path} - {e}", is_error=True)
        return []
        
    return dependencies
