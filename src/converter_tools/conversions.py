# -*- coding: utf-8 -*-
# /converter_tools/conversions.py (Integrated with detailed settings from config.py)

import os
import glob
import shutil
import config  # Now contains all the detailed settings
import utils


# --- Internal Helper for Archive Handling in Compression Routines ---
def _handle_archive_input_for_compression(processing_path, base_temp_dir,
                                          supported_media_extensions, output_signal=None, error_signal=None):
    """
    Checks if processing_path is an archive. If so, extracts it to a sub-temp dir,
    finds the primary media file, and returns its path and the sub-temp dir path.
    Otherwise, returns the original processing_path and None for the sub-temp dir.
    """
    file_name = os.path.basename(processing_path)
    name_part, ext_part = os.path.splitext(file_name)
    ext_lower = ext_part.lower()

    archive_extensions = ['.7z', '.zip', '.rar', '.gz']

    if ext_lower in archive_extensions:
        utils._emit_or_print(
            f">> Input '{file_name}' is an archive. Attempting extraction...", output_signal, fallback_color_code="cyan")

        archive_extract_sub_temp_dir = os.path.join(
            base_temp_dir, f"{name_part}_extracted_content")
        if not os.path.exists(archive_extract_sub_temp_dir):
            try:
                os.makedirs(archive_extract_sub_temp_dir)
            except OSError as e:
                utils._emit_or_print(
                    f"ERROR: Could not create sub-temp dir for archive extraction: {e}", error_signal, is_error=True)
                return processing_path, None

        if not utils.extract_archive(processing_path, archive_extract_sub_temp_dir, output_signal, error_signal):
            utils._emit_or_print(
                f"ERROR: Failed to extract archive '{file_name}'.", error_signal, is_error=True)
            try:
                shutil.rmtree(archive_extract_sub_temp_dir)
            except OSError:
                pass
            return processing_path, None

        utils._emit_or_print(
            f">> Searching for media files ({', '.join(supported_media_extensions)}) in extracted content...", output_signal, fallback_color_code="cyan")

        found_media_file = None
        for media_ext in supported_media_extensions:
            root_files = glob.glob(os.path.join(
                archive_extract_sub_temp_dir, f"*{media_ext}"))
            if root_files:
                found_media_file = root_files[0]
                break
            recursive_files = glob.glob(os.path.join(
                archive_extract_sub_temp_dir, '**', f"*{media_ext}"), recursive=True)
            if recursive_files:
                found_media_file = recursive_files[0]
                break

        if found_media_file:
            utils._emit_or_print(
                f"Found media file for compression: {os.path.basename(found_media_file)}", output_signal, fallback_color_code="green")
            return found_media_file, archive_extract_sub_temp_dir
        else:
            utils._emit_or_print(
                f"ERROR: No supported media files ({', '.join(supported_media_extensions)}) found in extracted archive '{file_name}'.", error_signal, is_error=True)
            return processing_path, archive_extract_sub_temp_dir
    else:
        return processing_path, None


def _add_chdman_common_args(command_list):
    """Helper to add common CHDMAN arguments like numprocessors."""
    if config.CHDMAN_NUM_PROCESSORS_MODE == "manual" and config.CHDMAN_NUM_PROCESSORS_MANUAL > 0:
        command_list.extend(
            ["--numprocessors", str(config.CHDMAN_NUM_PROCESSORS_MANUAL)])


# --- COMPRESSION ROUTINES ---
def compress_discimage_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    utils._emit_or_print(
        f">> Starting CD Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, [
            '.iso', '.cue', '.img', '.toc', '.gdi'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    # Verify actual_media_path before calling the tool
    if not os.path.isfile(actual_media_path):
        utils._emit_or_print(
            f"ERROR: Input media file for CHDMAN (CD) not found at: {actual_media_path}", error_signal, is_error=True)
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(
        f">> Compressing to CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createcd', '-i',
               actual_media_path, '-o', output_chd_path]

    _add_chdman_common_args(command)
    if config.CHDMAN_CD_USE_CUSTOM_HUNKS and config.CHDMAN_CD_HUNKS > 0:
        command.extend(["--hunksize", str(config.CHDMAN_CD_HUNKS)])
    if config.CHDMAN_CD_USE_CUSTOM_COMPRESSION and config.CHDMAN_CD_COMPRESSION_TYPES:
        command.extend(["--compression", config.CHDMAN_CD_COMPRESSION_TYPES])

    success = utils.run_command(
        command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success or not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_dvdimage_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    utils._emit_or_print(
        f">> Starting DVD Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, [
            '.iso', '.img'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    if not os.path.isfile(actual_media_path):
        utils._emit_or_print(
            f"ERROR: Input media file for CHDMAN (DVD) not found at: {actual_media_path}", error_signal, is_error=True)
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(
        f">> Compressing to DVD CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createdvd', '-i',
               actual_media_path, '-o', output_chd_path]

    _add_chdman_common_args(command)
    if config.CHDMAN_DVD_USE_CUSTOM_HUNKS and config.CHDMAN_DVD_HUNKS > 0:
        command.extend(["--hunksize", str(config.CHDMAN_DVD_HUNKS)])
    if config.CHDMAN_DVD_USE_CUSTOM_COMPRESSION and config.CHDMAN_DVD_COMPRESSION_TYPES:
        command.extend(["--compression", config.CHDMAN_DVD_COMPRESSION_TYPES])

    success = utils.run_command(
        command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success or not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_dolphin_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="rvz", **kwargs):
    utils._emit_or_print(
        f">> Starting Dolphin Compression to {target_format_from_worker.upper()} for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso', '.gcm', '.rvz', '.gcz',
                                    '.wbfs', '.ciso', '.wad'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    # ** ADDED CHECK **
    # Verify that the actual_media_path (which will be the input to DolphinTool) exists before proceeding
    if not os.path.isfile(actual_media_path):
        utils._emit_or_print(
            f"ERROR: Input media file for DolphinTool not found at: {actual_media_path}", error_signal, is_error=True)
        utils._emit_or_print(
            f"       (Original input was: {processing_path})", error_signal, is_error=True)
        if sub_temp_dir:  # Cleanup archive extraction temp if it exists
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    output_ext = target_format_from_worker.lower()
    utils._emit_or_print(
        f">> Compressing to {output_ext.upper()}: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_file_path = os.path.join(temp_dir, f"{name}.{output_ext}")
    command = [config.TOOL_DOLPHINTOOL, 'convert',
               f'--input={actual_media_path}', f'--output={output_file_path}', f'--format={output_ext}']

    if output_ext == 'rvz':
        if config.DOLPHINTOOL_RVZ_COMPRESSION_TYPE and config.DOLPHINTOOL_RVZ_COMPRESSION_TYPE != "none":
            command.extend(
                ['--compression', config.DOLPHINTOOL_RVZ_COMPRESSION_TYPE])
            if config.DOLPHINTOOL_RVZ_COMPRESSION_LEVEL > 0:
                command.extend(
                    [f'--compression_level={config.DOLPHINTOOL_RVZ_COMPRESSION_LEVEL}'])
        if config.DOLPHINTOOL_RVZ_BLOCKSIZE > 0:
            command.extend(
                [f'--block_size={config.DOLPHINTOOL_RVZ_BLOCKSIZE}'])
    elif output_ext == 'wia':
        if config.DOLPHINTOOL_WIA_COMPRESSION_TYPE and config.DOLPHINTOOL_WIA_COMPRESSION_TYPE != "none":
            command.extend(
                ['--compression', config.DOLPHINTOOL_WIA_COMPRESSION_TYPE])
            if config.DOLPHINTOOL_WIA_COMPRESSION_TYPE not in ["none", "purge"] and config.DOLPHINTOOL_WIA_COMPRESSION_LEVEL > 0:
                command.extend(
                    [f'--compression_level={config.DOLPHINTOOL_WIA_COMPRESSION_LEVEL}'])
    elif output_ext == 'gcz':
        if config.DOLPHINTOOL_GCZ_BLOCKSIZE > 0:
            command.extend(
                [f'--block_size={config.DOLPHINTOOL_GCZ_BLOCKSIZE}'])

    success = utils.run_command(
        command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success or not os.path.exists(output_file_path) or os.path.getsize(output_file_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output {output_ext.upper()} \"{os.path.basename(output_file_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_harddisk_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    utils._emit_or_print(
        f">> Starting Hard Disk Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.img', '.raw',
                                    '.bin', '.iso'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    if not os.path.isfile(actual_media_path):
        utils._emit_or_print(
            f"ERROR: Input media file for CHDMAN (HD) not found at: {actual_media_path}", error_signal, is_error=True)
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(
        f">> Compressing to Hard Disk CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createhd', '-i',
               actual_media_path, '-o', output_chd_path]

    _add_chdman_common_args(command)
    if config.CHDMAN_HD_USE_CUSTOM_HUNKS and config.CHDMAN_HD_HUNKS > 0:
        command.extend(["--hunksize", str(config.CHDMAN_HD_HUNKS)])
    if config.CHDMAN_HD_USE_CUSTOM_COMPRESSION and config.CHDMAN_HD_COMPRESSION_TYPES:
        command.extend(["--compression", config.CHDMAN_HD_COMPRESSION_TYPES])
    if config.CHDMAN_HD_USE_SECTOR_SIZE and config.CHDMAN_HD_SECTOR_SIZE:
        command.extend(["--sectorsize", str(config.CHDMAN_HD_SECTOR_SIZE)])
    if config.CHDMAN_HD_USE_CHS and config.CHDMAN_HD_CHS_C and config.CHDMAN_HD_CHS_H and config.CHDMAN_HD_CHS_S:
        command.extend(
            ["--chs", f"{config.CHDMAN_HD_CHS_C},{config.CHDMAN_HD_CHS_H},{config.CHDMAN_HD_CHS_S}"])
    if config.CHDMAN_HD_USE_TEMPLATE and config.CHDMAN_HD_TEMPLATE_PATH:
        command.extend(["--template", config.CHDMAN_HD_TEMPLATE_PATH])

    success = utils.run_command(
        command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success or not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_laserdisc_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    utils._emit_or_print(
        f">> Starting LaserDisc Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.cue', '.ld'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    if not os.path.isfile(actual_media_path):
        utils._emit_or_print(
            f"ERROR: Input media file for CHDMAN (LD) not found at: {actual_media_path}", error_signal, is_error=True)
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(
        f">> Compressing to LaserDisc CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createld', '-i',
               actual_media_path, '-o', output_chd_path]

    _add_chdman_common_args(command)
    if config.CHDMAN_LD_USE_CUSTOM_HUNKS and config.CHDMAN_LD_HUNKS > 0:
        command.extend(["--hunksize", str(config.CHDMAN_LD_HUNKS)])
    if config.CHDMAN_LD_USE_CUSTOM_COMPRESSION and config.CHDMAN_LD_COMPRESSION_TYPES:
        command.extend(["--compression", config.CHDMAN_LD_COMPRESSION_TYPES])
    if config.CHDMAN_LD_USE_INPUT_START_FRAME and config.CHDMAN_LD_INPUT_START_FRAME is not None:
        command.extend(
            ["--inputstartframe", str(config.CHDMAN_LD_INPUT_START_FRAME)])
    if config.CHDMAN_LD_USE_INPUT_FRAMES and config.CHDMAN_LD_INPUT_FRAMES is not None:
        command.extend(["--inputframes", str(config.CHDMAN_LD_INPUT_FRAMES)])

    success = utils.run_command(
        command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success or not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_raw_to_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    utils._emit_or_print(
        f">> Starting Raw Image to CHD for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.img', '.raw',
                                    '.bin'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    if not os.path.isfile(actual_media_path):
        utils._emit_or_print(
            f"ERROR: Input media file for CHDMAN (Raw) not found at: {actual_media_path}", error_signal, is_error=True)
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(
        f">> Compressing Raw Image to CHD: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_chd_path = os.path.join(temp_dir, f"{name}.chd")
    command = [config.TOOL_CHDMAN, 'createhd', '-i', actual_media_path,
               '-o', output_chd_path]

    _add_chdman_common_args(command)
    if config.CHDMAN_RAW_USE_CUSTOM_HUNKS and config.CHDMAN_RAW_HUNKS > 0:
        command.extend(["--hunksize", str(config.CHDMAN_RAW_HUNKS)])
    if config.CHDMAN_RAW_USE_CUSTOM_COMPRESSION and config.CHDMAN_RAW_COMPRESSION_TYPES:
        command.extend(["--compression", config.CHDMAN_RAW_COMPRESSION_TYPES])

    success = utils.run_command(
        command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not success or not os.path.exists(output_chd_path) or os.path.getsize(output_chd_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output CHD \"{os.path.basename(output_chd_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def compress_iso_to_cso_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    utils._emit_or_print(
        f">> Starting ISO to CSO for: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    actual_media_path, sub_temp_dir = _handle_archive_input_for_compression(
        processing_path, temp_dir, ['.iso'], output_signal, error_signal
    )
    if actual_media_path == processing_path and sub_temp_dir is not None and not os.path.exists(os.path.join(sub_temp_dir, os.path.basename(processing_path))):
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    if not os.path.isfile(actual_media_path):
        utils._emit_or_print(
            f"ERROR: Input media file for MAXCSO not found at: {actual_media_path}", error_signal, is_error=True)
        if sub_temp_dir:
            shutil.rmtree(sub_temp_dir, ignore_errors=True)
        return False

    utils._emit_or_print(
        f">> Compressing ISO to CSO: \"{os.path.basename(actual_media_path)}\"", output_signal, fallback_color_code="green")
    output_cso_path = os.path.join(temp_dir, f"{name}.cso")
    command = [config.TOOL_MAXCSO, actual_media_path,
               '--output', output_cso_path]

    maxcso_success = utils.run_command(
        command, output_signal=output_signal, error_signal=error_signal)
    if sub_temp_dir:
        shutil.rmtree(sub_temp_dir, ignore_errors=True)
    if not maxcso_success:
        if not os.path.exists(output_cso_path):
            utils._emit_or_print(
                "ERROR: maxcso compression failed and output CSO missing.", error_signal, is_error=True)
            return False
        else:
            utils._emit_or_print("WARNING: maxcso returned an error code, but output CSO exists. Assuming success.",
                                 error_signal, fallback_color_code="yellow")
    if not os.path.exists(output_cso_path) or os.path.getsize(output_cso_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output CSO \"{os.path.basename(output_cso_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


# --- EXTRACTION ROUTINES ---
def extract_chd_to_cd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="cue", **kwargs):
    utils._emit_or_print(
        f">> Verifying CHD (CD): \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="green")
    verify_command = [config.TOOL_CHDMAN, 'verify', '-i', processing_path]
    if config.CHDMAN_VERIFY_FIX:
        verify_command.append('--fix')
    if not utils.run_command(verify_command, output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed or found errors. Attempting extraction anyway.",
                             error_signal, fallback_color_code="yellow")

    actual_target_format = target_format_from_worker.lower()
    output_base_name = os.path.join(temp_dir, f"{name}.{actual_target_format}")
    utils._emit_or_print(
        f">> Extracting CHD to {actual_target_format.upper()} ({os.path.basename(output_base_name)})...", output_signal, fallback_color_code="green")
    command = [config.TOOL_CHDMAN, 'extractcd', '-i',
               processing_path, '-o', output_base_name]

    _add_chdman_common_args(command)

    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_base_name) or os.path.getsize(output_base_name) == 0:
        utils._emit_or_print(
            f"ERROR: Output {actual_target_format.upper()} file \"{os.path.basename(output_base_name)}\" was not created or is empty.", error_signal, is_error=True)
        return False
    if actual_target_format == "cue":
        bin_files = glob.glob(os.path.join(temp_dir, f"{name}*.bin"))
        if not bin_files or not any(os.path.getsize(f) > 0 for f in bin_files):
            utils._emit_or_print(
                f"ERROR: Associated BIN file(s) for CUE sheet '{name}.cue' not found or empty.", error_signal, is_error=True)
            return False
    elif actual_target_format == "gdi":
        track_files = glob.glob(os.path.join(
            temp_dir, f"{name}*.bin")) + glob.glob(os.path.join(temp_dir, f"{name}*.raw"))
        if not track_files or not any(os.path.getsize(f) > 0 for f in track_files):
            utils._emit_or_print(
                f"ERROR: Associated track files (.bin/.raw) for GDI '{name}.gdi' not found or empty.", error_signal, is_error=True)
            return False
    return True


def extract_chd_to_dvd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    utils._emit_or_print(
        f">> Verifying CHD (DVD): \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="green")
    verify_command = [config.TOOL_CHDMAN, 'verify', '-i', processing_path]
    if config.CHDMAN_VERIFY_FIX:
        verify_command.append('--fix')
    if not utils.run_command(verify_command, output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.",
                             error_signal, fallback_color_code="yellow")

    output_iso_path = os.path.join(temp_dir, f"{name}.iso")
    utils._emit_or_print(
        f">> Extracting CHD to DVD ISO ({os.path.basename(output_iso_path)})...", output_signal, fallback_color_code="green")
    command = [config.TOOL_CHDMAN, 'extractdvd',
               '-i', processing_path, '-o', output_iso_path]
    _add_chdman_common_args(command)
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_iso_path) or os.path.getsize(output_iso_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output DVD ISO \"{os.path.basename(output_iso_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def extract_dolphin_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="iso", **kwargs):
    actual_target_format = target_format_from_worker.lower()
    utils._emit_or_print(
        f">> Converting {os.path.splitext(processing_path)[1].upper()} to {actual_target_format.upper()}: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="green")
    output_file_path = os.path.join(temp_dir, f"{name}.{actual_target_format}")
    command = [config.TOOL_DOLPHINTOOL, 'convert',
               f'--input={processing_path}', f'--output={output_file_path}', f'--format={actual_target_format}']

    # ** ADDED CHECK **
    # Check the source path for DolphinTool extract
    if not os.path.isfile(processing_path):
        utils._emit_or_print(
            f"ERROR: Input file for DolphinTool extract not found at: {processing_path}", error_signal, is_error=True)
        return False

    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_file_path) or os.path.getsize(output_file_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output {actual_target_format.upper()} \"{os.path.basename(output_file_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def extract_chd_to_harddisk_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="img", **kwargs):
    utils._emit_or_print(
        f">> Verifying CHD (HD): \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="green")
    verify_command = [config.TOOL_CHDMAN, 'verify', '-i', processing_path]
    if config.CHDMAN_VERIFY_FIX:
        verify_command.append('--fix')
    if not utils.run_command(verify_command, output_signal=output_signal, error_signal=error_signal):
        utils._emit_or_print("WARNING: CHD verification failed. Attempting extraction anyway.",
                             error_signal, fallback_color_code="yellow")

    actual_target_format = target_format_from_worker.lower()
    output_image_path = os.path.join(
        temp_dir, f"{name}.{actual_target_format}")
    utils._emit_or_print(
        f">> Extracting CHD to Hard Disk Image ({os.path.basename(output_image_path)})...", output_signal, fallback_color_code="green")
    command = [config.TOOL_CHDMAN, 'extracthd', '-i',
               processing_path, '-o', output_image_path]
    _add_chdman_common_args(command)
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_image_path) or os.path.getsize(output_image_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output Image \"{os.path.basename(output_image_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    return True


def extract_chd_to_laserdisc_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="raw", **kwargs):
    utils._emit_or_print(
        f">> Extracting CHD to LaserDisc ({name}.{target_format_from_worker})...", output_signal, fallback_color_code="green")
    output_file_base = os.path.join(
        temp_dir, f"{name}.{target_format_from_worker}")
    command = [config.TOOL_CHDMAN, 'extractld', '-i',
               processing_path, '-o', output_file_base]
    _add_chdman_common_args(command)
    if not utils.run_command(command, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_file_base) or os.path.getsize(output_file_base) == 0:
        utils._emit_or_print(
            f"ERROR: Output LaserDisc file \"{os.path.basename(output_file_base)}\" was not created or empty.", error_signal, is_error=True)
        return False
    return True


def extract_chd_to_raw_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, target_format_from_worker="raw", **kwargs):
    return extract_chd_to_harddisk_routine(processing_path, temp_dir, name, output_signal, error_signal, target_format_from_worker=target_format_from_worker, **kwargs)


# --- GENERAL PURPOSE ARCHIVE EXTRACTION ---
def extract_archive_to_folder_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    utils._emit_or_print(
        f">> Extracting archive \"{os.path.basename(processing_path)}\" to folder \"{temp_dir}\"", output_signal, fallback_color_code="green")
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        return False
    if not os.listdir(temp_dir):
        utils._emit_or_print(
            f"WARNING: Archive \"{os.path.basename(processing_path)}\" extracted, but output folder \"{temp_dir}\" is empty.", error_signal, fallback_color_code="yellow")
    utils._emit_or_print(
        f"Archive \"{os.path.basename(processing_path)}\" extracted successfully to \"{temp_dir}\".", output_signal, fallback_color_code="green")
    return True


# --- ARCHIVE TO FORMAT CONVERSIONS ---
def convert_archive_to_7z_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    utils._emit_or_print(
        f">> Converting archive {os.path.basename(processing_path)} to 7Z format...", output_signal, fallback_color_code="cyan")
    if not utils.extract_archive(processing_path, temp_dir, output_signal, error_signal):
        utils._emit_or_print(
            f"Failed to extract source archive {os.path.basename(processing_path)}.", error_signal, is_error=True)
        return False
    utils._emit_or_print(">> Re-compressing extracted content to 7Z...",
                         output_signal, fallback_color_code="green")
    output_7z_path = os.path.join(temp_dir, f"{name}.7z")
    items_to_archive = [os.path.join(temp_dir, item)
                        for item in os.listdir(temp_dir)]
    items_to_archive = [
        item for item in items_to_archive if os.path.basename(item) != f"{name}.7z"]
    if not items_to_archive:
        utils._emit_or_print(
            "No content found after extraction to re-compress to 7Z.", error_signal, is_error=True)
        return False
    command = [config.TOOL_7ZA, 'a', '-t7z', '-mx9', '-md=128m',
               output_7z_path, '.']
    if not utils.run_command(command, cwd=temp_dir, output_signal=output_signal, error_signal=error_signal):
        return False
    if not os.path.exists(output_7z_path) or os.path.getsize(output_7z_path) == 0:
        utils._emit_or_print(
            f"ERROR: Output 7Z \"{os.path.basename(output_7z_path)}\" not created or empty.", error_signal, is_error=True)
        return False
    if config.VALIDATE_FILE:
        utils._emit_or_print(">> Validating new 7Z archive...",
                             output_signal, fallback_color_code="green")
        if not utils.run_command([config.TOOL_7ZA, 't', output_7z_path], output_signal=output_signal, error_signal=error_signal):
            utils._emit_or_print(
                f"Validation failed for \"{os.path.basename(output_7z_path)}\".", error_signal, is_error=True)
            return False
        else:
            utils._emit_or_print(">> Validation passed.",
                                 output_signal, fallback_color_code="green")
    return True


# --- NEW INFO/VERIFY ROUTINES ---
def get_chd_info_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Gets information from a CHD file using 'chdman info'."""
    utils._emit_or_print(
        f">> Getting info for CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    command = [config.TOOL_CHDMAN, 'info', '-i', processing_path]

    success = utils.run_command(
        command, output_signal=output_signal, error_signal=error_signal)
    if not success:
        utils._emit_or_print(
            f"ERROR: Failed to get info for CHD \"{os.path.basename(processing_path)}\".", error_signal, is_error=True)
        return False
    utils._emit_or_print(
        f"Successfully retrieved info for \"{os.path.basename(processing_path)}\". Output is in the log.", output_signal, fallback_color_code="green")
    return True


def verify_chd_routine(processing_path, temp_dir, name, output_signal=None, error_signal=None, **kwargs):
    """Verifies a CHD file using 'chdman verify', with an option to fix."""
    utils._emit_or_print(
        f">> Verifying CHD: \"{os.path.basename(processing_path)}\"", output_signal, fallback_color_code="cyan")
    command = [config.TOOL_CHDMAN, 'verify', '-i', processing_path]
    if config.CHDMAN_VERIFY_FIX:
        command.append('--fix')
        utils._emit_or_print("   Attempting to fix errors if found (--fix enabled).",
                             output_signal, fallback_color_code="yellow")

    success = utils.run_command(
        command, output_signal=output_signal, error_signal=error_signal)
    if success:
        utils._emit_or_print(
            f"CHD \"{os.path.basename(processing_path)}\" verified successfully.", output_signal, fallback_color_code="green")
    else:
        utils._emit_or_print(
            f"ERROR: CHD \"{os.path.basename(processing_path)}\" verification failed or found errors. Check log.", error_signal, is_error=True)
    return success
