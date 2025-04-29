# -*- coding: utf-8 -*-
# /convert_tools/conversions.py (Refactored for GUI Logging)

import os
import sys
import glob
import config  # Import settings like tool paths, parameters
import utils   # Import helper functions like run_command, extract_archive, etc.

# --- SPECIFIC CONVERSION ROUTINES ---
# All routines now accept output_signal and error_signal for GUI logging

def convert_archive_to_rvz_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Extracts 7z/zip/rar and converts the contained ISO to RVZ."""
    # Extract archive, passing signals
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        # Error emitted by extract_archive
        return False

    # Search for extracted ISO
    extracted_isos = glob.glob(os.path.join(temp_dir, '**', '*.iso'), recursive=True)
    if not extracted_isos:
        err_msg = f"ERROR: No ISO file found after extracting {os.path.basename(processing_path)}."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    # Prefer ISO in root if multiple found
    root_isos = glob.glob(os.path.join(temp_dir, '*.iso'))
    extracted_iso_path = root_isos[0] if root_isos else extracted_isos[0]
    msg = f"Found ISO: {extracted_iso_path}"
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[94m{msg}\033[0m")

    # Compress to RVZ
    msg = ">> Compressing ISO to RVZ..."
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_rvz_path = os.path.join(temp_dir, f"{name}.rvz")
    command = [
        config.TOOL_DOLPHINTOOL, 'convert',
        f'--input={extracted_iso_path}', f'--output={output_rvz_path}',
        '--format=rvz', '--compression=zstd', '--block_size=131072',
        f'--compression_level={config.COMPRESS_LEVEL}'
    ]
    # Run command, passing signals
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        # Error emitted by run_command
        return False

    # Verify output RVZ file
    if not os.path.exists(output_rvz_path) or os.path.getsize(output_rvz_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_rvz_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    # Clean up intermediate ISO
    try:
        msg = ">> Removing intermediate ISO file..."
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")
        os.remove(extracted_iso_path)
    except OSError as e:
        warn_msg = f"WARNING: Failed to remove intermediate ISO file: {e}"
        if error_signal: error_signal.emit(warn_msg) # Use error signal for warnings
        else: print(f"\033[93m{warn_msg}\033[0m")

    return True # Success

def convert_chd_to_cuebin_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts a CHD file to CUE/BIN."""
    msg = f">> Verifying CHD: \"{os.path.basename(processing_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    # Verify CHD, passing signals
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        warn_msg = "WARNING: CHD verification failed. Attempting extraction anyway."
        if error_signal: error_signal.emit(warn_msg)
        else: print(f"\033[93m{warn_msg}\033[0m")

    # Extract CHD
    msg = ">> Extracting CHD to CUE/BIN..."
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_cue_path = os.path.join(temp_dir, f"{name}.cue")
    command = [config.TOOL_CHDMAN, 'extractcd', '-i', processing_path, '-o', output_cue_path]
    # Run command, passing signals
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        # Error emitted by run_command
        return False

    # Verify output CUE file
    if not os.path.exists(output_cue_path) or os.path.getsize(output_cue_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_cue_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    # Verify output BIN file(s)
    bin_files = glob.glob(os.path.join(temp_dir, '**', '*.bin'), recursive=True)
    if not bin_files:
        err_msg = "ERROR: Output BIN file was not found in temp directory."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False
    if os.path.getsize(bin_files[0]) == 0: # Check first BIN file found
        err_msg = f"ERROR: Output BIN file \"{os.path.basename(bin_files[0])}\" is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    return True # Success

def convert_chd_to_cdiso_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Attempts to convert a CHD file directly to CD ISO using chdman extractcd."""
    msg = f">> Attempting to extract CHD to ISO: \"{os.path.basename(processing_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    note_msg = "   NOTE: This conversion may only work for CHDs created from single-track ISOs."
    if output_signal: output_signal.emit(note_msg)
    else: print(f"\033[93m{note_msg}\033[0m")

    output_iso_path = os.path.join(temp_dir, f"{name}.iso")
    command = [config.TOOL_CHDMAN, 'extractcd', '-i', processing_path, '-o', output_iso_path]

    # Run command, passing signals
    run_success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if not run_success:
        warn_msg = "   chdman command returned an error, checking if ISO was created anyway..."
        if error_signal: error_signal.emit(warn_msg)
        else: print(f"\033[93m{warn_msg}\033[0m")

    # Verify output ISO file
    if os.path.exists(output_iso_path) and os.path.getsize(output_iso_path) > 0:
        msg = f"   Successfully extracted to \"{os.path.basename(output_iso_path)}\"."
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[92m{msg}\033[0m")

        # Check for other potentially problematic files (like .cue)
        other_files = glob.glob(os.path.join(temp_dir, f"{name}.*"))
        other_files = [f for f in other_files if not f.lower().endswith('.iso')]
        if other_files:
            other_names = [os.path.basename(f) for f in other_files]
            warn_msg = f"   Warning: Other files found ({other_names}), source might have been multi-track. ISO validity not guaranteed."
            if error_signal: error_signal.emit(warn_msg)
            else: print(f"\033[93m{warn_msg}\033[0m")
        return True # Success (with potential warning)
    else:
        # Handle failure
        err_msg1 = f"ERROR: Failed to create output ISO file \"{os.path.basename(output_iso_path)}\"."
        err_msg2 = "       The CHD may be multi-track (from CUE/BIN or GDI)."
        err_msg3 = "       Try extracting to CUE/BIN or GDI instead."
        if error_signal:
            error_signal.emit(err_msg1)
            error_signal.emit(err_msg2)
            error_signal.emit(err_msg3)
        else:
            print(f"\033[91m{err_msg1}\033[0m")
            print(f"\033[91m{err_msg2}\033[0m")
            print(f"\033[91m{err_msg3}\033[0m")

        # Clean up any partial files created by failed extraction
        other_files = glob.glob(os.path.join(temp_dir, f"{name}.*"))
        for f in other_files:
            try: os.remove(f)
            except OSError: pass
        return False # Failure

def convert_chd_to_dvdiso_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Attempts to convert a CHD file directly to DVD ISO using chdman extractdvd."""
    msg = f">> Attempting to extract CHD to ISO: \"{os.path.basename(processing_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    note_msg = "   NOTE: This conversion may only work for CHDs created from single-track ISOs."
    if output_signal: output_signal.emit(note_msg)
    else: print(f"\033[93m{note_msg}\033[0m")

    output_iso_path = os.path.join(temp_dir, f"{name}.iso")
    command = [config.TOOL_CHDMAN, 'extractdvd', '-i', processing_path, '-o', output_iso_path]

    # Run command, passing signals
    run_success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if not run_success:
        warn_msg = "   chdman command returned an error, checking if ISO was created anyway..."
        if error_signal: error_signal.emit(warn_msg)
        else: print(f"\033[93m{warn_msg}\033[0m")

    # Verify output ISO file
    if os.path.exists(output_iso_path) and os.path.getsize(output_iso_path) > 0:
        msg = f"   Successfully extracted to \"{os.path.basename(output_iso_path)}\"."
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[92m{msg}\033[0m")

        # Check for other potentially problematic files (like .cue)
        other_files = glob.glob(os.path.join(temp_dir, f"{name}.*"))
        other_files = [f for f in other_files if not f.lower().endswith('.iso')]
        if other_files:
            other_names = [os.path.basename(f) for f in other_files]
            warn_msg = f"   Warning: Other files found ({other_names}), source might have been multi-track. ISO validity not guaranteed."
            if error_signal: error_signal.emit(warn_msg)
            else: print(f"\033[93m{warn_msg}\033[0m")
        return True # Success (with potential warning)
    else:
        # Handle failure
        err_msg1 = f"ERROR: Failed to create output ISO file \"{os.path.basename(output_iso_path)}\"."
        err_msg2 = "       The CHD may be multi-track (from CUE/BIN or GDI)."
        err_msg3 = "       Try extracting to CUE/BIN or GDI instead."
        if error_signal:
            error_signal.emit(err_msg1)
            error_signal.emit(err_msg2)
            error_signal.emit(err_msg3)
        else:
            print(f"\033[91m{err_msg1}\033[0m")
            print(f"\033[91m{err_msg2}\033[0m")
            print(f"\033[91m{err_msg3}\033[0m")

        # Clean up any partial files created by failed extraction
        other_files = glob.glob(os.path.join(temp_dir, f"{name}.*"))
        for f in other_files:
            try: os.remove(f)
            except OSError: pass
        return False # Failure

def convert_chd_to_gdi_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts a CHD file to GDI/BIN/RAW."""
    msg = f">> Verifying CHD: \"{os.path.basename(processing_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    # Verify CHD, passing signals
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        warn_msg = "WARNING: CHD verification failed. Attempting extraction anyway."
        if error_signal: error_signal.emit(warn_msg)
        else: print(f"\033[93m{warn_msg}\033[0m")

    # Extract CHD
    msg = ">> Extracting CHD to GDI..."
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_gdi_path = os.path.join(temp_dir, f"{name}.gdi")
    command = [config.TOOL_CHDMAN, 'extractcd', '-i', processing_path, '-o', output_gdi_path]
    # Run command, passing signals
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        # Error emitted by run_command
        return False

    # Verify output GDI file
    if not os.path.exists(output_gdi_path) or os.path.getsize(output_gdi_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_gdi_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    # Verify track files exist
    track_files = glob.glob(os.path.join(temp_dir, '**', '*.bin'), recursive=True) + \
                  glob.glob(os.path.join(temp_dir, '**', '*.raw'), recursive=True)
    if not track_files:
         err_msg = "ERROR: GDI track files (.bin/.raw) were not created."
         if error_signal: error_signal.emit(err_msg)
         else: print(f"\033[91m{err_msg}\033[0m")
         return False

    return True # Success

def convert_cso_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts a CSO file to CHD."""
    msg = f">> Decompressing CSO: \"{os.path.basename(processing_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    decompressed_iso_path = os.path.join(temp_dir, f"{name}.iso")
    cso_input_path = processing_path

    # Decompress CSO, passing signals
    maxcso_success = utils.run_command(
        [config.TOOL_MAXCSO, '--decompress', cso_input_path, '--output', decompressed_iso_path],
        output_signal=output_signal, error_signal=error_signal
    )
    if not maxcso_success:
        # Check if ISO exists despite error code (maxcso might do this)
        if not os.path.exists(decompressed_iso_path):
            # Error already emitted by run_command if signal exists
            if not error_signal: print(f"\033[91mERROR: maxcso decompression failed and output ISO missing.\033[0m")
            return False
        else:
            warn_msg = "WARNING: maxcso returned an error code, but output ISO exists. Proceeding."
            if error_signal: error_signal.emit(warn_msg)
            else: print(f"\033[93m{warn_msg}\033[0m")

    # Verify decompressed ISO
    if not os.path.exists(decompressed_iso_path) or os.path.getsize(decompressed_iso_path) == 0:
        err_msg = f"ERROR: Decompressed ISO file \"{os.path.basename(decompressed_iso_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    # Compress ISO to CHD
    msg = ">> Compressing ISO to CHD..."
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createcd', '-i', decompressed_iso_path, '-o', output_chd_path]
    # Run command, passing signals
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        # Error emitted by run_command
        return False

    # Verify output CHD
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_chd_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    # Clean up intermediate ISO
    try:
        msg = ">> Removing intermediate ISO file..."
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")
        os.remove(decompressed_iso_path)
    except OSError as e:
        warn_msg = f"WARNING: Failed to remove intermediate ISO file: {e}"
        if error_signal: error_signal.emit(warn_msg)
        else: print(f"\033[93m{warn_msg}\033[0m")

    return True # Success

def convert_discimage_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts ISO, CUE, or GDI files to CHD."""
    msg = f">> Compressing Disc Image to CHD: \"{os.path.basename(processing_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    is_dvd = False
    input_ext = os.path.splitext(processing_path)[1].lower()

    # Check if input is ISO and potentially large (DVD)
    if input_ext == '.iso':
        try:
            # Use 4 GiB threshold (adjust if needed)
            if os.path.getsize(processing_path) > 4 * 1024 * 1024 * 1024:
                 is_dvd = True
                 dvd_msg = "Detected large ISO, using 'createdvd' for CHDMAN."
                 if output_signal: output_signal.emit(dvd_msg)
                 else: print(f"\033[94m{dvd_msg}\033[0m")
        except OSError as e:
             warn_msg = f"WARNING: Could not get size of {processing_path} to check for DVD format: {e}"
             if error_signal: error_signal.emit(warn_msg)
             else: print(f"\033[93m{warn_msg}\033[0m")

    # Select appropriate CHDMAN command
    chdman_command_type = 'createdvd' if is_dvd else 'createcd'
    command = [config.TOOL_CHDMAN, chdman_command_type, '-i', processing_path, '-o', output_chd_path]

    # Run command, passing signals
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        # Error emitted by run_command
        return False

    # Verify output CHD
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_chd_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    return True # Success


def convert_iso_to_cso_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts an ISO file to CSO."""
    msg = f">> Compressing ISO to CSO: \"{os.path.basename(processing_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_cso_path = os.path.join(temp_dir, f"{name}.cso")
    iso_input_path = processing_path
    command = [config.TOOL_MAXCSO, iso_input_path, '--output', output_cso_path]

    # Run command, passing signals
    maxcso_success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if not maxcso_success:
         # Check if CSO exists despite error code
         if not os.path.exists(output_cso_path):
             # Error already emitted by run_command if signal exists
             if not error_signal: print(f"\033[91mERROR: maxcso compression failed and output CSO missing.\033[0m")
             return False
         else:
             warn_msg = "WARNING: maxcso returned an error code, but output CSO exists. Assuming success."
             if error_signal: error_signal.emit(warn_msg)
             else: print(f"\033[93m{warn_msg}\033[0m")

    # Verify output CSO
    if not os.path.exists(output_cso_path) or os.path.getsize(output_cso_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_cso_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    return True # Success

def convert_iso_to_rvz_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts an ISO file to RVZ."""
    msg = f">> Compressing ISO to RVZ: \"{os.path.basename(processing_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_rvz_path = os.path.join(temp_dir, f"{name}.rvz")
    command = [
        config.TOOL_DOLPHINTOOL, 'convert',
        f'--input={processing_path}', f'--output={output_rvz_path}',
        '--format=rvz', '--compression=zstd', '--block_size=131072',
        f'--compression_level={config.COMPRESS_LEVEL}'
    ]
    # Run command, passing signals
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        # Error emitted by run_command
        return False

    # Verify output RVZ
    if not os.path.exists(output_rvz_path) or os.path.getsize(output_rvz_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_rvz_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    return True # Success

def convert_rvz_to_iso_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts an RVZ file to ISO."""
    msg = f">> Converting RVZ to ISO: \"{os.path.basename(processing_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_iso_path = os.path.join(temp_dir, f"{name}.iso")
    command = [config.TOOL_DOLPHINTOOL, 'convert', f'--input={processing_path}', f'--output={output_iso_path}', '--format=iso']
    # Run command, passing signals
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        # Error emitted by run_command
        return False

    # Verify output ISO
    if not os.path.exists(output_iso_path) or os.path.getsize(output_iso_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_iso_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    return True # Success

def convert_archive_to_cso_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Extracts 7z/zip/rar and converts the contained ISO to CSO."""
    # Extract archive, passing signals
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        # Error emitted by extract_archive
        return False

    # Search for extracted ISO
    extracted_isos = glob.glob(os.path.join(temp_dir, '**', '*.iso'), recursive=True)
    if not extracted_isos:
        err_msg = f"ERROR: No ISO file found after extracting {os.path.basename(processing_path)}."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    root_isos = glob.glob(os.path.join(temp_dir, '*.iso'))
    extracted_iso_path = root_isos[0] if root_isos else extracted_isos[0]
    msg = f"Found ISO: {extracted_iso_path}"
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[94m{msg}\033[0m")

    # Compress ISO to CSO
    msg = f">> Compressing ISO to CSO: \"{os.path.basename(extracted_iso_path)}\""
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_cso_path = os.path.join(temp_dir, f"{name}.cso")
    command = [config.TOOL_MAXCSO, extracted_iso_path, '--output', output_cso_path]

    # Run command, passing signals
    maxcso_success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if not maxcso_success:
         # Check if CSO exists despite error code
         if not os.path.exists(output_cso_path):
             # Error already emitted by run_command if signal exists
             if not error_signal: print(f"\033[91mERROR: maxcso compression failed and output CSO missing.\033[0m")
             return False
         else:
             warn_msg = "WARNING: maxcso returned an error code, but output CSO exists. Assuming success."
             if error_signal: error_signal.emit(warn_msg)
             else: print(f"\033[93m{warn_msg}\033[0m")

    # Verify output CSO
    if not os.path.exists(output_cso_path) or os.path.getsize(output_cso_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_cso_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    # Clean up intermediate ISO
    try:
        msg = ">> Removing intermediate ISO file..."
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")
        os.remove(extracted_iso_path)
    except OSError as e:
        warn_msg = f"WARNING: Failed to remove intermediate ISO file: {e}"
        if error_signal: error_signal.emit(warn_msg)
        else: print(f"\033[93m{warn_msg}\033[0m")

    return True # Success

def convert_archive_to_7z_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Extracts ZIP/RAR and recompresses content to 7z."""
    # Extract archive, passing signals
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        # Error emitted by extract_archive
        return False

    # Compress extracted content
    msg = ">> Compressing extracted content to 7Z..."
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    output_7z_path = os.path.join(temp_dir, f"{name}.7z")
    # Use '.' to specify all content within the current working directory (temp_dir)
    content_specifier = '.'
    command = [config.TOOL_7ZA, 'a', '-t7z', '-mx9', '-md=128m', output_7z_path, content_specifier]

    # Run command within temp_dir, passing signals
    if not utils.run_command(command, cwd=temp_dir, output_signal=output_signal, error_signal=error_signal):
        # Error emitted by run_command
        return False

    # Verify output 7z
    if not os.path.exists(output_7z_path) or os.path.getsize(output_7z_path) == 0:
        err_msg = f"ERROR: Output file \"{os.path.basename(output_7z_path)}\" was not created or is empty."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    # Validate archive if enabled
    if config.VALIDATE_FILE:
        msg = ">> Validating archive..."
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")

        # Run validation, passing signals
        if not utils.run_command([config.TOOL_7ZA, 't', output_7z_path], output_signal=output_signal, error_signal=error_signal):
            # Error/Warning emitted by run_command
            err_msg = f"Validation failed for \"{os.path.basename(output_7z_path)}\"."
            # Ensure this specific failure message is emitted
            if error_signal: error_signal.emit(err_msg)
            else: print(f"\033[91m{err_msg}\033[0m")
            return False
        else:
            msg = ">> Validation passed."
            if output_signal: output_signal.emit(msg)
            else: print(f"\033[92m{msg}\033[0m")

    return True # Success

def convert_archive_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Extracts 7z/zip/rar and converts the contained CUE/GDI/ISO to CHD."""
    # Extract archive, passing signals
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        # Error emitted by extract_archive
        return False

    # Search for disc image
    msg = ">> Searching for CUE/GDI/ISO file in extracted content..."
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    extracted_image_path = None
    for pattern in ['*.cue', '*.gdi', '*.iso']:
        # Search recursively within temp_dir
        found = glob.glob(os.path.join(temp_dir, '**', pattern), recursive=True)
        if found:
            # Prefer file in root if multiple found
            root_files = glob.glob(os.path.join(temp_dir, pattern))
            extracted_image_path = root_files[0] if root_files else found[0]
            msg = f"Found disc image: {extracted_image_path}"
            if output_signal: output_signal.emit(msg)
            else: print(f"\033[94m{msg}\033[0m")
            break # Stop searching once found

    if not extracted_image_path:
        err_msg = f"ERROR: No CUE, GDI, or ISO file found after extracting {os.path.basename(processing_path)}. Cannot convert to CHD."
        if error_signal: error_signal.emit(err_msg)
        else: print(f"\033[91m{err_msg}\033[0m")
        return False

    # Call disc image to CHD conversion, passing signals
    msg = ">> Calling disc image to CHD conversion for found file..."
    if output_signal: output_signal.emit(msg)
    else: print(f"\033[91m>>\033[32m {msg}\033[0m")

    # Pass the *original archive name* for the output CHD name
    # Also pass signals down
    if not convert_discimage_to_chd_routine(
        extracted_image_path, temp_dir, name, output_signal, error_signal
    ):
         # Error emitted by convert_discimage_to_chd_routine
         return False

    # Clean up intermediate extracted files (except the final CHD)
    try:
        msg = ">> Removing intermediate extracted files (except CHD)..."
        if output_signal: output_signal.emit(msg)
        else: print(f"\033[91m>>\033[32m {msg}\033[0m")

        output_chd_name = f"{name}.chd"
        for item in os.listdir(temp_dir):
            # Don't delete the output CHD file itself!
            if item.lower() != output_chd_name.lower():
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except OSError as e:
                     # Report error removing specific item but continue cleanup
                     warn_msg = f"WARNING: Failed to remove intermediate item {item_path}: {e}"
                     if error_signal: error_signal.emit(warn_msg)
                     else: print(f"\033[93m{warn_msg}\033[0m")

    except Exception as e:
        warn_msg = f"WARNING: Failed during intermediate file cleanup: {e}"
        if error_signal: error_signal.emit(warn_msg)
        else: print(f"\033[93m{warn_msg}\033[0m")

    return True # Success


# --- Refactored Audio Conversion (CLI Only - No Signal Handling Needed Yet) ---
# This function is called directly by the CLI, not via process_file,
# so it doesn't need signal parameters for now. It uses print directly.
def convert_folder_audio_routine(input_folder_path, output_format, input_format=None):
    """Converts audio files in a folder (recursive) to the specified output format using ffmpeg."""
    mode = f"{input_format.upper()} to {output_format.upper()}" if input_format else f"Folder to {output_format.upper()}"
    print(f"\n\033[94m>> Starting Audio Batch ({mode}) in folder: \"{input_folder_path}\"\033[0m")
    processed_count, failed_count, skipped_count = 0, 0, 0
    files_to_process = []

    # Determine files to process based on input_format
    if input_format:
        pattern = os.path.join(input_folder_path, '**', f'*.{input_format}')
        files_to_process = glob.glob(pattern, recursive=True)
        print(f"\033[94m>> Searching for *.{input_format} files...\033[0m")
    else: # Scan for likely audio files if no input format specified
        pattern = os.path.join(input_folder_path, '**', '*')
        all_files = glob.glob(pattern, recursive=True)
        # Define common non-audio extensions to exclude
        non_audio_exts = {
            '.py', '.bat', '.exe', '.txt', '.log', '.ini', '.cue', '.gdi', '.iso',
            '.chd', '.rvz', '.cso', '.7z', '.zip', '.rar', '.sfv', '.md5', '.jpg',
            '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.nfo', '.url', '.lnk', '.pdf',
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.m3u', '.pls',
            f'.{output_format}' # Exclude target format
        }
        for f in all_files:
            if os.path.isfile(f):
                ext_lower = os.path.splitext(f)[1].lower()
                if ext_lower and ext_lower not in non_audio_exts: # Check if extension exists and not excluded
                    files_to_process.append(f)
        print(f"\033[94m>> Scanning for potential audio files (excluding known non-audio types)...\033[0m")

    if not files_to_process:
         print(f"\033[93m>> No suitable input files found in \"{input_folder_path}\" or subdirectories.\033[0m")
         return False

    print(f"\033[94m>> Found {len(files_to_process)} potential file(s) to process.\033[0m")

    # Process each file
    for file_path in files_to_process:
        root, file_name = os.path.dirname(file_path), os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)
        output_file_path = os.path.join(root, f"{name}.{output_format}")

        # Skip if output already exists
        if os.path.exists(output_file_path):
            print(f"\033[93mSkipping: Output file \"{output_file_path}\" already exists.\033[0m")
            skipped_count += 1
            continue

        print(f"\033[91m>>\033[32m Converting \"{file_path}\" to \"{output_file_path}\"\033[0m")
        # Use -nostdin to prevent ffmpeg from consuming stdin
        command = [config.TOOL_FFMPEG, '-nostdin', '-i', file_path, output_file_path]

        # Call run_command WITHOUT signals for CLI audio conversion
        if utils.run_command(command):
            # Verify output file after successful command run
            if os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
                processed_count += 1
                # Handle source deletion if enabled
                if config.DELETE_SOURCE_ON_SUCCESS:
                    # Call cleanup without signals for CLI audio
                    utils.cleanup(None, file_path)
            else:
                print(f"\033[91mERROR: Conversion command succeeded but output file is missing or empty: \"{output_file_path}\"\033[0m")
                failed_count += 1
                # Clean up potentially empty output file
                if os.path.exists(output_file_path):
                    try: os.remove(output_file_path)
                    except OSError: pass
        else:
            # run_command already printed error
            failed_count += 1
            # Clean up potentially partial/failed output file
            if os.path.exists(output_file_path):
                try: os.remove(output_file_path)
                except OSError: pass

    # Print summary
    print(f"\n--------------------------------------------------")
    print(f"\033[94m>> Audio Batch ({mode}) complete.\033[0m")
    print(f"\033[92m   Processed: {processed_count}\033[0m")
    print(f"\033[91m   Failed:    {failed_count}\033[0m")
    print(f"\033[93m   Skipped:   {skipped_count}\033[0m")
    print(f"--------------------------------------------------")
    return True # Indicate batch attempted