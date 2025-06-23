# -*- coding: utf-8 -*-
# /converter_tools/utils.py (Error Handling Enhancements & Direct File Check with Pause)

import os
import subprocess
import shutil
import glob
import time
import tempfile

from src.converter_tools import config
import re

try:
    import send2trash
except ImportError:
    send2trash = None

ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


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
                            emit_or_print(
                                f"Could not parse FILE line in CUE: {line}", is_error=True)

    except FileNotFoundError:
        emit_or_print(
            f"ERROR: CUE file not found: {cue_file_path}", is_error=True)
        return []
    except IOError as e:
        emit_or_print(
            f"ERROR: Could not read CUE file: {cue_file_path} - {e}", is_error=True)
        return []
    except Exception as e:
        emit_or_print(
            f"ERROR: Unexpected error processing CUE file: {cue_file_path} - {e}", is_error=True)
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
            for line_content in f:
                line = line_content.strip()

                # Regex to capture essential parts, focusing on robust filename extraction.
                # Groups: 1=track_num_str, 3=filename_quoted_content, 4=filename_unquoted
                match = re.match(
                    r'^\s*(\d+)\s+\S+\s+\S+\s+\S+\s+("([^"]+)"|([^\s"]+))(?:\s+.*)?$', line)

                if match:
                    # track_num_str = match.group(1) # We don't strictly need the track number itself
                    quoted_filename_content = match.group(3)
                    unquoted_filename = match.group(4)

                    filename = ""
                    if quoted_filename_content is not None:
                        filename = quoted_filename_content
                    elif unquoted_filename is not None:
                        filename = unquoted_filename
                    else:
                        # This case should ideally not be reached if regex matches and is well-formed.
                        # Assuming no signal available here
                        emit_or_print(
                            f"Could not parse filename from GDI line: {line}", signal=None, is_error=True)
                        continue

                    # The regex groups already handle stripping the quotes.
                    # Clean any potential leading/trailing whitespace from the extracted filename.
                    filename = filename.strip()

                    if not filename:  # Skip if filename ended up empty after strip
                        emit_or_print(
                            f"Empty filename parsed from GDI line: {line}", signal=None, is_error=True)
                        continue

                    abs_path = os.path.join(gdi_dir, filename)
                    dependencies.append(os.path.normpath(abs_path))
                # Silently ignore lines that don't match the expected GDI track format
                # (e.g., the first line with track count, comments, or malformed lines)

    except FileNotFoundError:
        emit_or_print(
            f"ERROR: GDI file not found: {gdi_file_path}", signal=None, is_error=True)
        return []
    except IOError as e:
        emit_or_print(
            f"ERROR: Could not read GDI file: {gdi_file_path} - {e}", signal=None, is_error=True)
        return []
    except Exception as e:
        emit_or_print(
            f"ERROR: Unexpected error processing GDI file: {gdi_file_path} - {e}", signal=None, is_error=True)
        return []

    return dependencies


def stage_job_files(primary_file_path, job_temp_dir, is_multi_file_type, copy_locally_setting, output_signal=None, error_signal=None):
    """
    Prepares files for a job in the job_temp_dir.
    For multi-file types (CUE, GDI), it always copies the primary and dependent files.
    For other types, it copies based on copy_locally_setting.
    Returns the path to the primary file that should be processed (either in temp or original).
    """
    file_name_base_with_ext = os.path.basename(primary_file_path)
    path_to_process = primary_file_path # Default to original path

    # Ensure job_temp_dir exists (should be created by the caller, but double check)
    if not os.path.exists(job_temp_dir):
        try:
            os.makedirs(job_temp_dir)
            emit_or_print(f"INFO: Job temp directory created at: {job_temp_dir}", output_signal)
        except Exception as e:
            emit_or_print(f"ERROR: Failed to create job_temp_dir {job_temp_dir}: {e}", error_signal, is_error=True)
            return None # Cannot proceed

    # Determine dependencies
    dependencies_to_copy = []
    file_ext_lower = os.path.splitext(primary_file_path)[1].lower()

    if is_multi_file_type: # e.g. CUE or GDI
        emit_or_print(f">> Staging multi-file job for: {file_name_base_with_ext} into {job_temp_dir}", output_signal, fallback_color_code="cyan")
        if file_ext_lower == '.cue':
            dependencies_to_copy = _get_cue_dependencies(primary_file_path)
        elif file_ext_lower == '.gdi':
            dependencies_to_copy = _get_gdi_dependencies(primary_file_path)

        # Copy primary file for multi-file types
        try:
            temp_primary_path = os.path.join(job_temp_dir, file_name_base_with_ext)
            shutil.copy2(primary_file_path, temp_primary_path)
            emit_or_print(f">> Copied primary file {file_name_base_with_ext} to temp.", output_signal)
            path_to_process = temp_primary_path # Process the copy
        except Exception as e:
            emit_or_print(f"ERROR: Failed to copy primary file {file_name_base_with_ext} to temp: {e}", error_signal, is_error=True)
            return None # Cannot proceed if primary file copy fails

        # Copy dependencies for multi-file types
        for dep_path in dependencies_to_copy:
            dep_filename = os.path.basename(dep_path)
            temp_dep_dest_path = os.path.join(job_temp_dir, dep_filename)
            try:
                if not os.path.exists(dep_path):
                    emit_or_print(f"WARNING: Dependent file \"{dep_filename}\" not found at \"{dep_path}\". Skipping copy.", error_signal, fallback_color_code="yellow")
                    continue
                shutil.copy2(dep_path, temp_dep_dest_path)
                emit_or_print(f">> Copied dependent file \"{dep_filename}\" to temp.", output_signal)
            except Exception as dep_e:
                emit_or_print(f"ERROR: Failed to copy dependent file \"{dep_filename}\" to temp: {dep_e}", error_signal, is_error=True)
                # Depending on strictness, you might want to return None here

    elif copy_locally_setting: # Single file type, and copy_locally is True
        emit_or_print(f">> Copying single file job for: {file_name_base_with_ext} to {job_temp_dir}", output_signal, fallback_color_code="cyan")
        try:
            temp_primary_path = os.path.join(job_temp_dir, file_name_base_with_ext)
            if os.path.isdir(primary_file_path): # Should not happen for typical conversion jobs
                shutil.copytree(primary_file_path, temp_primary_path, dirs_exist_ok=True)
            else:
                shutil.copy2(primary_file_path, temp_primary_path)
            emit_or_print(f">> Copied {file_name_base_with_ext} to temp.", output_signal)
            path_to_process = temp_primary_path # Process the copy
        except Exception as e:
            emit_or_print(f"ERROR: Failed to copy {file_name_base_with_ext} to temp: {e}", error_signal, is_error=True)
            return None
    else: # Single file type, and copy_locally is False
        emit_or_print(f">> Processing single file job in-place (or tool handles source directly): {file_name_base_with_ext}", output_signal, fallback_color_code="cyan")
        # path_to_process remains primary_file_path

    return path_to_process


def _strip_ansi_codes(text):
    if not text:
        return ""
    try:
        return ANSI_ESCAPE_RE.sub('', text)
    except Exception:
        return text


def emit_or_print(message, signal=None, fallback_color_code=None, is_error=False, type="NONE"):
    """
    Emits a message via a Qt signal if provided, otherwise prints to console.
    Optionally formats the fallback print message with a color code.
    If is_error is True, uses a default error color if no color_code is given.
    DEBUG	Grey	Low-priority diagnostic information for developers.
    INFO	Blue (or default text color)	Neutral, informational messages about routine operations.
    SUCCESS	Green	Confirms that an operation completed successfully.
    WARN	Yellow / Amber	Highlights potential issues that are not critical errors.
    ERROR	Red	Indicates a critical failure or problem that needs immediate attention.
    """
    color_map = {
        "red": "\033[91m",
        "green": "\033[92m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "black": "\033[30m",
        "bright_red": "\033[1;91m",
        "bright_green": "\033[1;92m",
        "bright_blue": "\033[1;94m",
        "bright_yellow": "\033[1;93m",
        "bright_magenta": "\033[1;95m",
        "bright_cyan": "\033[1;96m",
        "bright_white": "\033[1;97m",
        "bold_red": "\033[1;31m",
        "italic_green": "\033[3;92m",
        "underline_blue": "\033[4;94m",
    }

    if signal:
        if callable(signal): # Check if it's a function (like our worker queue putters)
            signal(message)
        elif hasattr(signal, 'emit'): # Check if it's a Qt Signal
            signal.emit(message)
        else: # Fallback if it's neither, just print
            print(message) # Or handle as an error/warning
    else:
        color_code_to_use = None
        if fallback_color_code:
            color_code_to_use = color_map.get(
                fallback_color_code.lower(), fallback_color_code)

        if color_code_to_use:
            print(f"{color_code_to_use}{message}\033[0m")
        elif is_error or type.upper() == "ERROR":
            print(f"\033[91m{message}\033[0m")  # Default error color
        elif type.upper() == "WARN":
            print(f"\033[93m{message}\033[0m")
        elif type.upper() == "SUCCESS":
            print(f"\033[92m{message}\033[0m")
        elif type.upper() == "INFO":
            print(f"\033[96m{message}\033[0m")
        elif type.upper() == "DEBUG":
            print(f"\033[95m{message}\033[0m")
        else:
            print(f"\033[0m{message}\033[0m")  # Default color


def check_tools_exist(tools_list):
    missing_tools = [tool for tool in tools_list if not os.path.exists(tool)]
    if missing_tools:
        emit_or_print("ERROR: Missing required tools:", is_error=True)
        for tool in missing_tools:
            emit_or_print(f"- {tool}", is_error=True)
        emit_or_print(
            "Ensure 'converter_tools' folder is in the same directory and contains all executables.", is_error=True)
        emit_or_print(
            f"Expected tools directory: {config.TOOLS_DIR}", is_error=True)
        return False
    return True


def get_free_disk_space_gb(path):
    try:
        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024**3)
        return free_gb
    except AttributeError:
        emit_or_print(
            "shutil.disk_usage not available to check disk space.", is_error=True)
        return None
    except Exception as e:
        emit_or_print(
            f"Error checking disk space for {path}: {e}", is_error=True)
        return None


def run_command(command, cwd=None, output_signal=None, error_signal=None, known_error_codes=None):
    command_str = ' '.join(command)
    emit_or_print(f">> Running: {command_str}",
                   output_signal, fallback_color_code="green")

    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace'
        )
        stdout_clean = _strip_ansi_codes(result.stdout.strip())
        if stdout_clean:
            log_msg = f"--- STDOUT ---\n{stdout_clean}\n--------------"
            emit_or_print(log_msg, output_signal)

        stderr_clean = _strip_ansi_codes(result.stderr.strip())
        if stderr_clean:
            log_msg = f"--- STDERR ---\n{stderr_clean}\n--------------"
            # If command was successful (returncode 0), STDERR is treated as info.
            # Otherwise, it's part of an error.
            if result.returncode == 0:
                emit_or_print(log_msg, output_signal) # Log to normal output
            else:
                emit_or_print(log_msg, error_signal, is_error=True) # Log as error

        if result.returncode != 0:
            err_msg = f"ERROR: Command failed (code {result.returncode})"
            if known_error_codes and result.returncode in known_error_codes:
                err_msg += f": {known_error_codes[result.returncode]}"
            # The STDERR content is already logged above, so no need to repeat it in err_msg
            # unless it wasn't logged due to being empty (but then it wouldn't be in stderr_clean).
            emit_or_print(err_msg, error_signal, is_error=True)
            return False
        return True
    except FileNotFoundError:
        err_msg = f"ERROR: Command not found: {command[0]}"
        emit_or_print(err_msg, error_signal, is_error=True)
        return False
    except Exception as e:
        err_msg = f"ERROR: Unexpected error running command: {e}"
        emit_or_print(err_msg, error_signal, is_error=True)
        return False


def create_temp_dir(base_name_of_input_file, output_signal=None, error_signal=None):
    original_dir_of_input_file = os.path.dirname(base_name_of_input_file)
    file_name_part_for_prefix = os.path.splitext(
        os.path.basename(base_name_of_input_file))[0]
    temp_dir_prefix = f"{file_name_part_for_prefix}_"
    temp_dir_suffix = "_temp"

    if not config.settings.COPY_LOCALLY:
        temp_base_for_this_file = os.path.join(
            original_dir_of_input_file, "_processing_temps_")
        msg = f"Temp folder for this file will be inside: \"{temp_base_for_this_file}\" (COPY_LOCALLY=False)"
    else:
        temp_base_for_this_file = config.settings.MAIN_TEMP_DIR
        msg = f"Temp folder for this file will be inside: \"{temp_base_for_this_file}\" (COPY_LOCALLY=True)"
    emit_or_print(msg, output_signal, fallback_color_code="green")

    if not os.path.exists(temp_base_for_this_file):
        try:
            os.makedirs(temp_base_for_this_file)
            emit_or_print(
                f"Created base for temp storage: \"{temp_base_for_this_file}\"", output_signal, fallback_color_code="green")
        except OSError as e:
            emit_or_print(
                f"ERROR: Failed to create base temporary directory {temp_base_for_this_file}: {e}", error_signal, is_error=True)
            return None
    try:
        temp_dir = tempfile.mkdtemp(
            prefix=temp_dir_prefix, suffix=temp_dir_suffix, dir=temp_base_for_this_file)
        emit_or_print(
            f"Created actual temp folder: \"{temp_dir}\"", output_signal, fallback_color_code="green")
        return temp_dir
    except Exception as e:
        emit_or_print(
            f"ERROR: Failed to create temp directory in {temp_base_for_this_file}: {e}", error_signal, is_error=True)
        return None


def move_files(src_dir, dest_dir_base, pattern, output_signal=None, error_signal=None, allow_overwrite=False):
    emit_or_print(f">> Moving files matching \"{pattern}\" from \"{src_dir}\" to \"{dest_dir_base}\" (Overwrite: {allow_overwrite})",
                   output_signal, fallback_color_code="green")
    moved_any_successfully = False
    try:
        abs_src_dir = os.path.abspath(src_dir)
        files_to_move = glob.glob(os.path.join(
            abs_src_dir, '**', pattern), recursive=True)
        files_to_move = [f for f in files_to_move if os.path.isfile(f)]

        if not files_to_move:
            emit_or_print(f"WARNING: No files found matching pattern \"{pattern}\" in \"{abs_src_dir}\" or its subdirectories.",
                           error_signal, fallback_color_code="yellow")
            return False

        if not os.path.exists(dest_dir_base):
            os.makedirs(dest_dir_base)
            emit_or_print(
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
                        emit_or_print(f"WARNING: Destination \"{current_dest_file_path}\" exists. Overwriting.",
                                       error_signal, fallback_color_code="yellow")
                        try:
                            if os.path.isdir(current_dest_file_path):
                                shutil.rmtree(current_dest_file_path)
                            else:
                                os.remove(current_dest_file_path)
                        except OSError as e_rm:
                            emit_or_print(f"ERROR: Failed to remove existing destination {current_dest_file_path} for overwrite: {e_rm}. Skipping.",
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
                                emit_or_print(
                                    f"INFO: Renaming output to: \"{current_dest_file_path}\"", output_signal, fallback_color_code="cyan")
                                break
                            count += 1
                            if count > 999:
                                emit_or_print(f"ERROR: Could not find an available sequentially numbered name for \"{initial_dest_file_path}\" after 999 attempts. Skipping.",
                                               error_signal, is_error=True)
                                continue

                shutil.move(file_path, current_dest_file_path)
                emit_or_print(f"Moved \"{os.path.basename(file_path)}\" to \"{current_dest_file_path}\"",
                               output_signal, fallback_color_code="green")
                moved_any_successfully = True
            except Exception as e_move:
                emit_or_print(f"ERROR: Failed to move \"{os.path.basename(file_path)}\" to \"{current_dest_file_path}\": {e_move}",
                               error_signal, is_error=True)
        return moved_any_successfully
    except Exception as e_prep:
        emit_or_print(
            f"ERROR: Preparing to move files: {e_prep}", error_signal, is_error=True)
        return False


def cleanup(temp_path, output_signal=None, error_signal=None): # Removed original_file_path
    if temp_path and os.path.exists(temp_path):
        retries = 3
        while retries > 0:
            try:
                shutil.rmtree(temp_path)
                emit_or_print(
                    f"Removed temporary directory: \"{temp_path}\"", output_signal)
                break
            except OSError as e:
                retries -= 1
                err_msg = f"Failed to remove temp directory {temp_path}: {e}"
                if retries == 0:
                    emit_or_print(
                        f"ERROR: {err_msg} after multiple attempts.", error_signal, is_error=True)
                else:
                    emit_or_print(
                        f"WARNING: {err_msg}, retrying...", error_signal, fallback_color_code="yellow")
                    time.sleep(0.5)
            except Exception as e_unexpected_rm:
                emit_or_print(
                    f"ERROR: Unexpected error removing temp dir {temp_path}: {e_unexpected_rm}", error_signal, is_error=True)
                break # Break from retries on unexpected error

            # After successfully removing job-specific temp_path, check its parent
            if not config.settings.COPY_LOCALLY: # This logic only applies if not using MAIN_TEMP_DIR
                parent_dir = os.path.dirname(temp_path)
                if os.path.basename(parent_dir) == "_processing_temps_":
                    try:
                        dir_contents = os.listdir(parent_dir)
                        if not dir_contents: # Check if empty
                            emit_or_print(f"INFO: Attempting to remove empty parent temp directory: \"{parent_dir}\"", output_signal)
                            os.rmdir(parent_dir)
                            emit_or_print(f"INFO: Successfully removed empty parent temp directory: \"{parent_dir}\"", output_signal)
                        else:
                            emit_or_print(f"DEBUG: Parent temp dir \"{parent_dir}\" not empty. Contents: {dir_contents}. Not removing.", output_signal)
                    except OSError as e:
                        emit_or_print(f"WARNING: Could not remove parent temp directory \"{parent_dir}\". Error: {e.strerror} (Code: {e.errno}). Path: {e.filename}", error_signal, fallback_color_code="yellow")
                    except Exception as e_parent_rm:
                        emit_or_print(f"ERROR: Unexpected error removing parent temp dir \"{parent_dir}\": {e_parent_rm}", error_signal, is_error=True)
                else:
                    emit_or_print(f"DEBUG: Parent of job temp dir ('{parent_dir}') is not named '_processing_temps_'. Skipping its removal.", output_signal)
            break # Break from retries as shutil.rmtree was successful or an unexpected error occurred

    # Original file deletion logic is now handled in process_worker_task


def check_tools_exist(tools_list: list[str]) -> bool:
    """
    Checks if all specified command-line tools are accessible.
    If a tool is given as an absolute path, its existence is checked.
    If a tool is given as a name, shutil.which is used to find it in PATH.
    Prints messages for missing tools.
    Returns True if all tools are found/accessible, False otherwise.
    """
    all_found = True
    if not isinstance(tools_list, list):
        print("Error: tools_list is not a list. Cannot check for tools.",
              file=sys.stderr)
        return False

    print("\nChecking for essential tools:")
    for tool_specifier in tools_list:
        tool_display_name = os.path.basename(tool_specifier)  # For display
        found_this_tool = False
        location_info = ""

        if os.path.isabs(tool_specifier):
            if os.path.exists(tool_specifier):
                # For files, also check if it's executable, though os.access might be tricky cross-platform esp. on Windows
                # For now, os.path.exists for full paths is the main check from config.
                if os.path.isfile(tool_specifier):  # Ensure it's a file
                    found_this_tool = True
                    location_info = f"(at specified path: {tool_specifier})"
                else:
                    location_info = f"(specified path {tool_specifier} is not a file)"
            else:
                location_info = f"(specified path {tool_specifier} not found)"
        else:  # It's a name, try to find it in PATH
            which_result = shutil.which(tool_specifier)
            if which_result:
                found_this_tool = True
                location_info = f"(in PATH at: {which_result})"
            else:
                location_info = "(not found in PATH)"

        if found_this_tool:
            print(f"  [FOUND] {tool_display_name} {location_info}")
        else:
            print(f"  [MISSING] {tool_display_name} {location_info}")
            all_found = False

    if all_found:
        print("All essential tools verified.")
    else:
        print("\nWarning: Some essential tools are missing or not configured correctly. Application functionality may be limited.")
    return all_found


def extract_archive(archive_path, output_dir, output_signal=None, error_signal=None):
    emit_or_print(f">> Extracting: \"{os.path.basename(archive_path)}\" to \"{output_dir}\"",
                   output_signal, fallback_color_code="green")
    command = [config.TOOL_7ZA, 'x', archive_path, f'-o{output_dir}', '-y']
    return run_command(command, output_signal=output_signal, error_signal=error_signal)


def process_file(staged_primary_file_path, job_temp_dir, original_file_path_for_naming_and_delete, conversion_func, format_out, format_out2=None,
                 output_signal=None, error_signal=None, explicit_output_dir=None, allow_overwrite=False,
                 target_format_from_worker=None, stage_reporter=None, file_progress_reporter=None):
    # original_dir_of_input_file = os.path.dirname(staged_primary_file_path) # This is now job_temp_dir
    file_name_base_with_ext = os.path.basename(staged_primary_file_path) # Name of the file in temp (should match original)
    name_part, _ = os.path.splitext(file_name_base_with_ext) # Use this for output naming

    # Determine final output destination
    # If explicit_output_dir is provided (e.g. user selected custom output folder), use it.
    # Otherwise, output to the same directory as the original input file.
    original_input_dir_for_output = os.path.dirname(original_file_path_for_naming_and_delete)
    final_output_destination_base = explicit_output_dir if explicit_output_dir else original_input_dir_for_output

    if not os.path.exists(final_output_destination_base):
        try:
            os.makedirs(final_output_destination_base)
            emit_or_print(f"INFO: Created final output directory {final_output_destination_base}", output_signal)
        except OSError as e:
            emit_or_print(f"ERROR: Failed to create final output dir {final_output_destination_base}: {e}.", error_signal, is_error=True)
            return False

    # The "Preparing" stage, including file copying, is now done by stage_job_files before this function is called.
    # So, staged_primary_file_path is the path to the file (potentially inside job_temp_dir) that the tool should process.
    # job_temp_dir is where the conversion tool should write its raw output.

    if stage_reporter:
        stage_reporter("Converting") # Report current stage
    if file_progress_reporter:
        file_progress_reporter(33)  # Conversion starting
    conversion_args = {
        "processing_path": staged_primary_file_path, # This is the path to the primary file, possibly in job_temp_dir
        "temp_dir": job_temp_dir,                   # This is where the tool should write its direct output
        "name": name_part,                          # Base name for output files
        "output_signal": output_signal,
        "error_signal": error_signal
    }
    if target_format_from_worker and hasattr(conversion_func, '__code__') and 'target_format_from_worker' in conversion_func.__code__.co_varnames:
        conversion_args["target_format_from_worker"] = target_format_from_worker
    conversion_successful = conversion_func(**conversion_args)

    # Debugging pause can be re-enabled if needed by uncommenting here
    # ...

    if stage_reporter:
        stage_reporter("Finalizing")
    if file_progress_reporter:
        file_progress_reporter(66)  # Finalizing stage

    if conversion_successful:
        primary_move_ok = False
        # Determine effective output format (used by tool)
        effective_format_out = target_format_from_worker if target_format_from_worker and \
            hasattr(conversion_func, '__code__') and \
            'target_format_from_worker' in conversion_func.__code__.co_varnames else format_out

        if effective_format_out: # If there's a primary output file expected
            expected_primary_output_filename = f"{name_part}.{effective_format_out}"
            # The conversion tool writes its output directly into job_temp_dir
            expected_primary_output_full_path_in_job_temp = os.path.join(
                job_temp_dir, expected_primary_output_filename)

            # Check if the expected primary output exists in job_temp_dir
            if os.path.isfile(expected_primary_output_full_path_in_job_temp):
                emit_or_print(f"DEBUG_UTIL: Located expected primary output: {expected_primary_output_full_path_in_job_temp}", output_signal)
                # Move the primary output file
                if move_files(job_temp_dir, final_output_destination_base, expected_primary_output_filename,
                              output_signal, error_signal, allow_overwrite):
                    primary_move_ok = True
                else:
                    emit_or_print(f"ERROR: Primary output ('{expected_primary_output_filename}') for \"{original_file_path_for_naming_and_delete}\" was not moved.",
                                   error_signal, is_error=True)
            else:
                emit_or_print(f"ERROR: Expected primary output ('{expected_primary_output_filename}') not found in job temp dir '{job_temp_dir}' for input \"{original_file_path_for_naming_and_delete}\".",
                               error_signal, is_error=True)
                all_files_in_temp_root = glob.glob(os.path.join(job_temp_dir, "*"))
                emit_or_print(f"DEBUG_UTIL: Contents of job temp root '{job_temp_dir}': {all_files_in_temp_root}", output_signal)


            # Handle secondary files (e.g., .bin for .cue, .raw for .gdi) if primary moved ok
            if primary_move_ok and format_out2: # format_out2 might indicate other general patterns
                if not move_files(job_temp_dir, final_output_destination_base, f"*.{format_out2}",
                                  output_signal, error_signal, allow_overwrite):
                    emit_or_print(f"WARNING: Secondary output (*.{format_out2}) move failed or files skipped for \"{original_file_path_for_naming_and_delete}\".",
                                   error_signal, fallback_color_code="yellow")

            # Specific handling for GDI/CUE dependent files that are part of the output set
            # These are usually created alongside the primary .gdi/.cue in the job_temp_dir by chdman extract
            if primary_move_ok:
                if effective_format_out == 'gdi':
                    move_files(job_temp_dir, final_output_destination_base, "*.bin", output_signal, error_signal, allow_overwrite)
                    move_files(job_temp_dir, final_output_destination_base, "*.raw", output_signal, error_signal, allow_overwrite)
                elif effective_format_out == 'cue': # For CHD to CUE extraction
                    # Move all .bin files that were created by chdman extractcd
                    # Pattern should be specific enough if name_part is used, e.g., f"{name_part}*.bin"
                    # For simplicity, moving all .bin files from temp if not already moved.
                    # This assumes chdman extractcd -o temp/mygame.cue produces temp/mygame.cue and temp/mygame_track01.bin etc.
                    move_files(job_temp_dir, final_output_destination_base, f"{name_part}*.bin", output_signal, error_signal, allow_overwrite)
                    move_files(job_temp_dir, final_output_destination_base, f"{name_part}*.wav", output_signal, error_signal, allow_overwrite) # If any audio tracks

        else: # No specific primary output file (e.g., extract_archive_to_folder_routine, or info jobs)
            if conversion_func.__name__ == "extract_archive_to_folder_routine":
                # Output is an entire folder, named after the archive.
                archive_output_folder_name = name_part # Folder name is base name of archive
                # All contents of job_temp_dir (which should be the extracted files) are moved.
                # The destination is a new sub-folder in final_output_destination_base.
                final_archive_extract_path = os.path.join(final_output_destination_base, archive_output_folder_name)

                if os.path.exists(final_archive_extract_path):
                    if allow_overwrite:
                        emit_or_print(f"INFO: Overwriting existing extraction folder: {final_archive_extract_path}", output_signal)
                        shutil.rmtree(final_archive_extract_path)
                    else:
                        emit_or_print(f"ERROR: Extraction folder {final_archive_extract_path} already exists and overwrite is false.", error_signal, is_error=True)
                        primary_move_ok = False # Set to false as we can't proceed

                if primary_move_ok is not False: # Check if not already failed
                    try:
                        shutil.copytree(job_temp_dir, final_archive_extract_path, dirs_exist_ok=allow_overwrite)
                        emit_or_print(f"Extracted archive contents moved to {final_archive_extract_path}", output_signal)
                        primary_move_ok = True
                    except Exception as e_extract_move:
                        emit_or_print(f"ERROR moving extracted archive contents from {job_temp_dir} to {final_archive_extract_path}: {e_extract_move}", error_signal, is_error=True)
                        primary_move_ok = False
            elif "info_routine" in conversion_func.__name__ or "verify_routine" in conversion_func.__name__:
                # These routines typically print to console/log; no files to move.
                emit_or_print(f"Info/Verify job for {original_file_path_for_naming_and_delete} completed.", output_signal)
                primary_move_ok = True # Considered successful if the function itself reported success
            else: # Some other conversion type that doesn't fit known patterns
                emit_or_print(f"WARNING: Conversion for {original_file_path_for_naming_and_delete} reported success, but no specific output file handling defined.", error_signal, fallback_color_code="yellow")
                primary_move_ok = True # Assume success if conversion_func returned true

        if primary_move_ok:
            if file_progress_reporter:
                file_progress_reporter(100)  # Complete
            # Cleanup the job_temp_dir.
            cleanup(job_temp_dir, output_signal=output_signal, error_signal=error_signal)
            return True
        else: # primary_move_ok is False
            cleanup(job_temp_dir, output_signal=output_signal, error_signal=error_signal)
            return False
    else: # conversion_successful is False
        cleanup(job_temp_dir, output_signal=output_signal, error_signal=error_signal)
        return False


def process_input(input_path, conversion_func, formats_in, format_out, format_out2=None):
    pass


def print_help(formats_in, format_out, format_out2=None):
    emit_or_print(
        "CLI Help Text Placeholder - Retain your original help text here.", fallback_color_code="cyan")
    pass


def clean_filename_for_playlist(filename: str) -> str:
    if not filename:
        return "playlist"  # Default if input is empty

    name = str(filename)  # Ensure it's a string

    # Patterns from M3UCreatorWindow._temporary_clean_filename
    patterns = [
        r'\s*\(Disc\s*\d+(?:\s*of\s*\d+)?\)\s*', r'\s*\(CD\s*\d*(?:\s*of\s*\d+)?\)\s*',
        # Square brackets and content
        r'\s*\(Disk\s*\d+(?:\s*of\s*\d+)?\)\s*', r'\s*\[.*?\]\s*',
        r'\s*\(.*Version.*\)\s*', r'\s*\(Beta\)\s*', r'\s*\(Proto\)\s*',
        r'\s*\((?:USA|US|Europe|EU|Japan|JP|World)\)\s*',  # Region tags
        # Common language tags
        r'\s*\((?:En|Fr|De|Es|It|Nl|Pt|Sv|No|Da|Fi)\)\s*',
        # Revision/Alt tags
        r'\s*\(Rev\s*[\w\.]+\)\s*', r'\s*\(Alternative?\)\s*', r'\s*\(Alt\)\s*',
        r'\s*\(Unl(?:icensed)?\)\s*',  # Unlicensed
        r'\s*\(Track\s*\d+\)\s*', r'\s*\(Bonus Disc\)\s*', r'\s*\(Game\s*\d*\)\s*',
        r'\s*\(Side\s*[AB12]\)\s*',
        r'\(Demo\)\s*', r'\(Sample\)\s*', r'\(Promo\)\s*',
        r'\(Enhanced\)\s*', r'\(Remastered\)\s*', r'\(Limited Edition\)\s*',
        r'\(Collector\'s Edition\)\s*',
        # Specific example from issue
        r'\s*\(\s*CD\s*\d+\s*of\s*\d+\s*\)\s*',
        r'\s*\(\s*Disc\s*\d+\s*of\s*\d+\s*\)\s*',
    ]
    for pattern in patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # Remove any leading/trailing spaces, underscores, hyphens
    name = name.strip(' _-')
    # Replace multiple spaces or underscores with a single space
    name = re.sub(r'[\s_]+', ' ', name)
    # Normalize spacing around hyphens (e.g., "name - subtitle" to "name-subtitle" if desired, or keep space)
    # For now, just ensure single space around them if they are meant to be word separators
    # Ensures space around hyphen if present
    name = re.sub(r'\s*-\s*', ' - ', name)
    name = name.strip()  # Final strip

    # If after all cleaning the name is empty, return a default
    return name if name else "playlist"


def set_folder_hidden_attribute(folder_path: str):
    """
    Sets the hidden attribute for a folder.
    On Windows, uses ctypes to call SetFileAttributesW.
    On Unix-like systems (Linux, macOS), prepends a '.' to the folder name if not already present.
    Note: Renaming on Unix might fail if the target name exists or due to permissions.
    """
    if not os.path.isdir(folder_path):
        # Or raise ValueError("Folder does not exist or is not a directory.")
        print(
            f"Warning: Folder '{folder_path}' not found or is not a directory. Cannot set hidden attribute.", file=sys.stderr)
        return False

    system_platform = sys.platform.lower()

    try:
        if system_platform.startswith("win"):  # Windows
            FILE_ATTRIBUTE_HIDDEN = 0x02
            # Ensure path is unicode for ctypes
            ret = ctypes.windll.kernel32.SetFileAttributesW(
                str(folder_path), FILE_ATTRIBUTE_HIDDEN)
            if not ret:  # SetFileAttributes returns 0 on failure
                # You might want to raise an exception here or get last error
                # For now, just print error from ctypes.WinError()
                error_code = ctypes.get_last_error()
                ctypes_error = ctypes.WinError(error_code)
                print(
                    f"Error setting hidden attribute on '{folder_path}': {ctypes_error} (Code: {error_code})", file=sys.stderr)
                return False
            return True

        # Linux or macOS
        elif system_platform.startswith("linux") or system_platform.startswith("darwin"):
            folder_basename = os.path.basename(folder_path)
            folder_dirname = os.path.dirname(folder_path)

            if not folder_basename.startswith("."):
                new_hidden_name = "." + folder_basename
                new_full_path = os.path.join(folder_dirname, new_hidden_name)

                if os.path.exists(new_full_path):
                    print(f"Warning: Cannot make '{folder_path}' hidden by renaming. "
                          f"Target '{new_full_path}' already exists.", file=sys.stderr)
                    return False  # Or True if it's already hidden effectively by existing dot folder

                # shutil.move can rename directories
                shutil.move(folder_path, new_full_path)
                print(
                    f"Info: Folder '{folder_path}' renamed to '{new_full_path}' to make it hidden.")
                # Important: The calling code needs to be aware that folder_path has changed if this succeeds.
                # This function should ideally return the new path if it changes.
                # However, the plan was just to set it hidden.
                # For now, this function's contract is just to try and hide it.
                # The caller (M3UCreatorWindow) already has the new_folder_path which would be the dot-prefixed one
                # if the playlist name itself started with a dot.
                # This function is called AFTER the folder is created with its final name.
                # So, if the final name was ".myplaylist", this function on Unix would do nothing.
                # If the final name was "myplaylist", this renames it to ".myplaylist".
            else:
                # Folder already starts with a dot, considered hidden by convention
                print(
                    f"Info: Folder '{folder_path}' already starts with '.', considered hidden on Unix-like systems.")
            return True

        else:
            print(
                f"Unsupported platform: {system_platform}. Cannot set hidden attribute.", file=sys.stderr)
            return False

    except Exception as e:
        print(
            f"Exception while trying to set hidden attribute on '{folder_path}': {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Test out different color prints
    emit_or_print("##  --INITIATING COLOR TEST--  ##")
    emit_or_print("DEBUG: TEST DEBUG", type="DEBUG")
    emit_or_print("INFO: TEST DEBUG", type="INFO")
    emit_or_print("SUCCESS: TEST DEBUG", type="SUCCESS")
    emit_or_print("WARN: TEST DEBUG", type="WARN")
    emit_or_print("ERROR: TEST DEBUG", type="ERROR")
    emit_or_print("ERROR: TEST DEBUG", is_error=True)
    emit_or_print("No type")
    emit_or_print("##  --ENDING COLOR TEST--  ##")
