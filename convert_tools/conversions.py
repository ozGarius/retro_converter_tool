# -*- coding: utf-8 -*-
# /convert_tools/conversions.py (TypeError Fix & Parameter Alignment)

import os
import glob
import shutil
import config
import utils


# --- Internal Helper for Archive Handling in Compression Routines ---
def _handle_archive_input_for_compression(processing_path, base_temp_dir,
                                          supported_media_extensions, output_signal=None, error_signal=None):
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

    archive_extensions = ['.7z', '.zip', '.rar', '.gz']

    if ext_lower in archive_extensions:
        utils._emit_or_print(f">> Input '{file_name}' is an archive. Attempting extraction...", output_signal, fallback_color_code="cyan")

        archive_extract_sub_temp_dir = os.path.join(base_temp_dir, f"{name_part}_extracted_content")
        if not os.path.exists(archive_extract_sub_temp_dir):
            try:
                os.makedirs(archive_extract_sub_temp_dir)
            except OSError as e:
                utils._emit_or_print(f"ERROR: Could not create sub-temp dir for archive extraction: {e}", error_signal, is_error=True)
                return processing_path, None

        if not utils.extract_archive(processing_path, archive_extract_sub_temp_dir, output_signal, error_signal):
            utils._emit_or_print(f"ERROR: Failed to extract archive '{file_name}'.", error_signal, is_error=True)
            try:
                shutil.rmtree(archive_extract_sub_temp_dir)
            except OSError:
                pass
            return processing_path, None

        utils._emit_or_print(f">> Searching for media files ({', '.join(supported_media_extensions)}) in extracted content...", output_signal, fallback_color_code="cyan")

        found_media_file = None
        for media_ext in supported_media_extensions:
            root_files = glob.glob(os.path.join(archive_extract_sub_temp_dir, f"*{media_ext}"))
            if root_files:
                found_media_file = root_files[0]
                break
            recursive_files = glob.glob(os.path.join(archive_extract_sub_temp_dir, '**', f"*{media_ext}"), recursive=True)
            if recursive_files:
                found_media_file = recursive_files[0]
                break

        if found_media_file:
            utils._emit_or_print(f"Found media file for compression: {os.path.basename(found_media_file)}", output_signal, fallback_color_code="green")
            return found_media_file, archive_extract_sub_temp_dir
        else:
            utils._emit_or_print(f"ERROR: No supported media files ({', '.join(supported_media_extensions)}) found in extracted archive '{file_name}'.", error_signal, is_error=True)
            return processing_path, archive_extract_sub_temp_dir
    else:
        return processing_path, None


# --- COMPRESSION ROUTINES ---
def compress_discimage_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Converts CD-like disc images (ISO, CUE, IMG, TOC) or archives containing them to CHD format.

    Args:
        processing_path (str): Path to the disc image file or archive.
        temp_dir (str): Temporary directory for intermediate files.
        name (str): Base name for the output CHD file (without extension).
        output_signal: Signal object for informational messages.  Defaults to None.
        error_signal: Signal object for error messages. Defaults to None.
        **kwargs: Additional keyword arguments (currently unused).

    Returns:
        bool: True if the conversion was successful, False otherwise.
    """
    utils._emit_or_print(f">> Starting CD Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")

    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso', '.cue', '.img', '.toc'], output_signal, error_signal
    )

    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(f">> Compressing to CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createcd', '-i', actual_media_path, '-o', output_chd_path]

    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)

    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)

    if not success:
        return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_dvdimage_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Compresses a DVD image (.iso or .img) to a CHD format.

    Args:
        processing_path (str): Path to the DVD image file.
        temp_dir (str): Temporary directory for intermediate files.
        name (str): Base name for the output CHD file (without extension).
        output_signal (Signal, optional): Signal object for informational messages. Defaults to None.
        error_signal (Signal, optional): Signal object for error messages. Defaults to None.
        **kwargs: Additional keyword arguments (not used).

    Returns:
        bool: True if the compression was successful, False otherwise.
    """
    utils._emit_or_print(f">> Starting DVD Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso', '.img'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False
    utils._emit_or_print(f">> Compressing to DVD CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createdvd', '-i', actual_media_path, '-o', output_chd_path]
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success:
        return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_dolphin_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="rvz", **kwargs):
    """Compresses Dolphin game images (.iso, .gcm, .rvz, .gcz, .wbfs, .ciso, .wad) using DolphinTool.

    Args:
        processing_path (str): Path to the Dolphin game image file or archive.
        temp_dir (str): Temporary directory for intermediate files.
        name (str): Base name for the output compressed file (without extension).
        output_signal (Signal, optional): Signal object for informational messages. Defaults to None.
        error_signal (Signal, optional): Signal object for error messages. Defaults to None.
        target_format_from_worker (str, optional): The desired compression format ('rvz', 'wbfs', 'gcz', or 'wia'). Defaults to "rvz".
        **kwargs: Additional keyword arguments (currently unused).

    Returns:
        bool: True if the compression was successful, False otherwise.
    """
    utils._emit_or_print(f">> Starting Dolphin Compression to {target_format_from_worker.upper()} for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso', '.gcm', '.rvz', '.gcz', '.wbfs', '.ciso', '.wad'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    output_ext = target_format_from_worker.lower()
    # tool_format_param = 'wbfs' if output_ext == 'via' else output_ext
    # if output_ext == 'via':
    #     utils._emit_or_print("   (Note: VIA output uses WBFS format with DolphinTool)", output_signal, fallback_color_code="yellow")

    utils._emit_or_print(f">> Compressing to {output_ext.upper()}: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_file_path = os.path.join(temp_dir, f"{name}.{output_ext}")
    command = [config.TOOL_DOLPHINTOOL, 'convert', f'--input={actual_media_path}', f'--output={output_file_path}', f'--format={output_ext}']
    if output_ext == 'rvz':
        command.extend(['--compression=lzma2', '--block_size=2097152', f'--compression_level={config.DOLPHIN_COMPRESS_LEVEL}'])
    elif output_ext == 'wia':
        command.extend(['--compression=lzma2', '--block_size=2097152', f'--compression_level={config.DOLPHIN_COMPRESS_LEVEL}'])
    elif output_ext == 'gcz':
        command.extend(['--block_size=131072'])
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success:
        return False
    if not os.path.exists(output_file_path) or os.path.getsize(output_file_path) == 0:
        utils._emit_or_print(f"ERROR: Output {output_ext.upper()} \"{os.path.basename(output_file_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_harddisk_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Compresses a hard disk image (.img, .raw, .bin, .iso) to a CHD format.

    Args:
        processing_path (str): Path to the hard disk image file.
        temp_dir (str): Temporary directory for intermediate files.
        name (str): Base name for the output CHD file (without extension).
        output_signal (Signal, optional): Signal object for informational messages. Defaults to None.
        error_signal (Signal, optional): Signal object for error messages. Defaults to None.
        **kwargs: Additional keyword arguments (not used).

    Returns:
        bool: True if the compression was successful, False otherwise.
    """
    utils._emit_or_print(f">> Starting Hard Disk Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.img', '.raw', '.bin', '.iso'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False
    utils._emit_or_print(f">> Compressing to Hard Disk CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createhd', '-i', actual_media_path, '-o', output_chd_path]
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success:
        return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_laserdisc_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Compresses a LaserDisc image (.cue, .ld) to a CHD format.

    Args:
        processing_path (str): Path to the LaserDisc image file or archive.
        temp_dir (str): Temporary directory for intermediate files.
        name (str): Base name for the output CHD file (without extension).
        output_signal (Signal, optional): Signal object for informational messages. Defaults to None.
        error_signal (Signal, optional): Signal object for error messages. Defaults to None.
        **kwargs: Additional keyword arguments (not used).

    Returns:
        bool: True if the compression was successful, False otherwise.
    """
    utils._emit_or_print(f">> Starting LaserDisc Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.cue', '.ld'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False
    utils._emit_or_print(f">> Compressing to LaserDisc CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createld', '-i', actual_media_path, '-o', output_chd_path]
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success:
        return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_raw_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Compresses a raw image (.img, .raw, .bin) to a CHD format.

    Args:
        processing_path (str): Path to the raw image file.
        temp_dir (str): Temporary directory for intermediate files.
        name (str): Base name for the output CHD file (without extension).
        output_signal (Signal, optional): Signal object for informational messages. Defaults to None.
        error_signal (Signal, optional): Signal object for error messages. Defaults to None.
        **kwargs: Additional keyword arguments (not used).

    Returns:
        bool: True if the compression was successful, False otherwise.
    """
    utils._emit_or_print(f">> Starting Raw Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.img', '.raw', '.bin'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False
    utils._emit_or_print(f">> Compressing Raw Image to CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createhd', '-i', actual_media_path, '-o', output_chd_path]
    success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success:
        return False
    if not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_iso_to_cso_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Compresses an ISO image to a CSO format.

    Args:
        processing_path (str): Path to the ISO image file.
        temp_dir (str): Temporary directory for intermediate files.
        name (str): Base name for the output CSO file (without extension).
        output_signal (Signal, optional): Signal object for informational messages. Defaults to None.
        error_signal (Signal, optional): Signal object for error messages. Defaults to None.
        **kwargs: Additional keyword arguments (not used).

    Returns:
        bool: True if the compression was successful, False otherwise.
    """
    utils._emit_or_print(f">> Starting ISO to CSO for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False
    utils._emit_or_print(f">> Compressing ISO to CSO: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_cso_path = os.path.join(temp_dir, f"{name}.cso")
    command = [config.TOOL_MAXCSO, actual_media_path, '--output', output_cso_path]
    maxcso_success = utils.run_command(command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not maxcso_success:
        if not os.path.exists(output_cso_path):
            utils._emit_or_print("ERROR: maxcso compression failed and output CSO missing.", error_signal, is_error=True)
            return False
        else:
            utils._emit_or_print("WARNING: maxcso returned an error code, but output CSO exists. Assuming success.", error_signal, fallback_color_code="yellow")
    if not os.path.exists(output_cso_path) or os.path.getsize(output_cso_path) == 0:
        utils._emit_or_print(f"ERROR: Output CSO \"{os.path.basename(output_cso_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


# --- EXTRACTION ROUTINES ---
def extract_chd_to_cd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="cue", **kwargs):
    """Extracts a CHD (CD) to CUE/BIN, TOC/BIN, GDI, or ISO.  This process decompresses the CHD archive and outputs the original CD image in one of several formats. The format is determined by the user's selection in the GUI.

    Args:
        processing_path (str): Path to the input CHD file.
        temp_dir (str): Temporary directory for intermediate files.
        name (str): Base name for output files (without extension).
        output_signal (SignalHandler, optional): Signal handler for output messages. Defaults to None.
        error_signal (SignalHandler, optional): Signal handler for error messages. Defaults to None.
        target_format_from_worker (str, optional): The desired output format ("cue", "toc", "gdi", or "iso").  Defaults to "cue".

    Returns:
        bool: True if the extraction was successful, False otherwise.
    """
    utils._emit_or_print(f">> Verifying CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="green")
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.", error_signal, fallback_color_code="yellow")

    # Use the target_format_from_worker passed from process_file (which gets it from GUI selection)
    actual_target_format = target_format_from_worker.lower()
    output_base_name = os.path.join(temp_dir, f"{name}.{actual_target_format}")
    utils._emit_or_print(f">> Extracting CHD to {actual_target_format.upper()} ({os.path.basename(output_base_name)})...", output_signal, fallback_color_code="green")

    command = [config.TOOL_CHDMAN, 'extractcd', '-i', processing_path, '-o', output_base_name]
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False

    if not os.path.exists(output_base_name) or os.path.getsize(output_base_name) == 0:
        utils._emit_or_print(f"ERROR: Output {actual_target_format.upper()} file \"{os.path.basename(output_base_name)}\" was not created or is empty.", error_signal, is_error=True)
        return False

    if actual_target_format == "cue":
        bin_files = glob.glob(os.path.join(temp_dir, f"{name}*.bin"))
        if not bin_files or not any(os.path.getsize(f) > 0 for f in bin_files):
            utils._emit_or_print(f"ERROR: Associated BIN file(s) for CUE sheet '{name}.cue' not found or empty.", error_signal, is_error=True)
            return False
    elif actual_target_format == "gdi":
        track_files = glob.glob(os.path.join(temp_dir, f"{name}*.bin")) + glob.glob(os.path.join(temp_dir, f"{name}*.raw"))
        if not track_files or not any(os.path.getsize(f) > 0 for f in track_files):
            utils._emit_or_print(f"ERROR: Associated track files (.bin/.raw) for GDI '{name}.gdi' not found or empty.", error_signal, is_error=True)
            return False
    return True


def extract_chd_to_dvd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Extracts a CHD (DVD) to DVD ISO.

    Args:
        processing_path (str): The path to the CHD file.
        temp_dir (str): The temporary directory for intermediate files.
        name (str): The base name of the output file (without extension).
        output_signal (Signal, optional): A signal object for emitting messages. Defaults to None.
        error_signal (Signal, optional): A signal object for emitting error messages. Defaults to None.
        **kwargs: Additional keyword arguments (not used).

    Returns:
        bool: True if the extraction was successful, False otherwise.
    """
    utils._emit_or_print(f">> Verifying CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="green")
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.", error_signal, fallback_color_code="yellow")
    output_iso_path = os.path.join(temp_dir, f"{name}.iso")
    utils._emit_or_print(f">> Extracting CHD to DVD ISO ({os.path.basename(output_iso_path)})...", output_signal, fallback_color_code="green")
    command = [config.TOOL_CHDMAN, 'extractdvd', '-i', processing_path, '-o', output_iso_path]
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_iso_path) or os.path.getsize(output_iso_path) == 0:
        utils._emit_or_print(f"ERROR: Output DVD ISO file \"{os.path.basename(output_iso_path)}\" was not created or is empty.", error_signal, is_error=True)
        return False
    return True


def extract_dolphin_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="iso", **kwargs):
    """Extracts a Dolphin (GC) ISO to another format using DolphinTool.

    Args:
        processing_path (str): Path to the input Dolphin ISO file.
        temp_dir (str): Temporary directory for intermediate files.
        name (str): Base name of the output file (without extension).
        output_signal (obj, optional): Output signal object for progress reporting. Defaults to None.
        error_signal (obj, optional): Error signal object for error reporting. Defaults to None.
        target_format_from_worker (str, optional): The desired output format ("iso", "cue", "gdi", etc.). Defaults to "iso".

    Returns:
        bool: True if the extraction was successful, False otherwise.
    """
    actual_target_format = target_format_from_worker.lower()
    utils._emit_or_print(f">> Converting {os.path.splitext(processing_path)[1].upper()} to {actual_target_format.upper()}: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="green")
    output_file_path = os.path.join(temp_dir, f"{name}.{actual_target_format}")
    command = [config.TOOL_DOLPHINTOOL, 'convert', f'--input={processing_path}', f'--output={output_file_path}', f'--format={actual_target_format}']
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_file_path) or os.path.getsize(output_file_path) == 0:
        utils._emit_or_print(f"ERROR: Output {actual_target_format.upper()} \"{os.path.basename(output_file_path)}\" not created or is empty.", error_signal, is_error=True)
        return False
    return True


def extract_chd_to_harddisk_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="img", **kwargs):
    """Extracts a CHD to a hard disk image format (IMG).

    Args:
        processing_path (str): The path to the CHD file.
        temp_dir (str): The temporary directory for intermediate files.
        name (str): The base name of the output file (without extension).
        output_signal (obj, optional):  An object used for emitting status messages. Defaults to None.
        error_signal (obj, optional): An object used for emitting error messages. Defaults to None.
        target_format_from_worker (str, optional): The desired output format ("img"). Defaults to "img".

    Returns:
        bool: True if the extraction was successful, False otherwise.
    """
    utils._emit_or_print(f">> Verifying CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="green")
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.", error_signal, fallback_color_code="yellow")
    actual_target_format = target_format_from_worker.lower()
    output_image_path = os.path.join(temp_dir, f"{name}.{actual_target_format}")
    utils._emit_or_print(f">> Extracting CHD to Hard Disk Image ({os.path.basename(output_image_path)})...", output_signal, fallback_color_code="green")
    command = [config.TOOL_CHDMAN, 'extracthd', '-i', processing_path, '-o', output_image_path]
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_image_path) or os.path.getsize(output_image_path) == 0:
        utils._emit_or_print(f"ERROR: Output Image \"{os.path.basename(output_image_path)}\" was not created or empty.", error_signal, is_error=True)
        return False
    return True


def extract_chd_to_laserdisc_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="raw", **kwargs):
    """Extracts a CHD (CD) to LaserDisc format.

    Args:
        processing_path (str): The path to the CHD file.
        temp_dir (str): The temporary directory for intermediate files.
        name (str): The base name of the output files (without extension).
        output_signal (object, optional): An object for emitting output messages. Defaults to None.
        error_signal (object, optional): An object for emitting error messages. Defaults to None.
        target_format_from_worker (str, optional): The desired target format. Defaults to "raw".
    Returns:
        bool: True if the extraction was successful, False otherwise.
    """
    utils._emit_or_print(f">> Extracting CHD to LaserDisc ({name}.raw)...", output_signal, fallback_color_code="green")

    command = [config.TOOL_CHDMAN, 'extractld', '-i', processing_path, '-o', os.path.join(temp_dir, f"{name}.raw")]
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False

    output_file_path = os.path.join(temp_dir, f"{name}.raw")
    if not os.path.exists(output_file_path) or os.path.getsize(output_file_path) == 0:
        utils._emit_or_print(f"ERROR: Output LaserDisc file \"{os.path.basename(output_file_path)}\" was not created or is empty.", error_signal, is_error=True)
        return False

    return True


def extract_chd_to_raw_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="raw", **kwargs):
    """Extracts a CHD file to a raw image format.

    Args:
        processing_path (str): The path to the CHD file.
        temp_dir (str): The temporary directory for storing intermediate files.
        name (str): The base name of the output file (without extension).
        output_signal (Signal): A signal object for sending output messages.
        error_signal (Signal): A signal object for sending error messages.
        target_format_from_worker (str, optional): The desired target format. Defaults to "raw".
        **kwargs: Additional keyword arguments (not used).

    Returns:
        bool: True if the extraction was successful, False otherwise.
    """
    utils._emit_or_print(f">> Verifying CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="green")
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.", error_signal, fallback_color_code="yellow")
    if not utils.run_command([config.TOOL_CHDMAN, 'verify', '-i', processing_path], output_signal=output_signal, error_signal=error_signal):
        return False
    actual_target_format = target_format_from_worker.lower()
    output_image_path = os.path.join(temp_dir, f"{name}.{actual_target_format}")
    utils._emit_or_print(f">> Extracting CHD to Raw Image ({os.path.basename(output_image_path)})...", output_signal, fallback_color_code="green")
    command = [config.TOOL_CHDMAN, 'extracthd', '-i', processing_path, '-o', output_image_path]
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_image_path) or os.path.getsize(output_image_path) == 0:
        utils._emit_or_print(f"ERROR: Output Raw Image \"{os.path.basename(output_image_path)}\" was not created or empty.", error_signal, is_error=True)
        return False
    return True


# --- GENERAL PURPOSE ARCHIVE EXTRACTION ---
def extract_archive_to_folder_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Extracts an archive file (e.g., zip, 7z, rar) to a specified folder.

    Args:
        processing_path (str): The path to the archive file.
        temp_dir (str): The temporary directory where the contents will be extracted.
        name (str): A name used for logging and potential output filenames.  Not directly used in extraction.
        output_signal (callable, optional): A function to emit log messages. Defaults to None.
        error_signal (callable, optional): A function to signal errors. Defaults to None.
        **kwargs: Additional keyword arguments (not currently used).

    Returns:
        bool: True if the extraction was successful, False otherwise.
    """
    utils._emit_or_print(f">> Extracting archive \"{os.path.basename(processing_path)}\" to folder \"{temp_dir}\"", output_signal, fallback_color_code="green")
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        return False
    if not os.listdir(temp_dir):
        utils._emit_or_print(f"WARNING: Archive \"{os.path.basename(processing_path)}\" extracted, but output folder \"{temp_dir}\" is empty.", error_signal, fallback_color_code="yellow")
    utils._emit_or_print(f"Archive \"{os.path.basename(processing_path)}\" extracted successfully to \"{temp_dir}\".", output_signal, fallback_color_code="green")
    return True


# --- ARCHIVE TO FORMAT CONVERSIONS ---
def convert_archive_to_7z_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Converts an archive file to the 7Z format.

    Args:
        processing_path (str): The path to the input archive file.
        temp_dir (str): The temporary directory for intermediate files.
        name (str): The base name of the archive (used for output filenames).
        output_signal (Signal, optional): A signal object for emitting messages. Defaults to None.
        error_signal (Signal, optional): A signal object for emitting error messages. Defaults to None.
        **kwargs: Additional keyword arguments (not used in this function).

    Returns:
        bool: True if the conversion was successful, False otherwise.
    """
    utils._emit_or_print(f">> Converting archive {os.path.basename(processing_path)} to 7Z format...", output_signal, fallback_color_code="cyan")
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        utils._emit_or_print(f"Failed to extract source archive {os.path.basename(processing_path)}.", error_signal, is_error=True)
        return False
    utils._emit_or_print(">> Re-compressing extracted content to 7Z...", output_signal, fallback_color_code="green")
    output_7z_path = os.path.join(temp_dir, f"{name}.7z")
    items_to_archive = [os.path.join(temp_dir, item) for item in os.listdir(temp_dir)]
    items_to_archive = [item for item in items_to_archive if os.path.basename(item) != f"{name}.7z"]
    if not items_to_archive:
        utils._emit_or_print("No content found after extraction to re-compress to 7Z.", error_signal, is_error=True)
        return False
    command = [config.TOOL_7ZA, 'a', '-t7z', '-mx9', '-md=128m', output_7z_path, '.']
    if not utils.run_command(command, cwd=temp_dir, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_7z_path) or os.path.getsize(output_7z_path) == 0:
        utils._emit_or_print(f"ERROR: Output 7Z \"{os.path.basename(output_7z_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    if config.VALIDATE_FILE:
        utils._emit_or_print(">> Validating new 7Z archive...", output_signal, fallback_color_code="green")
        if not utils.run_command([config.TOOL_7ZA, 't', output_7z_path], output_signal=output_signal, error_signal=error_signal):
            utils._emit_or_print(f"Validation failed for \"{os.path.basename(output_7z_path)}\".", error_signal, is_error=True)
            return False
        else:
            utils._emit_or_print(">> Validation passed.", output_signal, fallback_color_code="green")
    return True
