import os
import subprocess
import shutil
import glob
import time
import tempfile
import sys
import ctypes # For Windows hidden attribute
import logging
# import config # Changed to relative import
from . import config
import re
import logging
import os # os is used for makedirs, ensure it's noted

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

    if APP_LOGGER and hasattr(config, 'settings') and config.settings.DEBUG_MODE:
        # Ensure APP_LOGGER is not None and DEBUG_MODE is on
        # The strip_ansi_codes function is assumed to be available in this file.
        log_message = strip_ansi_codes(message)
        if is_error:
            APP_LOGGER.error(log_message)
        else:
            APP_LOGGER.info(log_message)


def strip_ansi_codes(text):
    if not text:
        return ""
    try:
        return ANSI_ESCAPE_RE.sub('', text)
    except Exception:
        return text


# --- Logging Setup ---
def setup_logging():
    """
    Sets up logging if DEBUG_MODE is True.
    Creates a log file in LOG_DIRECTORY with a timestamp.
    """
    if not hasattr(config, 'settings') or not config.settings.DEBUG_MODE:
        return None

    try:
        log_dir_path = config.settings.LOG_DIRECTORY
        os.makedirs(log_dir_path, exist_ok=True)

        log_filename = f"app_debug_{time.strftime('%Y%m%d_%H%M%S')}.log"
        log_filepath = os.path.join(log_dir_path, log_filename)

        logger = logging.getLogger("app_debug")

        if logger.level == logging.NOTSET:
             logger.setLevel(logging.DEBUG)

        if not logger.handlers:
            fh = logging.FileHandler(log_filepath, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        return logger
    except Exception as e:
        print(f"CRITICAL - Error setting up logging: {e}", flush=True)
        return None

APP_LOGGER = setup_logging()

if APP_LOGGER:
    APP_LOGGER.info("Logging initialized for app_debug.")
# --- End Logging Setup ---


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

def clean_filename_for_playlist(filename: str) -> str:
    if not filename:
        return "playlist" # Default if input is empty

    name = str(filename) # Ensure it's a string

    # Patterns from M3UCreatorWindow._temporary_clean_filename
    patterns = [
        r'\s*\(Disc\s*\d+(?:\s*of\s*\d+)?\)\s*', r'\s*\(CD\s*\d*(?:\s*of\s*\d+)?\)\s*',
        r'\s*\(Disk\s*\d+(?:\s*of\s*\d+)?\)\s*', r'\s*\[.*?\]\s*', # Square brackets and content
        r'\s*\(.*Version.*\)\s*', r'\s*\(Beta\)\s*', r'\s*\(Proto\)\s*',
        r'\s*\((?:USA|US|Europe|EU|Japan|JP|World)\)\s*', # Region tags
        r'\s*\((?:En|Fr|De|Es|It|Nl|Pt|Sv|No|Da|Fi)\)\s*', # Common language tags
        r'\s*\(Rev\s*[\w\.]+\)\s*', r'\s*\(Alternative?\)\s*', r'\s*\(Alt\)\s*', # Revision/Alt tags
        r'\s*\(Unl(?:icensed)?\)\s*', # Unlicensed
        r'\s*\(Track\s*\d+\)\s*', r'\s*\(Bonus Disc\)\s*', r'\s*\(Game\s*\d*\)\s*',
        r'\s*\(Side\s*[AB12]\)\s*',
        r'\(Demo\)\s*', r'\(Sample\)\s*', r'\(Promo\)\s*',
        r'\(Enhanced\)\s*', r'\(Remastered\)\s*', r'\(Limited Edition\)\s*',
        r'\(Collector's Edition\)\s*',
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
    name = re.sub(r'\s*-\s*', ' - ', name) # Ensures space around hyphen if present
    name = name.strip() # Final strip

    # If after all cleaning the name is empty, return a default
    return name if name else "playlist"


def run_command(command, cwd=None, output_signal=None, error_signal=None, known_error_codes=None):
    if APP_LOGGER and hasattr(config, 'settings') and config.settings.DEBUG_MODE:
        APP_LOGGER.debug(f"Executing command: {' '.join(command)}")
        if cwd:
            APP_LOGGER.debug(f"Working directory: {cwd}")

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
            if APP_LOGGER and hasattr(config, 'settings') and config.settings.DEBUG_MODE:
                APP_LOGGER.debug(f"Command stdout: {stdout_clean}")

        stderr_clean = strip_ansi_codes(result.stderr.strip())
        if stderr_clean:
            log_msg = f"--- STDERR ---\n{stderr_clean}\n--------------"
            _emit_or_print(log_msg, error_signal, is_error=True)
            if APP_LOGGER and hasattr(config, 'settings') and config.settings.DEBUG_MODE:
                APP_LOGGER.warning(f"Command stderr: {stderr_clean}") # Use warning for stderr

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
        if APP_LOGGER and hasattr(config, 'settings') and config.settings.DEBUG_MODE:
            APP_LOGGER.error(f"Command not found: {command[0]}", exc_info=True)
        _emit_or_print(err_msg, error_signal, is_error=True)
        return False
    except Exception as e:
        err_msg = f"ERROR: Unexpected error running command: {e}"
        if APP_LOGGER and hasattr(config, 'settings') and config.settings.DEBUG_MODE:
            APP_LOGGER.error(f"Unexpected error running command {' '.join(command)}: {e}", exc_info=True)
        _emit_or_print(err_msg, error_signal, is_error=True)
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
        if hasattr(config, 'settings') and config.settings.DEBUG_MODE:
            prompt_message = f"DEBUG MODE: Temporary folder '{temp_path}' is about to be cleaned up. Continue with cleanup?"
            if APP_LOGGER:
                APP_LOGGER.info(prompt_message)

            # Use _emit_or_print for visibility in GUI log, then input for actual choice
            _emit_or_print(prompt_message, output_signal, fallback_color_code="yellow")
            try:
                user_choice = input(f"{prompt_message} (yes/no): ").strip().lower()
            except RuntimeError: # Happens if sys.stdin is not available (e.g. some GUI contexts)
                _emit_or_print("WARNING: Cannot read user input for debug cleanup prompt in this context. Defaulting to NO cleanup.", error_signal, fallback_color_code="yellow")
                user_choice = "no" # Default to not cleaning up if input is not possible

            if user_choice not in ['yes', 'y']:
                if APP_LOGGER:
                    APP_LOGGER.info(f"User chose NOT to cleanup temp folder: {temp_path}")
                _emit_or_print(f"Skipping cleanup of temporary folder: {temp_path}", output_signal, fallback_color_code="yellow")
                # Skip temp path removal, but continue to source file deletion logic
            else:
                # User chose 'yes', proceed with temp folder cleanup
                if APP_LOGGER:
                    APP_LOGGER.info(f"User chose to cleanup temp folder: {temp_path}")
                _emit_or_print(f"Proceeding with cleanup of temporary folder: {temp_path}", output_signal, fallback_color_code="green")
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
        else: # Not DEBUG_MODE, proceed with normal cleanup
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

    if config.settings.DELETE_SOURCE_ON_SUCCESS and original_file_path and os.path.exists(original_file_path):
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
    if config.settings.COPY_LOCALLY:
        _emit_or_print(f">> Copying \"{file_name_base_with_ext}\" to \"{temp_path_for_this_file}\"",
                       output_signal, fallback_color_code="green")
        try:
            target_copy_path = os.path.join(
                temp_path_for_this_file, file_name_base_with_ext)
            if os.path.isdir(file_path):
                shutil.copytree(file_path, target_copy_path,
                                dirs_exist_ok=True)
            else:
                # Folder already starts with a dot, considered hidden by convention
                print(f"Info: Folder '{folder_path}' already starts with '.', considered hidden on Unix-like systems.")
            return True

        else:
            print(f"Unsupported platform: {system_platform}. Cannot set hidden attribute.", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Exception while trying to set hidden attribute on '{folder_path}': {e}", file=sys.stderr)
        return False

def set_folder_hidden_attribute(folder_path: str):
    """
    Sets the hidden attribute for a folder.
    On Windows, uses ctypes to call SetFileAttributesW.
    On Unix-like systems (Linux, macOS), prepends a '.' to the folder name if not already present.
    Note: Renaming on Unix might fail if the target name exists or due to permissions.
    """
    if not os.path.isdir(folder_path):
        # Or raise ValueError("Folder does not exist or is not a directory.")
        print(f"Warning: Folder '{folder_path}' not found or is not a directory. Cannot set hidden attribute.", file=sys.stderr)
        return False

    system_platform = sys.platform.lower()

    try:
        if system_platform.startswith("win"): # Windows
            FILE_ATTRIBUTE_HIDDEN = 0x02
            # Ensure path is unicode for ctypes
            ret = ctypes.windll.kernel32.SetFileAttributesW(str(folder_path), FILE_ATTRIBUTE_HIDDEN)
            if not ret: # SetFileAttributes returns 0 on failure
                # You might want to raise an exception here or get last error
                # For now, just print error from ctypes.WinError()
                error_code = ctypes.get_last_error()
                ctypes_error = ctypes.WinError(error_code)
                print(f"Error setting hidden attribute on '{folder_path}': {ctypes_error} (Code: {error_code})", file=sys.stderr)
                return False
            return True

        elif system_platform.startswith("linux") or system_platform.startswith("darwin"): # Linux or macOS
            folder_basename = os.path.basename(folder_path)
            folder_dirname = os.path.dirname(folder_path)

            if not folder_basename.startswith("."):
                new_hidden_name = "." + folder_basename
                new_full_path = os.path.join(folder_dirname, new_hidden_name)

                if os.path.exists(new_full_path):
                    print(f"Warning: Cannot make '{folder_path}' hidden by renaming. "
                          f"Target '{new_full_path}' already exists.", file=sys.stderr)
                    return False # Or True if it's already hidden effectively by existing dot folder

                shutil.move(folder_path, new_full_path) # shutil.move can rename directories
                print(f"Info: Folder '{folder_path}' renamed to '{new_full_path}' to make it hidden.")
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
                print(f"Info: Folder '{folder_path}' already starts with '.', considered hidden on Unix-like systems.")
            return True

        else:
            print(f"Unsupported platform: {system_platform}. Cannot set hidden attribute.", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Exception while trying to set hidden attribute on '{folder_path}': {e}", file=sys.stderr)
        return False
    
# Example of how to get free disk space (already in gui_main_window.py, but good for utils.py)
def get_free_disk_space_gb(folder_path: str) -> float | None:
    """Returns free disk space in GB for the drive containing folder_path."""
    try:
        stat = os.statvfs(os.path.abspath(folder_path))
        # Calculate free space in GB
        # stat.f_frsize is fundamental file system block size
        # stat.f_bavail is free blocks available to non-superuser
        free_gb = (stat.f_frsize * stat.f_bavail) / (1024 * 1024 * 1024)
        return free_gb
    except AttributeError: # os.statvfs not available on all platforms (e.g. Windows)
        if sys.platform.startswith("win"):
            try:
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(folder_path),
                    ctypes.byref(free_bytes),
                    ctypes.byref(total_bytes),
                    None) # Third param (total_free_bytes) can be None
                return free_bytes.value / (1024 * 1024 * 1024)
            except Exception:
                return None # Failed to get free space on Windows
        return None # Not Windows and no statvfs
    except Exception:
        return None # Other errors

if __name__ == '__main__':
    # Test clean_filename_for_playlist
    test_names = [
        "My Game (Disc 1 of 2) [USA]",
        "Another Game (CD2)",
        "Game Name (Europe) (Rev A) (Track 01)",
        "Test [Proto] (Unknown Version)",
        "  leading and trailing spaces  ",
        "Game_With_Underscores",
        "Empty () [] Test",
        "",
        "My Awesome Game (Demo) (Limited Edition) (Enhanced)",
        "Final Game (Side A)",
        "Game (CD 1 of 4)",
    ]
    for tn in test_names:
        print(f"Original: '{tn}' -> Cleaned: '{clean_filename_for_playlist(tn)}'")

    # Test set_folder_hidden_attribute (manual testing needed for actual effect)
    # Create dummy folders for testing
    test_folder_plain = "test_visible_folder"
    test_folder_dot = ".test_hidden_folder_unix"
    test_folder_win = "test_hidden_folder_win"

    for tf in [test_folder_plain, test_folder_dot, test_folder_win]:
        if os.path.exists(tf):
            if os.path.isdir(tf): shutil.rmtree(tf) # Remove if it's a dir
            else: os.remove(tf) # Remove if it's a file

    os.makedirs(test_folder_plain, exist_ok=True)
    os.makedirs(test_folder_dot, exist_ok=True)
    os.makedirs(test_folder_win, exist_ok=True)

    print(f"\nAttempting to hide '{test_folder_plain}':")
    set_folder_hidden_attribute(test_folder_plain) # On Unix, this should become ".test_visible_folder"

    print(f"Attempting to hide '{test_folder_dot}' (already dot-prefixed for Unix):")
    set_folder_hidden_attribute(test_folder_dot)

    print(f"Attempting to hide '{test_folder_win}' (Windows specific):")
    set_folder_hidden_attribute(test_folder_win) # This will use ctypes on Windows

    # Note: actual verification of hidden status needs manual check or platform-specific commands
    print("\nManual verification needed for hidden status of test folders.")
    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        if os.path.exists(os.path.join(os.path.dirname(test_folder_plain), "." + os.path.basename(test_folder_plain))):
            print(f"'{test_folder_plain}' likely renamed to '.{os.path.basename(test_folder_plain)}'")

    # Clean up test folders
    # for tf in [test_folder_plain, test_folder_dot, test_folder_win, ".test_visible_folder"]: # Also remove renamed one
    #     if os.path.exists(tf) and os.path.isdir(tf):
    #         try:
    #             # On Windows, hidden files might need attribute change before rmtree
    #             if sys.platform.startswith("win") and os.path.basename(tf) == test_folder_win:
    #                 # Attempt to unhide before deleting if it was hidden
    #                 ctypes.windll.kernel32.SetFileAttributesW(str(tf), 0x80) # FILE_ATTRIBUTE_NORMAL
    #             shutil.rmtree(tf)
    #         except Exception as e_clean:
    #             print(f"Error cleaning up test folder {tf}: {e_clean}")
