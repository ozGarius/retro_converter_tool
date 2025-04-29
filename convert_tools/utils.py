# -*- coding: utf-8 -*-
# /convert_tools/utils.py (Refactored for GUI Logging)

import os
import subprocess
import shutil
import glob
import time
import tempfile # Use tempfile for unique directories
import config # Import settings from config.py
import re # For stripping ANSI codes

# ANSI escape code regex
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi_codes(text):
    """Removes ANSI escape codes from a string."""
    if not text:
        return ""
    try:
        return ANSI_ESCAPE_RE.sub('', text)
    except Exception: # Catch potential errors during regex processing
        return text # Return original text if stripping fails

# --- TOOL & SYSTEM UTILITIES ---

def check_tools_exist(tools_list):
    """Checks if the required external tools exist."""
    # This function still prints directly as it runs before GUI/Worker starts
    missing_tools = [tool for tool in tools_list if not os.path.exists(tool)]
    if missing_tools:
        print(f"\033[91mERROR: Missing required tools:\033[0m")
        for tool in missing_tools:
            print(f"- {tool}")
        print(f"\033[91mPlease ensure the 'convert_tools' folder is in the same directory as the script and contains all necessary executables.\033[0m")
        print(f"\033[91mExpected tools directory: {config.TOOLS_DIR}\033[0m")
        return False
    return True

def run_command(command, cwd=None, output_signal=None, error_signal=None):
    """
    Runs an external command, captures its output, emits output/errors via signals,
    and returns True on success, False on failure.
    """
    command_str = ' '.join(command)
    # Emit the command being run
    if output_signal:
        output_signal.emit(f">> Running: {command_str}")
    else: # Fallback for CLI or non-GUI use
        print(f"\033[91m>>\033[32m Running command: {command_str}\033[0m")

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False, # Don't raise exception on non-zero exit
            encoding='utf-8',
            errors='replace' # Replace undecodable characters
        )

        # Emit stdout if captured and signal exists
        stdout_clean = strip_ansi_codes(result.stdout.strip())
        if stdout_clean and output_signal:
            output_signal.emit(f"--- STDOUT ---\n{stdout_clean}\n--------------")
        elif stdout_clean: # Fallback print
             print("--- STDOUT ---")
             print(stdout_clean)
             print("--------------")


        # Emit stderr if captured and signal exists
        stderr_clean = strip_ansi_codes(result.stderr.strip())
        if stderr_clean and error_signal:
            error_signal.emit(f"--- STDERR ---\n{stderr_clean}\n--------------")
        elif stderr_clean: # Fallback print
             print("--- STDERR ---")
             print(stderr_clean)
             print("--------------")


        # Check return code for success/failure
        if result.returncode != 0:
            err_msg = f"ERROR: Command failed with return code {result.returncode}"
            if error_signal:
                error_signal.emit(err_msg)
            else:
                print(f"\033[91m{err_msg}\033[0m")
            return False
        return True # Command succeeded

    except FileNotFoundError:
        err_msg = f"ERROR: Command not found. Make sure the executable is in the correct path:\n{command[0]}"
        if error_signal:
            error_signal.emit(err_msg)
        else:
            print(f"\033[91m{err_msg}\033[0m")
        return False
    except Exception as e:
        err_msg = f"ERROR: An unexpected error occurred while running command: {e}"
        if error_signal:
            error_signal.emit(err_msg)
        else:
            print(f"\033[91m{err_msg}\033[0m")
        return False

# --- FILE & DIRECTORY UTILITIES ---

def create_temp_dir(base_name, output_signal=None, error_signal=None):
    """
    Creates a unique temporary directory for processing.
    Emits status/errors via signals if provided.
    Returns the path to the created directory or None on failure.
    """
    temp_path_base = config.MAIN_TEMP_DIR
    original_dir = os.path.dirname(base_name)
    file_name_part = os.path.splitext(os.path.basename(base_name))[0]
    temp_dir_prefix = f"{file_name_part}_"
    temp_dir_suffix = "_temp"

    if not config.COPY_LOCALLY:
        # If not copying locally, create temp dir next to original file
        temp_path_base = original_dir # Base dir is original file's dir
        msg = f"Creating temp folder next to original in: \"{original_dir}\""
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    else:
        # Ensure the base temp directory exists if COPY_LOCALLY is True
        if not os.path.exists(config.MAIN_TEMP_DIR):
            try:
                os.makedirs(config.MAIN_TEMP_DIR)
                msg = f"Created main temp directory: \"{config.MAIN_TEMP_DIR}\""
                if output_signal: output_signal.emit(msg)
                else: print(f"\033[91m>>\033[32m {msg}\033[0m")
            except OSError as e:
                err_msg = f"ERROR: Failed to create main temporary directory {config.MAIN_TEMP_DIR}: {e}"
                if error_signal: error_signal.emit(err_msg)
                else: print(f"\033[91m{err_msg}\033[0m")
                return None
        temp_path_base = config.MAIN_TEMP_DIR
        msg = f"Creating temp folder inside: \"{temp_path_base}\""
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")


    # Create unique dir using tempfile.mkdtemp
    try:
        temp_dir = tempfile.mkdtemp(prefix=temp_dir_prefix, suffix=temp_dir_suffix, dir=temp_path_base)
        msg = f"Created temp folder: \"{temp_dir}\""
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")
        return temp_dir
    except OSError as e:
        err_msg = f"ERROR: Failed to create temporary directory in {temp_path_base}: {e}"
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return None
    except Exception as e:
        err_msg = f"ERROR: Unexpected error creating temp directory: {e}"
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return None


def move_files(src_dir, dest_dir, pattern, output_signal=None, error_signal=None):
    """Moves files matching a pattern, emits status/errors via signals."""
    msg = f">> Moving files matching \"{pattern}\" from \"{src_dir}\" to \"{dest_dir}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    moved_any = False
    try:
        # Use absolute paths for glob for reliability
        abs_src_dir = os.path.abspath(src_dir)
        files_to_move = glob.glob(os.path.join(abs_src_dir, '**', pattern), recursive=True)
        files_to_move = [f for f in files_to_move if os.path.isfile(f)]

        if not files_to_move:
            warn_msg = f"WARNING: No files found matching pattern \"{pattern}\" in \"{abs_src_dir}\" or its subdirectories."
            if error_signal: error_signal.emit(warn_msg) # Use error signal for warnings too? Or separate? Let's use error for now.
            else: print(f"\033[93m{warn_msg}\033[0m")
            return False

        if not os.path.exists(dest_dir):
             os.makedirs(dest_dir)

        for file_path in files_to_move:
            try:
                relative_path = os.path.relpath(file_path, abs_src_dir)
                dest_path = os.path.join(dest_dir, relative_path)
                dest_subdir = os.path.dirname(dest_path)

                if not os.path.exists(dest_subdir):
                    try:
                        os.makedirs(dest_subdir)
                    except OSError as e:
                        err_msg = f"ERROR: Failed to create destination subdirectory {dest_subdir}: {e}. Skipping move."
                        if error_signal: error_signal.emit(err_msg)
                        else: print(f"\033[91m{err_msg}\033[0m")
                        continue # Skip this file

                if os.path.exists(dest_path):
                    warn_msg = f"WARNING: Destination file \"{dest_path}\" already exists. Overwriting."
                    if error_signal: error_signal.emit(warn_msg)
                    else: print(f"\033[93m{warn_msg}\033[0m")
                    try:
                        if os.path.isdir(dest_path): shutil.rmtree(dest_path)
                        else: os.remove(dest_path)
                    except OSError as e:
                        err_msg = f"ERROR: Failed to remove existing destination file {dest_path}: {e}. Skipping move."
                        if error_signal: error_signal.emit(err_msg)
                        else: print(f"\033[91m{err_msg}\033[0m")
                        continue # Skip this file

                shutil.move(file_path, dest_path)
                msg = f"Moved \"{relative_path}\""
                if output_signal: output_signal.emit(msg)
                # Don't print fallback here, too verbose

                moved_any = True
            except Exception as e: # Catch error moving individual file
                 err_msg = f"ERROR: Failed to move file \"{relative_path}\": {e}"
                 if error_signal: error_signal.emit(err_msg)
                 else: print(f"\033[91m{err_msg}\033[0m")
                 # Continue with next file

        return moved_any
    except Exception as e: # Catch error during glob or initial setup
        err_msg = f"ERROR: An error occurred while finding files to move: {e}"
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

def cleanup(temp_path, original_file_path=None, output_signal=None, error_signal=None):
    """Cleans up temp dir and optionally source file, emits status/errors."""
    msg = ">> Cleaning up..."
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    # Remove the specific temporary directory
    if temp_path and os.path.exists(temp_path):
        retries = 3
        while retries > 0:
            try:
                shutil.rmtree(temp_path)
                msg = f"Removed temporary directory: \"{temp_path}\""
                if output_signal: output_signal.emit(msg)
                else: print(msg)
                break # Success
            except OSError as e:
                retries -= 1
                err_msg = f"Failed to remove temp directory {temp_path}: {e}"
                if retries == 0:
                    err_msg = f"ERROR: {err_msg} after multiple attempts."
                    if error_signal: error_signal.emit(err_msg)
                    else: print(f"\033[91m{err_msg}\033[0m")
                else:
                    warn_msg = f"WARNING: {err_msg}, retrying..."
                    if error_signal: error_signal.emit(warn_msg) # Emit warning
                    else: print(f"\033[93m{warn_msg}\033[0m")
                    time.sleep(0.5) # Wait before retry
            except Exception as e:
                 err_msg = f"ERROR: Unexpected error removing temporary directory {temp_path}: {e}"
                 if error_signal: error_signal.emit(err_msg)
                 else: print(f"\033[91m{err_msg}\033[0m")
                 break # Unexpected error, stop trying

    # Delete the original source file if requested and exists
    if config.DELETE_SOURCE_ON_SUCCESS and original_file_path and os.path.exists(original_file_path):
        msg = f">> Deleting source file: \"{original_file_path}\""
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")
        try:
            # Try using recycle tool if available
            if os.path.exists(config.TOOL_RECYCLE):
                # Use run_command to capture recycle.exe output/errors
                recycle_success = run_command(
                    [config.TOOL_RECYCLE, '-f', original_file_path],
                    output_signal=output_signal,
                    error_signal=error_signal
                )
                if recycle_success:
                    msg = "Source file sent to Recycle Bin."
                    if output_signal: output_signal.emit(msg)
                    else: print(msg)
                else:
                    # Error emitted by run_command
                    raise OSError("recycle.exe failed") # Raise error to trigger fallback
            else:
                 raise FileNotFoundError # Trigger fallback if recycle.exe not found

        except (OSError, FileNotFoundError) as e: # Catch recycle failure or not found
            if isinstance(e, FileNotFoundError):
                 warn_msg = f"WARNING: recycle.exe not found at {config.TOOL_RECYCLE}, falling back to standard delete."
                 if error_signal: error_signal.emit(warn_msg)
                 else: print(f"\033[93m{warn_msg}\033[0m")
            # Fallback to os.remove
            try:
                 os.remove(original_file_path)
                 msg = "Source file permanently deleted using os.remove."
                 if output_signal: output_signal.emit(msg)
                 else: print(msg)
            except OSError as remove_e:
                 err_msg = f"ERROR: Failed to delete source file {original_file_path} using os.remove: {remove_e}"
                 if error_signal: error_signal.emit(err_msg)
                 else: print(f"\033[91m{err_msg}\033[0m")
        except Exception as e: # Catch unexpected errors during deletion
             err_msg = f"ERROR: An unexpected error occurred during source file deletion: {e}"
             if error_signal: error_signal.emit(err_msg)
             else: print(f"\033[91m{err_msg}\033[0m")


# --- ARCHIVE UTILITIES ---

def extract_archive(archive_path, output_dir, output_signal=None, error_signal=None):
    """Extracts 7z, zip, or rar archives using 7ZA tool, emits status."""
    msg = f">> Extracting archive: \"{os.path.basename(archive_path)}\" to \"{output_dir}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    command = [config.TOOL_7ZA, 'x', archive_path, f'-o{output_dir}', '-y']
    # Pass signals down to run_command
    return run_command(command, output_signal=output_signal, error_signal=error_signal)

# --- PROCESS FLOW UTILITIES ---

def process_file(file_path, conversion_func, format_out, format_out2=None, output_signal=None, error_signal=None):
    """
    Generic function to handle processing a single file.
    Accepts and passes signals for detailed logging.
    """
    original_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name, ext = os.path.splitext(file_name)

    # Emit start message (already done by worker thread)
    # if output_signal:
    #     output_signal.emit(f"\n--------------------------------------------------")
    #     output_signal.emit(f"Processing file: \"{file_path}\"")
    #     output_signal.emit(f"--------------------------------------------------")
    # else:
    #     print(f"\n--------------------------------------------------")
    #     print(f"\033[96mProcessing file: \"{file_path}\"\033[0m")
    #     print(f"--------------------------------------------------")

    # Create temp directory, passing signals
    temp_path = create_temp_dir(file_path, output_signal=output_signal, error_signal=error_signal)
    if temp_path is None:
        err_msg = f"ERROR: Failed to create temp directory for \"{file_name}\". Skipping."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False # Indicate failure

    processing_path = file_path
    # Handle local copy if enabled
    if config.COPY_LOCALLY:
        msg = f">> Copying \"{file_name}\" to \"{temp_path}\""
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")
        try:
            target_copy_path = os.path.join(temp_path, file_name)
            if os.path.isdir(file_path):
                 # If input is a directory, copy its contents into a subdir in temp
                 shutil.copytree(file_path, target_copy_path, dirs_exist_ok=True)
                 processing_path = target_copy_path # Process the copied directory
            else:
                 shutil.copy2(file_path, target_copy_path) # Copy file
                 processing_path = target_copy_path # Process the copied file
        except Exception as e:
            err_msg = f"ERROR: Failed to copy \"{file_name}\" to \"{temp_path}\": {e}"
            if error_signal: error_signal.emit(err_msg)
            else: print(f"\033[91m{err_msg}\033[0m")
            cleanup(temp_path, output_signal=output_signal, error_signal=error_signal) # Clean up created temp dir
            return False # Indicate failure
    else:
        # If not copying, process in place relative to original dir,
        # temp_path is only for intermediate files generated by tools.
        processing_path = file_path
        msg = f">> Processing \"{file_name}\" in place."
        if output_signal: output_signal.emit(msg)
        # else: print(f"\033[91m>>\033[32m {msg}\033[0m") # Less verbose for inplace

    # Call the specific conversion routine, passing signals
    success = conversion_func(
        processing_path,
        temp_path,
        name,
        output_signal=output_signal,
        error_signal=error_signal
    )

    if success:
        move_success = False
        if format_out:
            # Move primary output format
            move_success1 = move_files(temp_path, original_dir, f"*.{format_out}", output_signal, error_signal)
            move_success = move_success1

            # Move secondary output format if specified
            if format_out2:
                move_success2 = move_files(temp_path, original_dir, f"*.{format_out2}", output_signal, error_signal)
                # Overall success requires both moves if format_out2 is defined
                move_success = move_success1 and move_success2

            # Special handling for GDI (move associated tracks)
            if format_out == 'gdi':
                 # These moves are secondary; main success depends on the .gdi file move (move_success1)
                 move_files(temp_path, original_dir, f"*.bin", output_signal, error_signal)
                 move_files(temp_path, original_dir, f"*.raw", output_signal, error_signal)
                 move_success = move_success1 # GDI success still depends only on the .gdi file being moved

        else: # No output format specified (e.g., audio handled differently)
             move_success = True # Assume success if conversion reported success and no move needed

        # Final status check
        if move_success:
            # Success message emitted by worker thread
            cleanup(temp_path, file_path, output_signal, error_signal) # Clean up temp, maybe delete source
            return True
        else:
            # Emit error about move failure
            err_msg = f"ERROR: Conversion reported success, but failed to move expected output file(s) back for \"{file_name}\"."
            if error_signal: error_signal.emit(err_msg)
            else: print(f"\033[91m{err_msg}\033[0m")
            cleanup(temp_path, output_signal=output_signal, error_signal=error_signal) # Clean up temp, DON'T delete source
            return False
    else:
        # Error message emitted by worker thread or conversion func
        cleanup(temp_path, output_signal=output_signal, error_signal=error_signal) # Clean up temp, DON'T delete source
        return False

# --- Batch Processing (Mainly for CLI, not directly used by GUI worker) ---
# This function remains largely unchanged as the GUI handles file iteration.
# It still uses print for its top-level status messages.
def process_input(input_path, conversion_func, formats_in, format_out, format_out2=None):
    """Handles processing either a single file or all files in a folder matching input formats."""
    if isinstance(formats_in, str): formats_in = [formats_in]
    formats_in = [f.lower() for f in formats_in]
    format_out = format_out.lower() if format_out else None
    format_out2 = format_out2.lower() if format_out2 else None
    input_patterns_str = ", ".join([f"*.{f}" for f in formats_in])

    if os.path.isdir(input_path):
        print(f"\033[94m>> Starting Batch in folder: \"{input_path}\"\033[0m")
        print(f"\033[94m>> Searching for files matching: {input_patterns_str}\033[0m")
        processed_count, failed_count, found_files = 0, 0, False
        files_to_process = []
        for fmt in formats_in:
            # Use absolute path for glob search
            abs_input_path = os.path.abspath(input_path)
            pattern = os.path.join(abs_input_path, '**', f'*.{fmt}')
            try:
                 found = glob.glob(pattern, recursive=True)
                 # Filter out files inside potential temp directories more robustly
                 norm_temp_dir = os.path.normpath(config.MAIN_TEMP_DIR)
                 found = [f for f in found if '_temp' not in os.path.normpath(f) and norm_temp_dir not in os.path.normpath(f)]
                 if found:
                     files_to_process.extend(found)
                     found_files = True
            except Exception as e:
                 print(f"\033[91mERROR: Failed to search for files with pattern {pattern}: {e}\033[0m")

        files_to_process = sorted(list(set(files_to_process))) # Unique, sorted list
        if not found_files:
            print(f"\033[93m>> No files matching {input_patterns_str} found in \"{input_path}\" or its subdirectories.\033[0m")
            return

        print(f"\033[94m>> Found {len(files_to_process)} file(s) to process.\033[0m")
        for file_path in files_to_process:
             # Call process_file without signals for CLI mode
            if process_file(file_path, conversion_func, format_out, format_out2):
                processed_count += 1
            else:
                failed_count += 1
        print(f"\n--------------------------------------------------")
        print(f"\033[94m>> Batch processing complete.\033[0m")
        print(f"\033[92m   Processed: {processed_count}\033[0m")
        print(f"\033[91m   Failed:    {failed_count}\033[0m")
        print(f"--------------------------------------------------")

    elif os.path.isfile(input_path):
        file_ext = os.path.splitext(input_path)[1].lower().lstrip('.')
        if file_ext in formats_in:
            # Call process_file without signals for CLI mode
            process_file(input_path, conversion_func, format_out, format_out2)
        else:
            print(f"\033[91mERROR: File type '.{file_ext}' does not match expected input format(s): {input_patterns_str}.\033[0m")
            print_help(formats_in, format_out, format_out2)
    else:
        print(f"\033[91mERROR: Invalid input path: \"{input_path}\". Not a file or directory.\033[0m")
        print_help(formats_in, format_out, format_out2)

# Placeholder for print_help if needed within utils, though likely better in main script
def print_help(formats_in, format_out, format_out2=None):
    print("\n\033[94m--- Help ---")
    input_formats_str = ", ".join([f"*.{f}" for f in formats_in]) if formats_in else "N/A"
    output_formats_str = f"*.{format_out}" if format_out else "N/A"
    if format_out2: output_formats_str += f" / *.{format_out2}"
    print(f" Input : {input_formats_str}")
    print(f" Output: {output_formats_str}")
    print(f" Usage: Provide a path to a file or folder containing input files.")
    print("--------------\033[0m")