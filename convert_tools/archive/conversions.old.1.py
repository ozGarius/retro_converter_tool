# -*- coding: utf-8 -*-
# /convert_tools/conversions.py (Refactored with Archive Handling, Flexible Dolphin Output, and _emit_or_print)

import os
import glob
import shutil 
import config
import utils 

# --- Internal Helper for Archive Handling in Compression Routines ---
def _handle_archive_input_for_compression(processing_path, base_temp_dir, supported_media_extensions, output_signal=None, error_signal=None):
    """
    Checks if processing_path is an archive. If so, extracts it to a sub-temp dir,
    finds the primary media file, and returns its path and the sub-temp dir path.
    Otherwise, returns the original processing_path and None for the sub-temp dir.

    Args:
        processing_path (str): Path to the input file/folder.
        base_temp_dir (str): The main temporary directory allocated for this file's processing.
        supported_media_extensions (list): List of strings, e.g., ['.iso', '.cue'].
        output_signal, error_signal: Qt signals for logging.

    Returns:
        tuple: (path_to_process, sub_temp_dir_path_or_none)
               path_to_process: Path to the actual media file to be compressed.
               sub_temp_dir_path_or_none: Path to the created sub-temp dir if an archive was extracted, else None.
    """
    file_name = os.path.basename(processing_path)
    name_part, ext_part = os.path.splitext(file_name)
    ext_lower = ext_part.lower()
    
    archive_extensions = ['.7z', '.zip', '.rar', '.gz'] # Supported archives for auto-extraction

    if ext_lower in archive_extensions:
        utils._emit_or_print(f">> Input '{file_name}' is an archive. Attempting extraction...", output_signal, fallback_color_code="\033[96m")
        
        archive_extract_sub_temp_dir = os.path.join(base_temp_dir, f"{name_part}_extracted_content")
        if not os.path.exists(archive_extract_sub_temp_dir):
            try:
                os.makedirs(archive_extract_sub_temp_dir)
            except OSError as e:
                utils._emit_or_print(f"ERROR: Could not create sub-temp dir for archive extraction: {e}", error_signal, is_error=True)
                return processing_path, None # Fallback to trying to process archive directly (likely fail)

        if not utils.extract_archive(processing_path, archive_extract_sub_temp_dir, output_signal, error_signal):
            utils._emit_or_print(f"ERROR: Failed to extract archive '{file_name}'.", error_signal, is_error=True)
            # Cleanup the sub-temp dir we created if extraction fails
            try:
                shutil.rmtree(archive_extract_sub_temp_dir)
            except OSError:
                pass # Best effort cleanup
            return processing_path, None # Fallback

        utils._emit_or_print(f">> Searching for media files ({', '.join(supported_media_extensions)}) in extracted content...", output_signal, fallback_color_code="\033[96m")
        
        found_media_file = None
        for media_ext in supported_media_extensions:
            # Search recursively within the extraction sub_temp_dir
            # Prioritize files in the root of the extracted archive
            root_files = glob.glob(os.path.join(archive_extract_sub_temp_dir, f"*{media_ext}"))
            if root_files:
                found_media_file = root_files[0] # Take the first one found in root
                break
            # If not in root, search recursively
            recursive_files = glob.glob(os.path.join(archive_extract_sub_temp_dir, '**', f"*{media_ext}"), recursive=True)
            if recursive_files:
                found_media_file = recursive_files[0] # Take the first one found recursively
                break
        
        if found_media_file:
            utils._emit_or_print(f"Found media file for compression: {os.path.basename(found_media_file)}", output_signal, fallback_color_code="\033[92m")
            return found_media_file, archive_extract_sub_temp_dir
        else:
            utils._emit_or_print(f"ERROR: No supported media files ({', '.join(supported_media_extensions)}) found in extracted archive '{file_name}'.", error_signal, is_error=True)
            return processing_path, archive_extract_sub_temp_dir # Return original path but still provide sub_temp for cleanup
    else:
        # Not an archive, process directly
        return processing_path, None


# --- COMPRESSION ROUTINES ---
def compress_discimage_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts CD-like disc images (ISO, CUE, IMG, TOC) or archives containing them to CHD."""
    utils._emit_or_print(f">> Starting CD Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[96m") # Cyan for job start
    
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso', '.cue', '.img', '.toc'], output_signal, error_signal
    )

    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        # This means archive extraction failed to find a suitable file, error already logged by helper
        if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(f">> Compressing to CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="\033[92m")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd") # Final CHD goes into the main temp_dir
    command = [config.TOOL_CHDMAN, 'createcd', '-i', actual_media_path, '-o', output_chd_path]
    
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    
    if sub_temp_dir: # Cleanup the directory used for archive extraction
        shutil.rmtree(sub_temp_dir, ignore_errors=True)

    if not success: return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True

def compress_dvdimage_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts DVD ISOs or archives containing them to CHD."""
    utils._emit_or_print(f">> Starting DVD Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[96m")
    
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso', '.img'], output_signal, error_signal # DVD usually .iso or .img
    )

    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(f">> Compressing to DVD CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="\033[92m")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createdvd', '-i', actual_media_path, '-o', output_chd_path]
    
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)

    if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
    
    if not success: return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True

def compress_dolphin_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format="rvz"):
    """Converts an ISO file (or archive containing ISO) to RVZ, GCZ, or VIA using DolphinTool.
       Target format is determined by the 'format_out' passed via process_file, which defaults to 'rvz' here if not specified.
    """
    utils._emit_or_print(f">> Starting Dolphin Compression to {target_format.upper()} for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[96m")

    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso', '.gcm', '.rvz', '.gcz', '.wbfs', '.ciso', '.wad'], output_signal, error_signal # DolphinTool supported inputs
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    output_ext = target_format.lower() # Ensure lowercase
    # DolphinTool uses 'wbfs' for VIA format, adjust if 'via' is passed
    if output_ext == 'via': 
        tool_format_param = 'wbfs' 
        utils._emit_or_print(f"   (Note: VIA output uses WBFS format with DolphinTool)", output_signal, fallback_color_code="\033[93m")
    else:
        tool_format_param = output_ext

    utils._emit_or_print(f">> Compressing to {output_ext.upper()}: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="\033[92m")
    output_file_path = os.path.join(temp_dir, f"{name}.{output_ext}")
    
    command = [
        config.TOOL_DOLPHINTOOL, 'convert', f'--input={actual_media_path}', f'--output={output_file_path}',
        f'--format={tool_format_param}'
    ]
    # Add compression parameters specific to RVZ if that's the target
    if output_ext == 'rvz':
        command.extend(['--compression=zstd', '--block_size=131072', f'--compression_level={config.DOLPHIN_COMPRESS_LEVEL}'])
    # Add other format-specific parameters if needed for GCZ, VIA (WBFS)

    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    
    if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)

    if not success: return False
    if not os.path.exists(output_file_path) or os.path.getsize(output_file_path) == 0:
        utils._emit_or_print(f"ERROR: Output {output_ext.upper()} \"{os.path.basename(output_file_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True

def compress_harddisk_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts raw hard disk images (or archives containing them) to CHD."""
    utils._emit_or_print(f">> Starting Hard Disk Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[96m")
    
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.img', '.raw', '.bin', '.iso'], output_signal, error_signal # Common raw/disk image extensions
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(f">> Compressing to Hard Disk CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="\033[92m")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    # CHDMAN for hard drives: createhd. It needs sector size, or can often auto-detect for raw images.
    # For simplicity, let's assume chdman can auto-detect or use defaults.
    # More specific options like --ident, --chs, --inputoffs might be needed for complex raw images.
    command = [config.TOOL_CHDMAN, 'createhd', '-i', actual_media_path, '-o', output_chd_path]
    
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    
    if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)

    if not success: return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True

def compress_laserdisc_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts LaserDisc images (e.g., raw A/V captures, often .ld or .raw with .cue) to CHD."""
    utils._emit_or_print(f">> Starting LaserDisc Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[96m")
    
    # LaserDisc images might be .cue/.ld, .cue/.raw. CHDMAN 'createld' expects the .cue.
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.cue', '.ld'], output_signal, error_signal 
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(f">> Compressing to LaserDisc CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="\033[92m")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createld', '-i', actual_media_path, '-o', output_chd_path]
    
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)

    if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
    
    if not success: return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True

def compress_raw_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Generic raw image to CHD, often implies hard disk but could be other raw types if CHDMAN supports them via createhd."""
    # This might be very similar to compress_harddisk_to_chd_routine.
    # If 'raw image' implies a different chdman command or parameters, this function would differ.
    # For now, let's assume it's similar to harddisk.
    utils._emit_or_print(f">> Starting Raw Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[96m")
    
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.img', '.raw', '.bin'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(f">> Compressing Raw Image to CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="\033[92m")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    # Using 'createhd' as a general approach for raw images.
    command = [config.TOOL_CHDMAN, 'createhd', '-i', actual_media_path, '-o', output_chd_path]
    
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)

    if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
    
    if not success: return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True

def compress_iso_to_cso_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Converts an ISO file (or archive containing one) to CSO."""
    utils._emit_or_print(f">> Starting ISO to CSO for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[96m")

    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(f">> Compressing ISO to CSO: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="\033[92m")
    output_cso_path = os.path.join(temp_dir, f"{name}.cso")
    command = [config.TOOL_MAXCSO, actual_media_path, '--output', output_cso_path]
    
    maxcso_success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    
    if sub_temp_dir: shutil.rmtree(sub_temp_dir, ignore_errors=True)

    if not maxcso_success:
         if not os.path.exists(output_cso_path): # Check if file was created despite error
             utils._emit_or_print("ERROR: maxcso compression failed and output CSO missing.", error_signal, is_error=True)
             return False
         else: # File exists but tool returned error
             utils._emit_or_print("WARNING: maxcso returned an error code, but output CSO exists. Assuming success.", error_signal, fallback_color_code="\033[93m")
    
    if not os.path.exists(output_cso_path) or os.path.getsize(output_cso_path) == 0: # Final check
        utils._emit_or_print(f"ERROR: Output CSO \"{os.path.basename(output_cso_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True

# --- EXTRACTION ROUTINES ---
def extract_chd_to_cd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format="cue"):
    """Extracts a CHD (CD) to CUE/BIN, TOC/BIN, GDI, or ISO.
       Target format is determined by 'format_out' from process_file.
    """
    utils._emit_or_print(f">> Verifying CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[92m")
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.", error_signal, fallback_color_code="\033[93m")

    output_base_name = os.path.join(temp_dir, f"{name}.{target_format.lower()}")
    utils._emit_or_print(f">> Extracting CHD to {target_format.upper()} ({os.path.basename(output_base_name)})...", output_signal, fallback_color_code="\033[92m")
    
    command = [config.TOOL_CHDMAN, 'extractcd', '-i', processing_path, '-o', output_base_name]
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False # Error already logged

    # Verify primary output file
    if not os.path.exists(output_base_name) or os.path.getsize(output_base_name) == 0:
        utils._emit_or_print(f"ERROR: Output {target_format.upper()} file \"{os.path.basename(output_base_name)}\" was not created or is empty.", error_signal, is_error=True)
        return False

    # Verify secondary files if applicable (e.g., .bin for .cue)
    if target_format.lower() == "cue":
        bin_files = glob.glob(os.path.join(temp_dir, f"{name}*.bin")) # chdman might create track01.bin etc.
        if not bin_files or not any(os.path.getsize(f) > 0 for f in bin_files):
            utils._emit_or_print(f"ERROR: Associated BIN file(s) for CUE sheet '{name}.cue' not found or empty.", error_signal, is_error=True)
            return False
    elif target_format.lower() == "gdi":
        track_files = glob.glob(os.path.join(temp_dir, f"{name}*.bin")) + glob.glob(os.path.join(temp_dir, f"{name}*.raw"))
        if not track_files or not any(os.path.getsize(f) > 0 for f in track_files):
             utils._emit_or_print(f"ERROR: Associated track files (.bin/.raw) for GDI '{name}.gdi' not found or empty.", error_signal, is_error=True)
             return False
    # For ISO or TOC, the primary file is usually sufficient.
    return True

def extract_chd_to_dvd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Extracts a CHD (DVD) to ISO."""
    utils._emit_or_print(f">> Verifying CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[92m")
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.", error_signal, fallback_color_code="\033[93m")

    output_iso_path = os.path.join(temp_dir, f"{name}.iso")
    utils._emit_or_print(f">> Extracting CHD to DVD ISO ({os.path.basename(output_iso_path)})...", output_signal, fallback_color_code="\033[92m")
    command = [config.TOOL_CHDMAN, 'extractdvd', '-i', processing_path, '-o', output_iso_path]
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_iso_path) or os.path.getsize(output_iso_path) == 0:
        utils._emit_or_print(f"ERROR: Output DVD ISO file \"{os.path.basename(output_iso_path)}\" was not created or is empty.", error_signal, is_error=True)
        return False
    return True

def extract_dolphin_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format="iso"):
    """Extracts an RVZ, GCZ, or VIA file to ISO using DolphinTool."""
    # target_format is determined by 'format_out' from process_file, defaulting to 'iso' here.
    utils._emit_or_print(f">> Converting {os.path.splitext(processing_path)[1].upper()} to ISO: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[92m")
    output_iso_path = os.path.join(temp_dir, f"{name}.{target_format.lower()}") # Usually ISO
    
    # DolphinTool 'convert' command with '--format=iso' (or other raw formats if supported for extraction)
    command = [config.TOOL_DOLPHINTOOL, 'convert', f'--input={processing_path}', f'--output={output_iso_path}', f'--format={target_format.lower()}']
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal): return False
    if not os.path.exists(output_iso_path) or os.path.getsize(output_iso_path) == 0:
        utils._emit_or_print(f"ERROR: Output ISO \"{os.path.basename(output_iso_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True

def extract_chd_to_harddisk_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format="img"):
    """Extracts a CHD (Hard Disk) to a raw image format (e.g., IMG)."""
    utils._emit_or_print(f">> Verifying CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[92m")
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.", error_signal, fallback_color_code="\033[93m")

    output_image_path = os.path.join(temp_dir, f"{name}.{target_format.lower()}")
    utils._emit_or_print(f">> Extracting CHD to Hard Disk Image ({os.path.basename(output_image_path)})...", output_signal, fallback_color_code="\033[92m")
    command = [config.TOOL_CHDMAN, 'extracthd', '-i', processing_path, '-o', output_image_path]
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_image_path) or os.path.getsize(output_image_path) == 0:
        utils._emit_or_print(f"ERROR: Output Image \"{os.path.basename(output_image_path)}\" was not created or empty.", error_signal, is_error=True)
        return False
    return True

def extract_chd_to_laserdisc_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format="raw"):
    """Extracts a CHD (LaserDisc) to raw A/V data (often .raw or .ld with .cue)."""
    # This is a placeholder. CHDMAN 'extractld' might output multiple files or a specific structure.
    # The target_format might need to be 'cue' and then associated files are also expected.
    utils._emit_or_print(f"Placeholder: Extract CHD (LaserDisc) to {target_format.upper()} - Not fully implemented.", output_signal, fallback_color_code="\033[93m")
    # Example:
    # output_cue_path = os.path.join(temp_dir, f"{name}.cue")
    # command = [config.TOOL_CHDMAN, 'extractld', '-i', processing_path, '-o', output_cue_path]
    # ... verification of .cue and .raw/.ld files ...
    return False # Mark as not implemented for now

def extract_chd_to_raw_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format="raw"):
    """Extracts a CHD to a generic raw image. Often implies extracthd."""
    # This is similar to extract_chd_to_harddisk_routine if 'raw' means a raw disk image.
    # If it's a different kind of raw extraction, the chdman command might change.
    utils._emit_or_print(f">> Verifying CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="\033[92m")
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.", error_signal, fallback_color_code="\033[93m")

    output_image_path = os.path.join(temp_dir, f"{name}.{target_format.lower()}")
    utils._emit_or_print(f">> Extracting CHD to Raw Image ({os.path.basename(output_image_path)})...", output_signal, fallback_color_code="\033[92m")
    # Assuming 'extracthd' is appropriate for a generic "raw" output from CHD.
    command = [config.TOOL_CHDMAN, 'extracthd', '-i', processing_path, '-o', output_image_path]
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_image_path) or os.path.getsize(output_image_path) == 0:
        utils._emit_or_print(f"ERROR: Output Raw Image \"{os.path.basename(output_image_path)}\" was not created or empty.", error_signal, is_error=True)
        return False
    return True

# --- GENERAL PURPOSE ARCHIVE EXTRACTION ---
def extract_archive_to_folder_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """
    Extracts a supported archive (7z, zip, rar, gz) directly to the temp_dir.
    In this context, temp_dir is treated as the final output destination by process_file
    if no specific output format is specified for moving.
    """
    utils._emit_or_print(f">> Extracting archive \"{os.path.basename(processing_path)}\" to folder \"{temp_dir}\"", output_signal, fallback_color_code="\033[92m")
    
    # utils.extract_archive handles the 7za.exe call and basic logging.
    # It extracts into the 'temp_dir' provided.
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        # Error already emitted by extract_archive or run_command
        return False
    
    # Verify that files were actually extracted into temp_dir
    # (A more robust check might be needed if archives can be empty but valid)
    if not os.listdir(temp_dir): # Check if the directory is empty after extraction
        utils._emit_or_print(f"WARNING: Archive \"{os.path.basename(processing_path)}\" was extracted, but the output folder \"{temp_dir}\" is empty.", error_signal, fallback_color_code="\033[93m")
        # Depending on desired behavior, this could be an error (return False)
        # For now, let's consider it a success if 7za ran without error, even if output is empty.
    
    utils._emit_or_print(f"Archive \"{os.path.basename(processing_path)}\" extracted successfully to \"{temp_dir}\".", output_signal, fallback_color_code="\033[92m")
    return True


# --- ARCHIVE TO FORMAT CONVERSIONS (These use the helper) ---
def convert_archive_to_7z_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None):
    """Extracts ZIP/RAR and recompresses content to 7z."""
    # This function is specific: it re-archives, so it doesn't use _handle_archive_input_for_compression
    # It extracts everything to temp_dir, then re-compresses temp_dir's content.
    
    # Ensure temp_dir is clean or a unique subdir for this operation if multiple archives are processed sequentially by one job.
    # For a single file process_file call, temp_dir is unique.
    
    utils._emit_or_print(f">> Converting archive {os.path.basename(processing_path)} to 7Z format...", output_signal, fallback_color_code="\033[96m")

    # Step 1: Extract the source archive (zip/rar) into temp_dir
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        utils._emit_or_print(f"Failed to extract source archive {os.path.basename(processing_path)}.", error_signal, is_error=True)
        return False
    
    # Step 2: Compress the extracted content from temp_dir to a new .7z file (also in temp_dir for now)
    utils._emit_or_print(">> Re-compressing extracted content to 7Z...", output_signal, fallback_color_code="\033[92m")
    output_7z_path = os.path.join(temp_dir, f"{name}.7z") # The new 7z archive
    
    # Ensure we don't try to add the source archive itself if it was copied to temp_dir
    # And don't add the target output_7z_path to itself.
    # The content_specifier '.' means all files in cwd (which will be temp_dir).
    # We need to be careful if the original processing_path (archive) was copied into temp_dir.
    # Let's list contents of temp_dir and exclude the original archive if COPY_LOCALLY was true
    # and the output 7z file itself.

    items_to_archive = [os.path.join(temp_dir, item) for item in os.listdir(temp_dir)]
    # Filter out the target 7z file to prevent recursion
    items_to_archive = [item for item in items_to_archive if os.path.basename(item) != f"{name}.7z"]
    # If original archive was copied locally, it might be in temp_dir.
    # However, extract_archive extracts *contents*, so original archive itself shouldn't be loose in temp_dir.

    if not items_to_archive:
        utils._emit_or_print("No content found after extraction to re-compress to 7Z.", error_signal, is_error=True)
        return False

    # Command to create 7z. Use relative paths if CWD is temp_dir.
    # To use relative paths for items, we need to run 7za with cwd=temp_dir
    # and provide just the names of items within temp_dir.
    # Or, provide full paths to items. Using '.' as content specifier with cwd=temp_dir is simplest.
    
    command = [config.TOOL_7ZA, 'a', '-t7z', '-mx9', '-md=128m', output_7z_path, '.'] # Compress current dir (temp_dir)

    if not utils.run_command(command, cwd=temp_dir, output_signal=output_signal, error_signal=error_signal):
        return False
        
    if not os.path.exists(output_7z_path) or os.path.getsize(output_7z_path) == 0:
        utils._emit_or_print(f"ERROR: Output 7Z \"{os.path.basename(output_7z_path)}\" not created or empty.", error_signal, is_error=True)
        return False
        
    if config.VALIDATE_FILE:
        utils._emit_or_print(">> Validating new 7Z archive...", output_signal, fallback_color_code="\033[92m")
        if not utils.run_command([config.TOOL_7ZA, 't', output_7z_path], output_signal=output_signal, error_signal=error_signal):
            utils._emit_or_print(f"Validation failed for \"{os.path.basename(output_7z_path)}\".", error_signal, is_error=True)
            return False 
        else:
            utils._emit_or_print(">> Validation passed.", output_signal, fallback_color_code="\033[92m")
    return True
