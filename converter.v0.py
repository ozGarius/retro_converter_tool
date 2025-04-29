import os
import subprocess
import shutil
import sys
import glob

# --- SETTINGS ---
# Default settings - can be overridden by specific conversion types
# COPY_LOCALLY:
# Set to True to copy files to a temporary directory on MAIN_TEMP_DIR before processing.
# Useful if MAIN_TEMP_DIR is on a faster drive (e.g., SSD) than the source files.
# Set to False to process files directly in the source directory (or a subdirectory within it).
# This avoids the copy step but means tools operate on the source drive.
COPY_LOCALLY = True

# DELETE_SOURCE_ON_SUCCESS:
# Set to True to automatically delete the original source file after a successful conversion.
# Set to False to keep the original source file.
DELETE_SOURCE_ON_SUCCESS = False

# MAIN_TEMP_DIR:
# The base directory for temporary folders when COPY_LOCALLY is True.
# Choose a location on a fast drive (like an SSD) for best performance.
# Ensure this path exists and is writable by the script.
MAIN_TEMP_DIR = "C:\\TEMP"

# COMPRESS_LEVEL:
# Default compression level for tools that support it (e.g., DolphinTool ZSTD).
# Higher values (e.g., 22 for DolphinTool) result in better compression but slower processing.
# Lower values result in faster processing but less compression.
COMPRESS_LEVEL = 22

# VALIDATE_FILE:
# Set to True to validate the output file after compression (currently only used for ZIP to 7Z).
# Adds processing time but ensures the output file is not corrupted.
VALIDATE_FILE = True

# Define paths to external tools relative to the script location
# The script assumes a subdirectory named 'convert_tools' exists in the same directory as the script.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(SCRIPT_DIR, 'convert_tools')

# Updated paths based on user feedback
TOOL_7ZA = os.path.join(TOOLS_DIR, '7ZA.exe')          # Required for 7z and Zip conversions
TOOL_DOLPHINTOOL = os.path.join(TOOLS_DIR, 'DolphinTool.exe') # Required for RVZ conversions
TOOL_CHDMAN = os.path.join(TOOLS_DIR, 'chdman.exe')      # Required for CHD conversions
TOOL_MAXCSO = os.path.join(TOOLS_DIR, 'maxcso.exe')      # Required for CSO conversions
TOOL_FFMPEG = os.path.join(TOOLS_DIR, 'ffmpeg.exe')      # Required for Audio conversions
TOOL_RECYCLE = os.path.join(TOOLS_DIR, 'recycle.exe') # Optional: Used for deleting source files to Recycle Bin

# --- HELPER FUNCTIONS ---

def check_tools_exist(tools_list):
    """Checks if the required external tools exist."""
    missing_tools = [tool for tool in tools_list if not os.path.exists(tool)]
    if missing_tools:
        print(f"\033[91mERROR: Missing required tools:\033[0m")
        for tool in missing_tools:
            print(f"- {tool}")
        print(f"\033[91mPlease ensure the 'convert_tools' folder is in the same directory as the script and contains all necessary executables.\033[0m")
        return False
    return True

def run_command(command, cwd=None):
    """Runs an external command and checks for errors."""
    # Print the command being executed for debugging/monitoring
    print(f"\033[91m>>\033[32m Running command: {' '.join(command)}\033[0m")
    try:
        # Use capture_output=True and text=True to get stdout/stderr as strings
        # check=False prevents raising an exception for non-zero exit codes immediately,
        # allowing us to check result.returncode manually.
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        # Print standard output and standard error from the tool
        if result.stdout:
             print("--- STDOUT ---")
             print(result.stdout)
             print("--------------")
        if result.stderr:
             print("--- STDERR ---")
             print(result.stderr)
             print("--------------")

        if result.returncode != 0:
            print(f"\033[91mERROR: Command failed with return code {result.returncode}\033[0m")
            return False
        return True
    except FileNotFoundError:
        print(f"\033[91mERROR: Command not found. Make sure the executable is in the correct path:\n{command[0]}\033[0m")
        return False
    except Exception as e:
        print(f"\033[91mERROR: An error occurred while running the command: {e}\033[0m")
        return False

def create_temp_dir(file_path):
    """Creates a temporary directory for processing."""
    # Get the base name of the file without extension for the temp folder name
    file_name_without_ext = os.path.splitext(os.path.basename(file_path))[0]

    # Determine the temporary path based on the COPY_LOCALLY setting
    if COPY_LOCALLY:
        temp_path = os.path.join(MAIN_TEMP_DIR, 'TEMP', file_name_without_ext)
    else:
        # Create temp dir within the original file's directory
        original_dir = os.path.dirname(file_path)
        temp_path = os.path.join(original_dir, file_name_without_ext)

    print(f"\033[91m>>\033[32m Creating temp folder: \"{temp_path}\"\033[0m")
    # Remove existing temp directory if it exists
    if os.path.exists(temp_path):
        try:
            shutil.rmtree(temp_path)
        except OSError as e:
            print(f"\033[91mERROR: Failed to remove existing temp directory {temp_path}: {e}\033[0m")
            return None
    # Create the new temporary directory
    try:
        os.makedirs(temp_path)
        return temp_path
    except OSError as e:
        print(f"\033[91mERROR: Failed to create temporary directory {temp_path}: {e}\033[0m")
        return None

def move_files(src_dir, dest_dir, pattern):
    """Moves files matching a pattern from source to destination."""
    print(f"\033[91m>>\033[32m Moving files matching \"{pattern}\" from \"{src_dir}\" to \"{dest_dir}\"\033[0m")
    try:
        # Use glob to find files matching the pattern in the source directory
        files_to_move = glob.glob(os.path.join(src_dir, pattern))
        if not files_to_move:
            print(f"\033[91mWARNING: No files found matching pattern \"{pattern}\" in \"{src_dir}\".\033[0m")
            # Depending on the conversion, finding no files might be an error.
            # For expected output files, this should return False.
            # For optional files, it might return True. We'll assume expected output for now.
            return False # Indicate failure if no files were found to move

        # Ensure the destination directory exists
        if not os.path.exists(dest_dir):
             os.makedirs(dest_dir)

        # Move each found file
        for file_path in files_to_move:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(dest_dir, file_name)
            shutil.move(file_path, dest_path)
            print(f"Moved \"{file_name}\"")
        return True
    except Exception as e:
        print(f"\033[91mERROR: An error occurred while moving files: {e}\033[0m")
        return False

def cleanup(temp_path, original_file_path=None):
    """Cleans up temporary files and optionally deletes the source file."""
    print(f"\033[91m>>\033[32m Cleaning up...\033[0m")
    # Remove the temporary directory if it exists
    if temp_path and os.path.exists(temp_path):
        try:
            shutil.rmtree(temp_path)
            print(f"Removed temporary directory: \"{temp_path}\"")
        except OSError as e:
            print(f"\033[91mERROR: Failed to remove temporary directory {temp_path}: {e}\033[0m")

    # Delete the original source file if DELETE_SOURCE_ON_SUCCESS is True
    if DELETE_SOURCE_ON_SUCCESS and original_file_path and os.path.exists(original_file_path):
        print(f"\033[91m>>\033[32m Deleting source file: \"{original_file_path}\"\033[0m")
        try:
            if os.path.exists(TOOL_RECYCLE):
                # Use recycle.exe if available for recycling
                subprocess.run([TOOL_RECYCLE, '-f', original_file_path], capture_output=True, text=True)
                print("Source file sent to Recycle Bin.")
            else:
                # Fallback to permanent delete if recycle.exe is not found
                os.remove(original_file_path)
                print("Source file permanently deleted.")
        except OSError as e:
            print(f"\033[91mERROR: Failed to delete source file {original_file_path}: {e}\033[0m")
        except FileNotFoundError:
             # This case should be caught by the initial tool check, but included for robustness
             print(f"\033[91mWARNING: recycle.exe not found, falling back to standard delete.\033[0m")
             try:
                 os.remove(original_file_path)
                 print("Source file permanently deleted using os.remove.")
             except OSError as e:
                 print(f"\033[91mERROR: Failed to delete source file {original_file_path} using os.remove: {e}\033[0m")


def process_file(file_path, conversion_func, format_out, format_out2=None):
    """Generic function to handle processing a single file."""
    # Declare global variables at the beginning of the function if they are modified
    # (Note: In Python, you don't need global for reading global variables, only for writing)
    # The previous error was due to assigning to 'name' before global was declared for it.
    # Let's avoid relying on global variables for file processing state within the function.
    # Pass necessary info as arguments or derive them locally.

    original_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name, ext = os.path.splitext(file_name)

    print(f"\033[91m>>\033[32m Processing file: \"{file_path}\"\033[0m")

    # Create temporary directory
    # Pass the full file path to create_temp_dir so it can derive the temp folder name
    temp_path = create_temp_dir(file_path)
    if temp_path is None:
        return False # Indicate failure

    # Copy file to temporary directory if copyLocally is enabled
    if COPY_LOCALLY:
        print(f"\033[91m>>\033[32m Copying \"{file_name}\" to \"{temp_path}\"\033[0m")
        try:
            shutil.copy2(file_path, temp_path) # copy2 attempts to preserve metadata
        except Exception as e:
            print(f"\033[91mERROR: Failed to copy \"{file_name}\" to \"{temp_path}\": {e}\033[0m")
            cleanup(temp_path)
            return False

    # Perform the specific conversion
    # Pass necessary arguments to the conversion routine
    success = conversion_func(os.path.join(temp_path, file_name), temp_path, name)

    # Move output file(s) back and cleanup
    if success:
        # Determine the output file pattern(s) to move
        # Use the format_out and format_out2 arguments passed to process_file
        if format_out2: # Handle multi-file output like CUE/BIN
             move_success1 = move_files(temp_path, original_dir, f"*.{format_out}")
             move_success2 = move_files(temp_path, original_dir, f"*.{format_out2}")
             move_success = move_success1 and move_success2
        else: # Handle single-file output
             move_success = move_files(temp_path, original_dir, f"*.{format_out}")

        if move_success:
            print(f"\033[91m>>\033[32m Done processing \"{file_name}\"\033[0m")
            cleanup(temp_path, file_path) # Pass original_file_path for deletion
            return True
        else:
            print(f"\033[91mERROR: Failed to move output file(s) back for \"{file_name}\".\033[0m")
            cleanup(temp_path) # Still clean up temp, but don't delete source
            return False
    else:
        print(f"\033[91mERROR: Conversion failed for \"{file_name}\".\033[0m")
        cleanup(temp_path) # Still clean up temp, but don't delete source
        return False


def process_input(input_path, conversion_func, format_in, format_out, format_in2=None, format_out2=None):
    """Handles processing either a single file or all files in a folder."""
    if os.path.isdir(input_path):
        print(f"\033[91m>>\033[32m Starting Batch in folder: \"{input_path}\"\033[0m")
        processed_count = 0
        failed_count = 0

        # Get list of files to process based on input format(s)
        files_to_process = []
        if format_in2: # Handle multiple input formats (like CUE/GDI)
            files_to_process.extend(glob.glob(os.path.join(input_path, f"*.{format_in}")))
            files_to_process.extend(glob.glob(os.path.join(input_path, f"*.{format_in2}")))
        else: # Handle single input format
             files_to_process.extend(glob.glob(os.path.join(input_path, f"*.{format_in}")))

        # Special handling for ZIP to CHD which also accepts *.z*
        if format_in == 'zip' and format_out == 'chd':
             files_to_process.extend(glob.glob(os.path.join(input_path, f"*.z*")))

        # Remove duplicates in case of multiple input patterns matching the same file
        files_to_process = list(set(files_to_process))

        if not files_to_process:
            input_patterns = f"*.{format_in}"
            if format_in2:
                input_patterns += f" or *.{format_in2}"
            if format_in == 'zip' and format_out == 'chd':
                 input_patterns += " or *.z*"
            print(f"\033[91m>>\033[32m No {input_patterns} files found in \"{input_path}\".\033[0m")
            return

        for file_path in files_to_process:
            # Call process_file with the specific conversion function and output formats
            if process_file(file_path, conversion_func, format_out, format_out2):
                processed_count += 1
            else:
                failed_count += 1
        print(f"\033[91m>>\033[32m Batch processing complete. Processed: {processed_count}, Failed: {failed_count}\033[0m")

    elif os.path.isfile(input_path):
        file_ext = os.path.splitext(input_path)[1].lower().lstrip('.')
        is_supported = False
        supported_in_formats = [format_in.lower()]
        if format_in2:
            supported_in_formats.append(format_in2.lower())
        # Special handling for ZIP to CHD which also accepts *.z*
        if format_in == 'zip' and format_out == 'chd':
             if 'z' in file_ext: # Simple check for *.z*
                 is_supported = True

        if file_ext in supported_in_formats or is_supported:
            # Call process_file with the specific conversion function and output formats
            process_file(input_path, conversion_func, format_out, format_out2)
        else:
            print(f"\033[91mERROR: File type '.{file_ext}' not supported for this conversion.\033[0m")
            print_help(format_in, format_out, format_in2=format_in2)
    else:
        print(f"\033[91mERROR: Invalid input path: \"{input_path}\". Not a file or directory.\033[0m")
        print_help(format_in, format_out, format_in2=format_in2)


# --- SPECIFIC CONVERSION ROUTINES ---
# These functions contain the unique commands for each conversion type.
# They take the full path to the file in the temp dir, the temp dir path, and the file name without extension.
# They should return True on success, False on failure.

def convert_7z_to_rvz_routine(temp_file_path, temp_dir, name):
    """Converts a 7z archive containing an ISO to RVZ."""
    print(f"\033[91m>>\033[32m Extracting archive: \"{os.path.basename(temp_file_path)}\"\033[0m")
    # Use os.path.dirname(temp_file_path) for the output directory
    if not run_command([TOOL_7ZA, 'x', temp_file_path, f'-o{os.path.dirname(temp_file_path)}']):
        return False

    # Find the extracted ISO file(s) in the temp_dir
    extracted_isos = glob.glob(os.path.join(temp_dir, '*.iso'))
    if not extracted_isos:
        print(f"\033[91mERROR: No ISO file found after extracting {os.path.basename(temp_file_path)}.\033[0m")
        return False
    extracted_iso_path = extracted_isos[0] # Assume the first found ISO is the correct one

    print(f"\033[91m>>\033[32m Extracting succeeded, Compressing ISO to RVZ...\033[0m")
    output_rvz_path = os.path.join(temp_dir, f"{name}.rvz")
    command = [
        TOOL_DOLPHINTOOL, 'convert',
        f'--user={temp_dir}', # DolphinTool might need user directory specified
        f'--input={extracted_iso_path}',
        f'--output={output_rvz_path}',
        '--format=rvz',
        '--compression=zstd',
        '--block_size=131072',
        f'--compression_level={COMPRESS_LEVEL}'
    ]
    if not run_command(command):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_rvz_path) or os.path.getsize(output_rvz_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_rvz_path)}\" was not created or is empty.\033[0m")
        return False

    return True

def convert_chd_to_cuebin_routine(temp_file_path, temp_dir, name):
    """Converts a CHD file to CUE/BIN."""
    print(f"\033[91m>>\033[32m Verifying CHD: \"{os.path.basename(temp_file_path)}\"\033[0m")
    if not run_command([TOOL_CHDMAN, 'verify', '-i', temp_file_path]):
        return False

    print(f"\033[91m>>\033[32m Extracting CHD to CUE/BIN...\033[0m")
    output_cue_path = os.path.join(temp_dir, f"{name}.cue")
    output_bin_path = os.path.join(temp_dir, f"{name}.bin")
    command = [
        TOOL_CHDMAN, 'extractcd',
        '-i', temp_file_path,
        '-o', output_cue_path,
        '-ob', output_bin_path
    ]
    if not run_command(command):
        return False

    # Check if output files were created and are not zero size
    if not os.path.exists(output_cue_path) or os.path.getsize(output_cue_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_cue_path)}\" was not created or is empty.\033[0m")
        return False
    if not os.path.exists(output_bin_path) or os.path.getsize(output_bin_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_bin_path)}\" was not created or is empty.\033[0m")
        return False

    return True

def convert_chd_to_gdi_routine(temp_file_path, temp_dir, name):
    """Converts a CHD file to GDI."""
    print(f"\033[91m>>\033[32m Verifying CHD: \"{os.path.basename(temp_file_path)}\"\033[0m")
    if not run_command([TOOL_CHDMAN, 'verify', '-i', temp_file_path]):
        return False

    print(f"\033[91m>>\033[32m Extracting CHD to GDI...\033[0m")
    output_gdi_path = os.path.join(temp_dir, f"{name}.gdi")
    command = [
        TOOL_CHDMAN, 'extractcd',
        '-i', temp_file_path,
        '-o', output_gdi_path
    ]
    if not run_command(command):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_gdi_path) or os.path.getsize(output_gdi_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_gdi_path)}\" was not created or is empty.\033[0m")
        return False

    return True

def convert_cso_to_chd_routine(temp_file_path, temp_dir, name):
    """Converts a CSO file to CHD."""
    print(f"\033[91m>>\033[32m Decompressing CSO: \"{os.path.basename(temp_file_path)}\"\033[0m")
    # maxcso --decompress needs to be run from the directory containing the file
    cso_file_name = os.path.basename(temp_file_path)
    # Output path is specified, so it shouldn't need cwd change, but original script did.
    # Let's stick to specifying output path explicitly.
    decompressed_iso_path = os.path.join(temp_dir, f"{name}.iso") # Predict the output name
    if not run_command([TOOL_MAXCSO, '--decompress', temp_file_path, '--output-path', temp_dir]):
        return False

    # Verify the decompressed ISO file exists
    if not os.path.exists(decompressed_iso_path):
        print(f"\033[91mERROR: Decompressed ISO file \"{os.path.basename(decompressed_iso_path)}\" was not created.\033[0m")
        return False

    print(f"\033[91m>>\033[32m Compressing ISO to CHD...\033[0m")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [
        TOOL_CHDMAN, 'createcd',
        '-i', decompressed_iso_path,
        '-o', output_chd_path
    ]
    if not run_command(command):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_chd_path)}\" was not created or is empty.\033[0m")
        return False

    return True

def convert_cuegdi_to_chd_routine(temp_file_path, temp_dir, name):
    """Converts CUE or GDI files to CHD."""
    print(f"\033[91m>>\033[32m Compressing CUE/GDI to CHD: \"{os.path.basename(temp_file_path)}\"\033[0m")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [
        TOOL_CHDMAN, 'createcd',
        '-i', temp_file_path,
        '-o', output_chd_path
    ]
    if not run_command(command):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_chd_path)}\" was not created or is empty.\033[0m")
        return False

    return True

def convert_iso_to_cso_routine(temp_file_path, temp_dir, name):
    """Converts an ISO file to CSO."""
    print(f"\033[91m>>\033[32m Compressing ISO to CSO: \"{os.path.basename(temp_file_path)}\"\033[0m")
    # maxcso needs to be run from the directory containing the file
    iso_file_name = os.path.basename(temp_file_path)
    # Predict the output CSO name
    output_cso_path = os.path.join(temp_dir, f"{name}.cso")
    # Call maxcso with explicit input and output
    if not run_command([TOOL_MAXCSO, temp_file_path, '-o', output_cso_path]):
         return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_cso_path) or os.path.getsize(output_cso_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_cso_path)}\" was not created or is empty.\033[0m")
        return False

    return True

def convert_iso_to_chd_routine(temp_file_path, temp_dir, name):
    """Converts an ISO file to CHD."""
    print(f"\033[91m>>\033[32m Compressing ISO to CHD: \"{os.path.basename(temp_file_path)}\"\033[0m")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [
        TOOL_CHDMAN, 'createcd',
        '-i', temp_file_path,
        '-o', output_chd_path
    ]
    if not run_command(command):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_chd_path)}\" was not created or is empty.\033[0m")
        return False

    return True

def convert_iso_to_rvz_routine(temp_file_path, temp_dir, name):
    """Converts an ISO file to RVZ."""
    print(f"\033[91m>>\033[32m Compressing ISO to RVZ: \"{os.path.basename(temp_file_path)}\"\033[0m")
    output_rvz_path = os.path.join(temp_dir, f"{name}.rvz")
    command = [
        TOOL_DOLPHINTOOL, 'convert',
        f'--user={temp_dir}', # DolphinTool might need user directory specified
        f'--input={temp_file_path}',
        f'--output={output_rvz_path}',
        '--format=rvz',
        '--compression=zstd',
        '--block_size=131072',
        f'--compression_level={COMPRESS_LEVEL}'
    ]
    if not run_command(command):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_rvz_path) or os.path.getsize(output_rvz_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_rvz_path)}\" was not created or is empty.\033[0m")
        return False

    return True

def convert_rvz_to_iso_routine(temp_file_path, temp_dir, name):
    """Converts an RVZ file to ISO."""
    print(f"\033[91m>>\033[32m Converting RVZ to ISO: \"{os.path.basename(temp_file_path)}\"\033[0m")
    output_iso_path = os.path.join(temp_dir, f"{name}.iso")
    command = [
        TOOL_DOLPHINTOOL, 'convert',
        f'--user={temp_dir}', # DolphinTool might need user directory specified
        f'--input={temp_file_path}',
        f'--output={output_iso_path}',
        '--format=iso' # Output format is iso
    ]
    if not run_command(command):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_iso_path) or os.path.getsize(output_iso_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_iso_path)}\" was not created or is empty.\033[0m")
        return False

    return True

def convert_zip_to_cso_routine(temp_file_path, temp_dir, name):
    """Converts a ZIP archive containing an ISO to CSO."""
    print(f"\033[91m>>\033[32m Extracting archive: \"{os.path.basename(temp_file_path)}\"\033[0m")
    # Use os.path.dirname(temp_file_path) for the output directory
    if not run_command([TOOL_7ZA, 'x', temp_file_path, f'-o{os.path.dirname(temp_file_path)}']):
        return False

    # Find the extracted ISO file in the temp_dir
    extracted_isos = glob.glob(os.path.join(temp_dir, '*.iso'))
    if not extracted_isos:
        print(f"\033[91mERROR: No ISO file found after extracting {os.path.basename(temp_file_path)}.\033[0m")
        return False
    extracted_iso_path = extracted_isos[0] # Assume the first found ISO is the correct one

    print(f"\033[91m>>\033[32m Compressing ISO to CSO: \"{os.path.basename(extracted_iso_path)}\"\033[0m")
    # maxcso needs to be run with explicit input and output paths
    output_cso_path = os.path.join(temp_dir, f"{name}.cso") # Predict the output CSO name
    if not run_command([TOOL_MAXCSO, extracted_iso_path, '-o', output_cso_path]):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_cso_path) or os.path.getsize(output_cso_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_cso_path)}\" was not created or is empty.\033[0m")
        return False

    # No need to rename if maxcso outputted with the correct name

    return True

def convert_zip_to_7z_routine(temp_file_path, temp_dir, name):
    """Converts a ZIP archive to 7z."""
    print(f"\033[91m>>\033[32m Extracting archive: \"{os.path.basename(temp_file_path)}\"\033[0m")
    # Use os.path.dirname(temp_file_path) for the output directory
    if not run_command([TOOL_7ZA, 'x', temp_file_path, f'-o{os.path.dirname(temp_file_path)}']):
        return False

    print(f"\033[91m>>\033[32m Compressing extracted content to 7Z...\033[0m")
    output_7z_path = os.path.join(temp_dir, f"{name}.7z")
    # Assuming compression level -mx9 and md=128m from original script
    command = [
        TOOL_7ZA, 'a', '-t7z', '-mx9', '-md=128m',
        output_7z_path,
        os.path.join(temp_dir, '*') # Add all extracted files/folders from temp_dir
    ]
    if not run_command(command):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_7z_path) or os.path.getsize(output_7z_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_7z_path)}\" was not created or is empty.\033[0m")
        return False

    # Validate the output file if setting is enabled
    if VALIDATE_FILE:
        print(f"\033[91m>>\033[32m Validating archive...\033[0m")
        if not run_command([TOOL_7ZA, 't', output_7z_path]):
            print(f"\033[91mValidation failed for \"{os.path.basename(output_7z_path)}\".\033[0m")
            # Optional: Delete the bad 7z file
            # if os.path.exists(output_7z_path):
            #     try:
            #         os.remove(output_7z_path)
            #         print("Deleted bad 7Z file.")
            #     except OSError as e:
            #         print(f"\033[91mERROR: Failed to delete bad 7Z file: {e}\033[0m")
            return False # Indicate failure if validation fails
        else:
            print(f"\033[91m>>\033[32m Validation passed.\033[0m")

    return True

def convert_zip_to_chd_routine(temp_file_path, temp_dir, name):
    """Converts a ZIP archive containing CUE/BIN or other CD image files to CHD."""
    print(f"\033[91m>>\033[32m Extracting archive: \"{os.path.basename(temp_file_path)}\"\033[0m")
    # Use os.path.dirname(temp_file_path) for the output directory
    if not run_command([TOOL_7ZA, 'x', temp_file_path, f'-o{os.path.dirname(temp_file_path)}']):
        return False

    print(f"\033[91m>>\033[32m Searching for CUE file in extracted content...\033[0m")
    # Find the extracted CUE file in the temp_dir
    extracted_cue_files = glob.glob(os.path.join(temp_dir, '*.cue'))
    if not extracted_cue_files:
        print(f"\033[91mERROR: No CUE file found after extracting {os.path.basename(temp_file_path)}. Cannot convert to CHD.\033[0m")
        return False
    extracted_cue_path = extracted_cue_files[0] # Assume the first found CUE is the correct one

    print(f"\033[91m>>\033[32m Compressing extracted CUE/BIN to CHD...\033[0m")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd") # Output CHD named after original zip
    command = [
        TOOL_CHDMAN, 'createcd',
        '-i', extracted_cue_path, # Use the found CUE file as input
        '-o', output_chd_path
    ]
    if not run_command(command):
        return False

    # Check if output file was created and is not zero size
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        print(f"\033[91mERROR: Output file \"{os.path.basename(output_chd_path)}\" was not created by chdman or is empty.\033[0m")
        return False

    return True

def convert_folder_to_flac_routine(input_folder_path):
    """Converts all audio files in a folder (and subfolders) to FLAC."""
    print(f"\033[91m>>\033[32m Starting Folder to FLAC conversion in: \"{input_folder_path}\"\033[0m")
    processed_count = 0
    failed_count = 0
    # Use os.walk to recursively find files in the folder
    for root, _, files in os.walk(input_folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            output_file_path = os.path.join(root, f"{os.path.splitext(file)[0]}.flac")

            # Avoid converting already converted files or the script itself
            if file_path.lower().endswith('.flac') or file_path.lower().endswith('.py') or file_path.lower().endswith('.bat'):
                 continue

            print(f"\033[91m>>\033[32m Converting \"{file_path}\" to \"{output_file_path}\"\033[0m")
            command = [TOOL_FFMPEG, '-i', file_path, output_file_path]
            if run_command(command):
                processed_count += 1
                # Optional: Delete source file after successful conversion
                if DELETE_SOURCE_ON_SUCCESS:
                    print(f"\033[91m>>\033[32m Deleting source file: \"{file_path}\"\033[0m")
                    try:
                        if os.path.exists(TOOL_RECYCLE):
                             subprocess.run([TOOL_RECYCLE, '-f', file_path], capture_output=True, text=True)
                             print("Source file sent to Recycle Bin.")
                        else:
                             os.remove(file_path)
                             print("Source file permanently deleted.")
                    except OSError as e:
                         print(f"\033[91mERROR: Failed to delete source file {file_path}: {e}\033[0m")
                    except FileNotFoundError:
                         print(f"\033[91mWARNING: recycle.exe not found, falling back to standard delete.\033[0m")
                         try:
                             os.remove(file_path)
                             print("Source file permanently deleted using os.remove.")
                         except OSError as e:
                             print(f"\033[91mERROR: Failed to delete source file {file_path} using os.remove: {e}\033[0m")

            else:
                failed_count += 1

    print(f"\033[91m>>\033[32m Folder to FLAC batch complete. Processed: {processed_count}, Failed: {failed_count}\033[0m")
    # This conversion doesn't use a temporary directory in the same way, so no temp cleanup needed here.
    return True # Indicate the batch process completed (even if some files failed)


# --- MAIN MENU ---

def print_menu():
    """Displays the main menu."""
    os.system('cls' if os.name == 'nt' else 'clear') # Clear console
    print(f"\033[91m>>\033[32m Consolidated File Converter \033[0m")
    print(f"\033[91m>>\033[32m Written by Oz \033[0m")
    print("\n\033[91m>>\033[32m Select a conversion type: \033[0m\n")
    print("\033[32m 1. 7Z to RVZ \033[0m")
    print("\033[32m 2. Audio to Audio \033[0m")
    print("\033[32m 3. CHD to CUE/BIN \033[0m")
    print("\033[32m 4. CHD to GDI \033[0m")
    print("\033[32m 5. CSO to CHD \033[0m")
    print("\033[32m 6. CUE/GDI to CHD \033[0m")
    print("\033[32m 7. ISO to CSO \033[0m")
    print("\033[32m 8. ISO to CHD \033[0m")
    print("\033[32m 9. ISO to RVZ \033[0m")
    print("\033[32m 10. RVZ to ISO \033[0m")
    print("\033[32m 11. ZIP to CSO \033[0m")
    print("\033[32m 12. ZIP to 7Z \033[0m")
    print("\033[32m 13. ZIP to CHD \033[0m")
    print("\033[32m 14. Folder to FLAC \033[0m") # New option
    print("\n\033[91m 0. Exit \033[0m\n")

def print_help(format_in, format_out, format_in2=None):
    """Prints help message for a specific conversion."""
    print(f"\033[91m>>\033[32m Usage: Drag and drop file(s)/folder onto the script, or enter path when prompted.\033[0m")
    input_formats = f"*.{format_in}"
    if format_in2:
        input_formats += f" or *.{format_in2}"
    output_formats = f"*.{format_out}"
    print(f"\033[91m>>\033[32m This conversion handles {input_formats} input files and outputs {output_formats}.\033[0m")
    print(f"\033[91m>>\033[32m Example: converter.py \"/path/to/your/folder\" or converter.py \"/path/to/your/file.{format_in}\"\033[0m")
    if format_in == 'zip' and format_out == 'chd':
         print(f"\033[91m>>\033[32m This conversion also supports *.z* files as input.\033[0m")
    print("\nPress Enter to return to the menu.")
    input() # Wait for user to press Enter

def main():
    """Main function to run the converter script."""

    # Check for essential tools at startup
    essential_tools = [TOOL_7ZA, TOOL_DOLPHINTOOL, TOOL_CHDMAN, TOOL_MAXCSO, TOOL_FFMPEG]
    if not check_tools_exist(essential_tools):
        sys.exit(1) # Exit if essential tools are missing

    while True:
        print_menu()
        choice = input("Enter your choice: ").strip()

        conversion_details = {
            '1': ('7z', 'rvz', convert_7z_to_rvz_routine),
            '2': ('audio', 'audio', None), # Special case handled separately
            '3': ('chd', 'cue', convert_chd_to_cuebin_routine, 'bin'),
            '4': ('chd', 'gdi', convert_chd_to_gdi_routine),
            '5': ('cso', 'chd', convert_cso_to_chd_routine),
            '6': ('cue', 'chd', convert_cuegdi_to_chd_routine, 'gdi'),
            '7': ('iso', 'cso', convert_iso_to_cso_routine),
            '8': ('iso', 'chd', convert_iso_to_chd_routine),
            '9': ('iso', 'rvz', convert_iso_to_rvz_routine),
            '10': ('rvz', 'iso', convert_rvz_to_iso_routine),
            '11': ('zip', 'cso', convert_zip_to_cso_routine),
            '12': ('zip', '7z', convert_zip_to_7z_routine),
            '13': ('zip', 'chd', convert_zip_to_chd_routine),
            '14': ('folder', 'flac', convert_folder_to_flac_routine), # New option
        }

        if choice == '0':
            break
        elif choice == '2':
            # Handle Audio to Audio conversion special case
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\033[91m>>\033[32m Audio to Audio Converter \033[0m")
            print(f"\033[91m>>\033[32m Written by Oz \033[0m")
            print("\n\033[91m>>\033[32m Usage: Drag and drop audio file(s)/folder onto the script, or enter path when prompted.\033[0m")
            print("\033[91m>>\033[32m You will be prompted for input and output formats.\033[0m\n")

            input_format = input("Enter input format (e.g., mp3): ").strip().lower()
            output_format = input("Enter output format (e.g., wav): ").strip().lower()

            if not input_format or not output_format:
                print("\033[91mERROR: Input or output format not specified.\033[0m")
                print("\nPress Enter to return to the menu.")
                input()
                continue

            input_path = input(f"Drag and drop file(s)/folder or enter path containing *.{input_format} files: ").strip().strip('"')

            if not os.path.exists(input_path):
                 print(f"\033[91mERROR: Invalid path: \"{input_path}\".\033[0m")
                 print("\nPress Enter to return to the menu.")
                 input()
                 continue

            if os.path.isdir(input_path):
                print(f"\033[91m>>\033[32m Starting Audio Batch in folder: \"{input_path}\"\033[0m")
                processed_count = 0
                failed_count = 0
                for root, _, files in os.walk(input_path):
                    for file in files:
                        if file.lower().endswith(f'.{input_format}'):
                            file_path = os.path.join(root, file)
                            output_file_path = os.path.join(root, f"{os.path.splitext(file)[0]}.{output_format}")
                            print(f"\033[91m>>\033[32m Converting \"{file_path}\" to \"{output_file_path}\"\033[0m")
                            command = [TOOL_FFMPEG, '-i', file_path, output_file_path]
                            if run_command(command):
                                processed_count += 1
                            else:
                                failed_count += 1
                print(f"\033[91m>>\033[32m Audio Batch processing complete. Processed: {processed_count}, Failed: {failed_count}\033[0m")

            elif os.path.isfile(input_path) and input_path.lower().endswith(f'.{input_format}'):
                output_file_path = os.path.splitext(input_path)[0] + f'.{output_format}'
                print(f"\033[91m>>\033[32m Converting \"{input_path}\" to \"{output_file_path}\"\033[0m")
                command = [TOOL_FFMPEG, '-i', input_path, output_file_path]
                run_command(command)
            else:
                 print(f"\033[91mERROR: Invalid file or file type for audio conversion: \"{input_path}\". Expected *.{input_format}\033[0m")


            print("\nPress Enter to return to the menu.")
            input()
            continue # Return to main menu

        elif choice == '14':
            # Handle Folder to FLAC conversion special case
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\033[91m>>\033[32m Folder to FLAC Converter \033[0m")
            print(f"\033[91m>>\033[32m Written by Oz \033[0m")
            print("\n\033[91m>>\033[32m This conversion processes all audio files in a folder (and subfolders) to FLAC.\033[0m")
            print("\033[91m>>\033[32m Usage: Drag and drop a folder onto the script, or enter folder path when prompted.\033[0m\n")

            input_path = input("Drag and drop folder or enter path to folder: ").strip().strip('"')

            if not os.path.isdir(input_path):
                 print(f"\033[91mERROR: Invalid path: \"{input_path}\". Please provide a folder path.\033[0m")
                 print("\nPress Enter to return to the menu.")
                 input()
                 continue

            convert_folder_to_flac_routine(input_path)

            print("\nPress Enter to return to the menu.")
            input()
            continue # Return to main menu


        elif choice in conversion_details:
            format_in, format_out, conversion_func, *optional_formats = conversion_details[choice]
            format_in2 = optional_formats[0] if optional_formats and len(optional_formats) > 0 else None
            format_out2 = optional_formats[1] if optional_formats and len(optional_formats) > 1 else None


            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\033[91m>>\033[32m {format_in.upper()}{'/' + format_in2.upper() if format_in2 else ''} to {format_out.upper()}{'/' + format_out2.upper() if format_out2 else ''} Converter \033[0m")
            print(f"\033[91m>>\033[32m Written by Oz \033[0m")
            print("\n\033[91m>>\033[32m Current Settings: \033[0m")
            print(f"\033[91m>>\033[32m copyLocally = {COPY_LOCALLY} \033[0m")
            print(f"\033[91m>>\033[32m deleteSourceOnSuccess = {DELETE_SOURCE_ON_SUCCESS} \033[0m")
            print(f"\033[91m>>\033[32m mainTemp = {MAIN_TEMP_DIR} \033[0m")
            if choice in ['1', '9']: # DolphinTool conversions
                 print(f"\033[91m>>\033[32m compressLevel = {COMPRESS_LEVEL} \033[0m")
            if choice == '12': # ZIP to 7Z
                 print(f"\033[91m>>\033[32m validateFile = {VALIDATE_FILE} \033[0m")
            print("\n")


            input_path = input(f"Drag and drop file(s)/folder or enter path containing *.{format_in}{' or *.' + format_in2 if format_in2 else ''} files: ").strip().strip('"')

            if not os.path.exists(input_path):
                 print(f"\033[91mERROR: Invalid path: \"{input_path}\".\033[0m")
                 print("\nPress Enter to return to the menu.")
                 input()
                 continue

            # For standard conversions, call process_input which handles file/folder logic
            process_input(input_path, conversion_func, format_in, format_out, format_in2, format_out2)

            print("\nPress Enter to return to the menu.")
            input()

        else:
            print("\033[91mInvalid choice. Please try again.\033[0m")
            # No need for timeout in Python, input() waits


    print("\033[91m>>\033[32m Exiting converter. \033[0m")

if __name__ == "__main__":
    # Check if arguments were passed (e.g., via drag and drop)
    if len(sys.argv) > 1:
        # If arguments are passed, check if the first is 'audio' for the special case
        # This handles running the script with 'audio input_format output_format' arguments
        if sys.argv[1].lower() == 'audio' and len(sys.argv) == 4:
            input_format = sys.argv[2].lower()
            output_format = sys.argv[3].lower()
            print(f"\033[91m>>\033[32m Audio to Audio Conversion: {input_format.upper()} to {output_format.upper()}\033[0m")
            print("\n\033[91m>>\033[32m Enter path to file(s)/folder to convert:\033[0m")
            input_path = input().strip().strip('"')
            if not os.path.exists(input_path):
                print(f"\033[91mERROR: Invalid path: \"{input_path}\".\033[0m")
                sys.exit(1)
            # Simulate the audio conversion batch process
            if os.path.isdir(input_path):
                print(f"\033[91m>>\033[32m Starting Audio Batch in folder: \"{input_path}\"\033[0m")
                processed_count = 0
                failed_count = 0
                for root, _, files in os.walk(input_path):
                    for file in files:
                        if file.lower().endswith(f'.{input_format}'):
                            file_path = os.path.join(root, file)
                            output_file_path = os.path.join(root, f"{os.path.splitext(file)[0]}.{output_format}")
                            print(f"\033[91m>>\033[32m Converting \"{file_path}\" to \"{output_file_path}\"\033[0m")
                            command = [TOOL_FFMPEG, '-i', file_path, output_file_path]
                            if run_command(command):
                                processed_count += 1
                            else:
                                failed_count += 1
                print(f"\033[91m>>\033[32m Audio Batch processing complete. Processed: {processed_count}, Failed: {failed_count}\033[0m")

            elif os.path.isfile(input_path) and input_path.lower().endswith(f'.{input_format}'):
                output_file_path = os.path.splitext(input_path)[0] + f'.{output_format}'
                print(f"\033[91m>>\033[32m Converting \"{input_path}\" to \"{output_file_path}\"\033[0m")
                command = [TOOL_FFMPEG, '-i', input_path, output_file_path]
                run_command(command)
            else:
                 print(f"\033[91mERROR: Invalid file or file type for audio conversion: \"{input_path}\". Expected *.{input_format}\033[0m")

            sys.exit(0) # Exit after handling audio conversion
        else:
            # For other conversions via drag and drop, prompt the user via the menu first.
            # The main menu will then handle the input path provided by the user.
            # This simplifies logic compared to trying to guess conversion type from drag/drop args.
            # We can potentially pre-fill the input path prompt with the dragged/dropped path.
            # Let's modify the main menu input prompt slightly for this case.
            print("\033[91m>>\033[32m Arguments detected. Please select conversion type from the menu.\033[0m")
            print("\033[91m>>\033[32m You will be prompted for the file/folder path after selecting the type.\033[0m")
            # Store the dragged/dropped path(s) to potentially suggest them later
            dragged_paths = sys.argv[1:]
            # For simplicity now, just inform the user and proceed to menu.
            # A more advanced version could parse the args and pre-select the menu option
            # or pre-fill the path prompt.
            input("Press Enter to continue to the menu...")
            main() # Go to the main menu

    else:
        # No arguments, just run the main menu
        main()
