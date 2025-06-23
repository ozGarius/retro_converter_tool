# src/converter_tools/worker_process.py

import os
import sys
import traceback

# Project modules
from src.converter_tools import config
from src.converter_tools import utils
from src.converter_tools import conversions

try:
    import send2trash
except ImportError:
    send2trash = None

# Number of distinct stages reported by utils.process_file for progress tracking.
# This might need to be passed or made more dynamic if it varies by job type
# and utils.process_file doesn't internally know it.
# For now, keeping it as it was in gui_main_window.
N_STAGES_PER_FILE = 3


def process_worker_task(job_queue, results_queue):
    """
    This function is run by each process in the ProcessPoolExecutor.
    It waits for jobs on the job_queue, processes them, and puts results on the results_queue.
    """
    # config.initialize_settings() # Settings are now restored from shared dict per job

    while True:
        try:
            job_payload = job_queue.get()
            if job_payload is None:  # Sentinel value to stop the worker
                # print(f"Worker {os.getpid()} received sentinel. Exiting.") # DEBUG
                break

            job_id = job_payload["job_id"]
            original_file_path = job_payload["file_path"]
            conversion_func_name = job_payload["conversion_func_name"]
            output_folder_path_final_dest = job_payload["output_folder_path"]
            overwrite_files = job_payload["overwrite_files"]
            selected_primary_output_ext = job_payload["selected_primary_output_ext"]
            selected_secondary_output_ext = job_payload["selected_secondary_output_ext"]
            is_multi_file_job_type = job_payload.get("is_multi_file_job_type", False)

            job_temp_dir = None # Initialize

            # Restore settings in this worker process's global config.settings object
            try:
                shared_settings_dict = job_payload.get("config_settings_dict", {})
                if shared_settings_dict: # Ensure there are settings to restore
                    config.settings.restore_from_shared(shared_settings_dict)
                # else: # Log if no settings were passed, though this might be normal for some setups
                    # print(f"Worker {os.getpid()} for job {job_id}: No shared settings provided in payload.")
            except Exception as e_settings:
                # print(f"Worker {os.getpid()} job {job_id}: Failed to restore settings: {e_settings}") # DEBUG
                results_queue.put({"job_id": job_id, "type": "error_update", "data": {"message": f"Worker process failed to restore settings: {e_settings}"}})
                results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": False, "message": "Settings restoration failure"}})
                continue


            current_file_name = os.path.basename(original_file_path)
            results_queue.put({"job_id": job_id, "type": "job_started", "data": {"filename": current_file_name, "total_stages": N_STAGES_PER_FILE}})

            def send_output_update_worker(message):
                results_queue.put({"job_id": job_id, "type": "output_update", "data": {"message": message}})

            def send_error_update_worker(message, is_error=True): # is_error matches utils.emit_or_print, but not strictly used here
                results_queue.put({"job_id": job_id, "type": "error_update", "data": {"message": message}})

            job_temp_dir = utils.create_temp_dir(original_file_path, output_signal=send_output_update_worker, error_signal=send_error_update_worker)
            if not job_temp_dir:
                send_error_update_worker(f"Failed to create temp directory for job {job_id}.")
                results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": False, "message": "Temp dir creation failed"}})
                continue

            path_to_process_in_temp = utils.stage_job_files(
                original_file_path,
                job_temp_dir,
                is_multi_file_job_type,
                config.settings.COPY_LOCALLY,
                output_signal=send_output_update_worker,
                error_signal=send_error_update_worker
            )

            if not path_to_process_in_temp:
                send_error_update_worker(f"Failed to stage files for job {job_id} ({current_file_name}).")
                results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": False, "message": "File staging failed"}})
                if job_temp_dir: utils.cleanup(job_temp_dir, output_signal=send_output_update_worker, error_signal=send_error_update_worker)
                continue

            cumulative_stages_done_for_file = 0
            def stage_reporter_for_process_file(stage_description):
                nonlocal cumulative_stages_done_for_file
                cumulative_stages_done_for_file +=1
                results_queue.put({
                    "job_id": job_id, "type": "status_update",
                    "data": {
                        "description": stage_description,
                        "current_step": cumulative_stages_done_for_file,
                        "total_steps": N_STAGES_PER_FILE # N_STAGES_PER_FILE should be accessible here
                    }
                })
                file_percentage = int((cumulative_stages_done_for_file / N_STAGES_PER_FILE) * 100)
                results_queue.put({
                    "job_id": job_id, "type": "file_progress_update",
                    "data": {"percentage": file_percentage}
                })

            conv_func = getattr(conversions, conversion_func_name, None) if conversion_func_name else None
            if not callable(conv_func):
                error_msg = f"Conversion function '{conversion_func_name}' not found in worker."
                send_error_update_worker(error_msg) # Corrected from send_error_update
                results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": False, "message": error_msg}})
                if job_temp_dir: utils.cleanup(job_temp_dir, output_signal=send_output_update_worker, error_signal=send_error_update_worker)
                continue

            success = utils.process_file(
                staged_primary_file_path=path_to_process_in_temp,
                job_temp_dir=job_temp_dir,
                original_file_path_for_naming_and_delete=original_file_path,
                conversion_func=conv_func,
                format_out=selected_primary_output_ext,
                format_out2=selected_secondary_output_ext,
                output_signal=send_output_update_worker,
                error_signal=send_error_update_worker,
                explicit_output_dir=output_folder_path_final_dest,
                allow_overwrite=overwrite_files,
                target_format_from_worker=selected_primary_output_ext,
                stage_reporter=stage_reporter_for_process_file
            )

            if cumulative_stages_done_for_file < N_STAGES_PER_FILE:
                 final_stage_desc = "Completed" if success else "Failed"
                 stage_reporter_for_process_file(final_stage_desc)

            results_queue.put({"job_id": job_id, "type": "job_completed", "data": {"success": success, "message": "Job processed" if success else "Job failed during processing"}})

            if success and config.settings.DELETE_SOURCE_ON_SUCCESS:
                send_output_update_worker(f"Job successful, deleting source: {original_file_path}")
                try:
                    files_to_delete_source = [original_file_path]
                    if is_multi_file_job_type:
                        if original_file_path.lower().endswith('.cue'):
                            files_to_delete_source.extend(utils._get_cue_dependencies(original_file_path))
                        elif original_file_path.lower().endswith('.gdi'):
                            files_to_delete_source.extend(utils._get_gdi_dependencies(original_file_path))

                    for f_path_to_del in set(files_to_delete_source):
                        if os.path.exists(f_path_to_del):
                            if send2trash:
                                send2trash.send2trash(f_path_to_del)
                                send_output_update_worker(f"Sent to trash: {f_path_to_del}")
                            else:
                                os.remove(f_path_to_del)
                                send_output_update_worker(f"Permanently deleted: {f_path_to_del} (send2trash not available)")
                except Exception as del_e:
                    send_error_update_worker(f"Error deleting source file {original_file_path} or its dependencies: {del_e}")

        except Exception as e_outer:
            tb_str = traceback.format_exc()
            job_id_error = job_payload.get("job_id", "unknown_job_id_in_worker_exception") if 'job_payload' in locals() and job_payload is not None else "unknown_job_id_payload_none"

            # Try to inform the main thread about the error
            try:
                results_queue.put({
                    "job_id": job_id_error, "type": "error_update",
                    "data": {"message": f"Unhandled error in worker process (job: {job_id_error}): {e_outer}\n{tb_str}"}
                })
                results_queue.put({"job_id": job_id_error, "type": "job_completed", "data": {"success": False, "message": str(e_outer)}})
            except Exception as queue_e:
                print(f"WORKER PID {os.getpid()} CRITICAL ERROR: Could not put error to results_queue for job {job_id_error}: {queue_e}", file=sys.stderr)
                print(f"Original worker error (job: {job_id_error}): {e_outer}\n{tb_str}", file=sys.stderr)

            if job_payload is None: # If error happened while getting None (sentinel)
                break
            # Continue to next job if possible
            continue

    print(f"Worker process {os.getpid()} exiting gracefully.")
