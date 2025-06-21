# converter_tools/gui_worker.py

import os
import traceback
try:
    from PySide6.QtCore import QThread, Signal
except ImportError as e:
    print(f"FATAL ERROR (gui_worker.py): PySide6.QtCore not found. {e}")
    raise

from src.converter_tools import utils # Changed to absolute import
from src.converter_tools import conversions # Changed to absolute import

# Number of distinct stages reported by utils.process_file for progress tracking.
N_STAGES_PER_FILE = 3

class ConversionWorker(QThread):
    status_update = Signal(int, int, str) # current_cumulative_step, total_overall_steps, description_with_filename
    output_update = Signal(str)
    error_update = Signal(str)
    critical_error_occurred = Signal(str)
    file_progress_update = Signal(int) # Percentage for the current file (0-100)
    finished = Signal(int, int)  # success_count, fail_count

    def __init__(self, files_to_convert, conversion_details, output_folder_path,
                 overwrite_files, selected_primary_output_ext, selected_secondary_output_ext,
                 parent=None):
        super().__init__(parent)
        self.files_to_convert = files_to_convert
        self.conversion_details = conversion_details
        self.output_folder_path = output_folder_path 
        self.overwrite_files = overwrite_files
        self.selected_primary_output_ext = selected_primary_output_ext 
        self.selected_secondary_output_ext = selected_secondary_output_ext 
        self._stop_requested = False
        
        self.total_overall_steps = len(self.files_to_convert) * N_STAGES_PER_FILE
        self.cumulative_overall_steps = 0

    def _report_stage_progress(self, stage_description, current_filename):
        if self._stop_requested:
            return 

        self.cumulative_overall_steps += 1
        clamped_cumulative_steps = min(self.cumulative_overall_steps, self.total_overall_steps)

        self.status_update.emit(
            clamped_cumulative_steps,
            self.total_overall_steps,
            f"{stage_description}: {current_filename}" 
        )

    def run(self):
        self._stop_requested = False 
        success_count = 0
        fail_count = 0
        
        func_name = self.conversion_details.get('conversion_func_name')
        conv_func = getattr(conversions, func_name, None) if func_name else None

        if not callable(conv_func):
            critical_msg = f"Critical Error: Conversion function '{func_name}' is not valid or not found in conversions.py. Job cannot proceed."
            self.error_update.emit(critical_msg)
            self.critical_error_occurred.emit(critical_msg) 
            self.finished.emit(0, len(self.files_to_convert)) 
            return

        primary_out_ext_for_util = self.selected_primary_output_ext
        secondary_out_ext_for_util = self.selected_secondary_output_ext

        self.cumulative_overall_steps = 0 

        try:
            for i, file_path in enumerate(self.files_to_convert):
                if self._stop_requested:
                    self.output_update.emit("--- Conversion process aborted by user ---")
                    fail_count = len(self.files_to_convert) - success_count 
                    break 

                current_file_name = os.path.basename(file_path)
                self.output_update.emit(f"\n--- Processing file {i+1}/{len(self.files_to_convert)}: {current_file_name} ---")
                self.file_progress_update.emit(0) 

                stage_reporter_for_process_file = lambda stage_desc: self._report_stage_progress(stage_desc, current_file_name)
                
                current_output_dir = self.output_folder_path 

                success = utils.process_file(
                    file_path,
                    conv_func,
                    primary_out_ext_for_util, 
                    secondary_out_ext_for_util, 
                    output_signal=self.output_update,
                    error_signal=self.error_update,
                    explicit_output_dir=current_output_dir,
                    allow_overwrite=self.overwrite_files,
                    target_format_from_worker=primary_out_ext_for_util,
                    stage_reporter=stage_reporter_for_process_file 
                )

                if self._stop_requested: 
                    self.output_update.emit(f"--- Processing of {current_file_name} interrupted by stop request ---")
                    fail_count += 1 
                    expected_steps_for_this_file_so_far = (i + 1) * N_STAGES_PER_FILE
                    if self.cumulative_overall_steps < expected_steps_for_this_file_so_far:
                        missing_stages = expected_steps_for_this_file_so_far - self.cumulative_overall_steps
                        for _ in range(missing_stages):
                            self._report_stage_progress("Interrupted", current_file_name)
                    continue 

                if success:
                    success_count += 1
                    self.output_update.emit(f"--- Success: {current_file_name} ---")
                    self.file_progress_update.emit(100) 
                else:
                    fail_count += 1
                    self.error_update.emit(f"--- FAILED: {current_file_name} (check log for details) ---")
                    expected_steps_for_this_file = (i + 1) * N_STAGES_PER_FILE
                    if self.cumulative_overall_steps < expected_steps_for_this_file:
                        missing_stages = expected_steps_for_this_file - self.cumulative_overall_steps
                        for _ in range(missing_stages): 
                            self._report_stage_progress("File failed", current_file_name)
                    self.file_progress_update.emit(100) 
        
        except Exception as e:
            tb = traceback.format_exc()
            critical_msg = f"Critical Error in conversion worker thread: {e}\nTraceback:\n{tb}"
            self.error_update.emit(critical_msg)
            self.critical_error_occurred.emit(critical_msg) 
            fail_count = len(self.files_to_convert) - success_count
        finally:
            if not self._stop_requested and self.cumulative_overall_steps < self.total_overall_steps:
                final_stage_desc = "Job finalizing after error or incomplete run" if fail_count > 0 else "Finalizing job completion"
                remaining_ticks = self.total_overall_steps - self.cumulative_overall_steps
                for _ in range(remaining_ticks):
                    self.cumulative_overall_steps += 1
                    self.status_update.emit(self.cumulative_overall_steps, self.total_overall_steps, final_stage_desc)

            self.finished.emit(success_count, fail_count)

    def request_stop(self):
        self.output_update.emit("--- Stop requested for current job ---")
        self._stop_requested = True
