# convert_tools/gui.py
"""
Contains the PySimpleGUI interface logic for the converter tool.
V15: Moves output to bottom, adds settings menu/window. Fixes control layout
and removes invalid Table parameter.
"""

import FreeSimpleGUI as sg
import os
import sys
import threading
import queue # For communicating with the conversion thread
import io # For redirecting stdout/stderr
import glob # For scanning folders
import operator # For table sorting
import traceback # For error reporting
import re # For stripping ANSI codes

# Import modular components from the same directory
try:
    import config         # Settings and tool paths
    import utils          # Helper functions (run_command, cleanup, etc.)
    import conversions    # Specific conversion routines
    import menu_definitions # Centralized menu data
except ImportError as e:
    sg.popup_error(f"ERROR: gui.py failed to import sibling modules.\nEnsure all modules are in 'convert_tools'.\nDetails: {e}", title="Import Error")
    sys.exit(1)

# --- Constants ---
OUTPUT_PANEL_KEY = '-OUTPUT_PANEL-'
OUTPUT_TEXT_KEY = '-OUTPUT_TEXT-'
TABLE_KEY = '-FILE_TABLE-'
FILE_TYPE_COMBO_KEY = '-FILE_TYPE_COMBO-'
CONVERSION_COMBO_KEY = '-CONVERSION_COMBO-'
RECURSIVE_CHECKBOX_KEY = '-RECURSIVE-'
CONVERT_BUTTON_KEY = '-CONVERT-'
CLEAR_INPUT_BUTTON_KEY = '-CLEAR_INPUT-'
CLEAR_OUTPUT_BUTTON_KEY = '-CLEAR_OUTPUT-'
TOGGLE_OUTPUT_BUTTON_KEY = '-TOGGLE_OUTPUT-'
STATUS_BAR_KEY = '-STATUS-'
ALL_DONE_TEXT_KEY = '-ALL_DONE-'

# New Button Keys
ADD_FILES_BUTTON_KEY = '-ADD_FILES-'
ADD_FOLDER_BUTTON_KEY = '-ADD_FOLDER-'

# Table constants
CHECKMARK = '✓'
TABLE_HEADINGS = [CHECKMARK, ' File Path', ' Type']
COL_CHECK = 0
COL_PATH = 1
COL_TYPE = 2

# Right-click menu
TABLE_RIGHT_CLICK_MENU = ['&Right', ['Remove from list::-TABLE_REMOVE-']]

# Queue communication constants
MSG_STATUS = 'STATUS'
MSG_OUTPUT = 'OUTPUT'
MSG_DONE = 'DONE'
MSG_ERROR = 'ERROR'

# Settings Window Keys
SETTING_COPY_LOCALLY = '-SETTING_COPY-'
SETTING_DELETE_SOURCE = '-SETTING_DELETE-'
SETTING_VALIDATE_7Z = '-SETTING_VALIDATE-'
SETTING_COMPRESS_LEVEL = '-SETTING_COMPRESS-'
SETTING_TEMP_DIR = '-SETTING_TEMP-'
SETTING_SAVE_BUTTON = '-SETTING_SAVE-'
SETTING_CANCEL_BUTTON = '-SETTING_CANCEL-'

# Store valid input extensions from menu_definitions
VALID_EXTENSIONS = menu_definitions.VALID_INPUT_EXTENSIONS
# Store conversion map (now includes gui_text)
CONVERSION_MAP = menu_definitions.CONVERSION_MAP

# ANSI escape code regex
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# --- GUI Helper Functions ---

def strip_ansi_codes(text):
    """Removes ANSI escape codes from a string."""
    return ANSI_ESCAPE_RE.sub('', text)

def scan_folder(folder_path, recursive):
    """Scans a folder for files with valid input extensions."""
    found_files = []
    if not os.path.isdir(folder_path):
        return found_files

    print(f"Scanning folder: {folder_path} (Recursive: {recursive})")
    if recursive:
        for root, _, files in os.walk(folder_path):
            if '_temp' in root or 'TEMP_CONVERT' in root: continue
            for file in files:
                ext = os.path.splitext(file)[1].lower().lstrip('.')
                if ext in VALID_EXTENSIONS:
                    full_path = os.path.join(root, file)
                    found_files.append(full_path)
    else:
        try:
            for item in os.listdir(folder_path):
                full_path = os.path.join(folder_path, item)
                if os.path.isfile(full_path):
                    ext = os.path.splitext(item)[1].lower().lstrip('.')
                    if ext in VALID_EXTENSIONS:
                         found_files.append(full_path)
        except OSError as e:
            print(f"Error scanning folder {folder_path}: {e}")

    print(f"Found {len(found_files)} convertible files in folder.")
    return found_files

def update_gui_after_input_change(window, table_data_ref, added_paths=None, recursive=False):
    """
    Processes newly added input paths OR just updates UI based on current table_data_ref.
    Modifies table_data_ref directly.
    """
    newly_added_count = 0
    if added_paths:
        current_files_in_table = {row[COL_PATH] for row in table_data_ref}
        file_types_detected = {row[COL_TYPE] for row in table_data_ref if len(row) > COL_TYPE}
        new_rows_added = []

        if not isinstance(added_paths, (list, tuple)):
            print(f"Warning: added_paths is not a list or tuple: {type(added_paths)}")
            added_paths = []

        for item_path in added_paths:
            if not item_path or not os.path.exists(item_path): continue

            if os.path.isfile(item_path):
                ext_lower = os.path.splitext(item_path)[1].lower().lstrip('.')
                if ext_lower in VALID_EXTENSIONS and item_path not in current_files_in_table:
                    ext_upper = ext_lower.upper()
                    new_rows_added.append(['', item_path, ext_upper])
                    file_types_detected.add(ext_upper)
                    newly_added_count += 1
                else:
                    print(f"Ignoring unsupported or duplicate file: {item_path}")
            elif os.path.isdir(item_path):
                print(f"Processing folder: {item_path}")
                files_in_folder = scan_folder(item_path, recursive)
                for f_path in files_in_folder:
                     if f_path not in current_files_in_table:
                          ext_lower = os.path.splitext(f_path)[1].lower().lstrip('.')
                          ext_upper = ext_lower.upper()
                          new_rows_added.append(['', f_path, ext_upper])
                          file_types_detected.add(ext_upper)
                          newly_added_count += 1
            else:
                 print(f"Ignoring invalid item: {item_path}")

        table_data_ref.extend(new_rows_added)
        seen_paths = set()
        unique_data = []
        for row in table_data_ref:
            if isinstance(row, (list, tuple)) and len(row) > COL_PATH and row[COL_PATH] not in seen_paths:
                unique_data.append(row)
                seen_paths.add(row[COL_PATH])
        table_data_ref[:] = unique_data
        table_data_ref.sort(key=lambda x: x[COL_PATH] if isinstance(x, (list, tuple)) and len(x) > COL_PATH else '')

    # --- Update GUI elements based on the final table_data_ref ---
    final_file_types = {row[COL_TYPE] for row in table_data_ref if isinstance(row, (list, tuple)) and len(row) > COL_TYPE}
    file_types_list = sorted(list(final_file_types))
    current_type_selection = window[FILE_TYPE_COMBO_KEY].get()
    new_type_value = ''
    should_auto_select = False

    if file_types_list:
        if current_type_selection in file_types_list:
            new_type_value = current_type_selection
        else:
            new_type_value = file_types_list[0]
            should_auto_select = True if new_type_value else False
        window[FILE_TYPE_COMBO_KEY].update(values=file_types_list, value=new_type_value, disabled=False)
        if should_auto_select:
            auto_select_files_by_type(window, table_data_ref, new_type_value)
        update_conversion_dropdown(window, table_data_ref, new_type_value)
    else: # No files left
        window[FILE_TYPE_COMBO_KEY].update(values=[], value='', disabled=True)
        update_conversion_dropdown(window, table_data_ref, None)

    # Final update of table visuals (data only, no colors)
    window[TABLE_KEY].update(values=table_data_ref, select_rows=[]) # Deselect rows

    status_text = f"{len(table_data_ref)} convertible file(s) loaded."
    if newly_added_count > 0:
        status_text += f" ({newly_added_count} added)."
    window[STATUS_BAR_KEY].update(status_text)
    window[ALL_DONE_TEXT_KEY].update(visible=False)


def update_conversion_dropdown(window, table_data_ref, selected_type):
    """Filters and updates the conversion dropdown based on selected file type."""
    possible_conversions = []
    gui_conversion_display_map = {}

    if selected_type:
        selected_type_lower = selected_type.lower()
        for choice_num, details in CONVERSION_MAP.items():
            input_formats = details.get('formats_in', [])
            if isinstance(input_formats, (list, tuple)) and selected_type_lower in input_formats:
                if choice_num in ['80', '81']: continue
                gui_display_text = details.get('gui_text', details.get('cli_text'))
                if gui_display_text:
                    possible_conversions.append(gui_display_text)
                    gui_conversion_display_map[gui_display_text] = choice_num

    current_conv_selection_display = window[CONVERSION_COMBO_KEY].get()
    new_conv_value = ''

    possible_conversions_set = set(possible_conversions)
    sorted_conversions = sorted(list(possible_conversions_set))

    if sorted_conversions:
        if current_conv_selection_display in possible_conversions_set:
             new_conv_value = current_conv_selection_display
        else:
             new_conv_value = sorted_conversions[0]
        window[CONVERSION_COMBO_KEY].update(values=sorted_conversions, value=new_conv_value, disabled=False)
    else:
        window[CONVERSION_COMBO_KEY].update(values=[], value='', disabled=True)

    # Update Convert button state
    any_checked = any(len(row) > COL_CHECK and row[COL_CHECK] == CHECKMARK for row in table_data_ref)
    if new_conv_value and any_checked:
        window[CONVERT_BUTTON_KEY].update(disabled=False, button_color=('white', 'green'))
    else:
        window[CONVERT_BUTTON_KEY].update(disabled=True, button_color=None)

    window.user_defined_data = {'gui_conversion_display_map': gui_conversion_display_map}

def auto_select_files_by_type(window, table_data_ref, selected_type):
    """Checks/unchecks rows in the table based on the selected file type."""
    changed = False
    for i, row in enumerate(table_data_ref):
        if len(row) <= COL_TYPE: continue
        current_check_state = (row[COL_CHECK] == CHECKMARK)
        should_be_checked = (row[COL_TYPE].upper() == selected_type.upper())
        if current_check_state != should_be_checked:
            table_data_ref[i][COL_CHECK] = CHECKMARK if should_be_checked else ''
            changed = True
    return changed


# --- Conversion Worker Thread ---

def conversion_worker(files_to_convert, conversion_details, msg_queue):
    """
    Runs the conversion process in a separate thread.
    Captures print output and sends status messages via queue.
    """
    total_files = len(files_to_convert)
    success_count = 0
    fail_count = 0

    conv_func = conversion_details['func']
    fmt_out = conversion_details['format_out']
    fmt_out2 = conversion_details['format_out2']

    if not callable(conv_func):
        msg_queue.put((MSG_ERROR, f"Invalid conversion function for selected option."))
        msg_queue.put((MSG_DONE, (success_count, fail_count)))
        return

    # Redirect stdout/stderr for capturing print statements
    class QueueIO:
        def __init__(self, queue_obj, msg_type):
            self.queue = queue_obj
            self.msg_type = msg_type
            self.buffer = ""

        def write(self, text):
            clean_text = strip_ansi_codes(text)
            self.buffer += clean_text
            while '\n' in self.buffer or '\r' in self.buffer:
                end_line_pos = -1
                newline_pos = self.buffer.find('\n')
                cr_pos = self.buffer.find('\r')

                if newline_pos != -1 and cr_pos != -1:
                    end_line_pos = min(newline_pos, cr_pos)
                elif newline_pos != -1:
                    end_line_pos = newline_pos
                elif cr_pos != -1:
                    end_line_pos = cr_pos
                else:
                    break

                line_to_send = self.buffer[:end_line_pos].strip()
                if line_to_send:
                    # Special handling for progress lines ending in \r
                    is_progress = (cr_pos == end_line_pos)
                    self.queue.put((self.msg_type, line_to_send, is_progress))

                self.buffer = self.buffer[end_line_pos+1:]

        def flush(self):
             if self.buffer:
                 clean_buffer = strip_ansi_codes(self.buffer.strip())
                 if clean_buffer:
                     self.queue.put((self.msg_type, clean_buffer, False)) # Not progress
                 self.buffer = ""

    queue_stdout = QueueIO(msg_queue, MSG_OUTPUT)
    queue_stderr = QueueIO(msg_queue, MSG_ERROR)

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = queue_stdout
    sys.stderr = queue_stderr

    try:
        for i, file_path in enumerate(files_to_convert):
            # Update status before processing
            msg_queue.put((MSG_STATUS, f"Processing file {i+1}/{total_files}: {os.path.basename(file_path)}"))
            msg_queue.put((MSG_OUTPUT, f"\n--- Processing: {file_path} ---", False))

            if utils.process_file(file_path, conv_func, fmt_out, fmt_out2):
                success_count += 1
                msg_queue.put((MSG_OUTPUT, f"--- Success: {os.path.basename(file_path)} ---", False))
            else:
                fail_count += 1
                msg_queue.put((MSG_ERROR, f"--- FAILED: {os.path.basename(file_path)} ---", False))

            sys.stdout.flush()
            sys.stderr.flush()

    except Exception as e:
        tb = traceback.format_exc()
        msg_queue.put((MSG_ERROR, f"Unexpected Error during conversion thread:\n{tb}", False))
        fail_count = total_files - success_count
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        msg_queue.put((MSG_DONE, (success_count, fail_count)))


# --- Settings Window ---

def create_settings_window():
    """Creates the layout for the settings window."""
    layout = [
        [sg.Text("Core Settings", font='Any 12 bold')],
        [sg.Checkbox("Copy files locally before processing", default=config.COPY_LOCALLY, key=SETTING_COPY_LOCALLY)],
        [sg.Checkbox("Delete original file on successful conversion", default=config.DELETE_SOURCE_ON_SUCCESS, key=SETTING_DELETE_SOURCE)],
        [sg.Text("Main Temp Directory:", size=(25,1)), sg.Input(config.MAIN_TEMP_DIR, key=SETTING_TEMP_DIR, size=(40,1)), sg.FolderBrowse()],
        [sg.HSeparator()],
        [sg.Text("Tool-Specific Settings", font='Any 12 bold')],
        [sg.Checkbox("Validate 7z archive after creation", default=config.VALIDATE_FILE, key=SETTING_VALIDATE_7Z)],
        [sg.Text("RVZ Compression Level (1-22):", size=(25,1)), sg.Spin(list(range(1, 23)), initial_value=config.COMPRESS_LEVEL, size=(5,1), key=SETTING_COMPRESS_LEVEL)],
        [sg.HSeparator()],
        [sg.Button("Save", key=SETTING_SAVE_BUTTON), sg.Button("Cancel", key=SETTING_CANCEL_BUTTON)]
    ]
    return sg.Window("Converter Settings", layout, modal=True, finalize=True)

def run_settings_window():
    """Displays the settings window and updates config values in memory."""
    settings_window = create_settings_window()

    while True:
        event, values = settings_window.read()
        if event in (sg.WIN_CLOSED, SETTING_CANCEL_BUTTON):
            break
        elif event == SETTING_SAVE_BUTTON:
            # Update config module attributes (in memory only)
            try:
                config.COPY_LOCALLY = values[SETTING_COPY_LOCALLY]
                config.DELETE_SOURCE_ON_SUCCESS = values[SETTING_DELETE_SOURCE]
                config.VALIDATE_FILE = values[SETTING_VALIDATE_7Z]
                config.COMPRESS_LEVEL = int(values[SETTING_COMPRESS_LEVEL])

                temp_dir = values[SETTING_TEMP_DIR]
                if os.path.isdir(temp_dir):
                     config.MAIN_TEMP_DIR = temp_dir
                else:
                     parent = os.path.dirname(temp_dir)
                     if os.path.isdir(parent):
                          config.MAIN_TEMP_DIR = temp_dir
                     else:
                          sg.popup_error(f"Invalid Temp Directory path:\n{temp_dir}\nParent directory does not exist.", title="Settings Error")
                          continue

                sg.popup_ok("Settings updated for this session.", title="Settings Saved")
                break
            except Exception as e:
                 sg.popup_error(f"Error applying settings:\n{e}", title="Settings Error")

    settings_window.close()


# --- GUI Layout Definition ---

def create_layout():
    """Creates the PySimpleGUI layout."""
    menu_def = [['File', ['Settings::-SETTINGS-', 'E&xit::-EXIT-']]]

    table_layout = [
        [sg.Table(values=[],
                  headings=TABLE_HEADINGS,
                  key=TABLE_KEY,
                  auto_size_columns=False,
                  col_widths=[3, 60, 10],
                  # FIX: Remove column_options
                  # column_options={'stretch': False},
                  cols_justification=['center', 'left', 'center'],
                  justification='left',
                  num_rows=10,
                  display_row_numbers=False,
                  enable_events=True,
                  enable_click_events=True,
                  expand_x=True,
                  expand_y=True,
                  right_click_menu=TABLE_RIGHT_CLICK_MENU
                  )]
    ]

    controls_layout = [
         [sg.Text("Select file type to convert:", size=(20,1)), sg.Push(),
          sg.Combo(values=[], size=(25, 1), key=FILE_TYPE_COMBO_KEY, enable_events=True, readonly=True, disabled=True, expand_x=True)],
         [sg.Text("Select conversion:", size=(20,1)), sg.Push(),
          sg.Combo(values=[], size=(25, 1), key=CONVERSION_COMBO_KEY, enable_events=True, readonly=True, disabled=True, expand_x=True)],
         [sg.Button("CONVERT", key=CONVERT_BUTTON_KEY, button_color=None, disabled=True, expand_x=True)],
    ]

    # Output panel layout
    output_layout = [
         [sg.Text("Log Output:", font='Any 10 bold'), sg.Push(), sg.Button("Clear Output", key=CLEAR_OUTPUT_BUTTON_KEY)],
         [sg.Multiline(s=(None, 10), key=OUTPUT_TEXT_KEY, autoscroll=True, reroute_stdout=False, reroute_stderr=False, write_only=True, disabled=True, expand_x=True)],
    ]
    output_panel = sg.pin(sg.Column(output_layout, key=OUTPUT_PANEL_KEY, visible=True, expand_x=True, expand_y=True))


    # Main Layout
    layout = [
         [sg.Menu(menu_def)],
         [sg.Button("Add Files...", key=ADD_FILES_BUTTON_KEY, size=(15,1)),
         sg.Button("Add Folder...", key=ADD_FOLDER_BUTTON_KEY, size=(15,1)),
         sg.Checkbox("Recursive", default=False, key=RECURSIVE_CHECKBOX_KEY, enable_events=True),
         sg.Push(),
         sg.Button("Clear Input List", key=CLEAR_INPUT_BUTTON_KEY)],
         [sg.Column(table_layout, expand_x=True, expand_y=True)],
         [sg.Column(controls_layout, expand_x=True)],
         [sg.HSeparator()],
         [sg.Button("Show Log ▼", key=TOGGLE_OUTPUT_BUTTON_KEY)],
         [output_panel],
         [sg.HSeparator()],
         [sg.Text("", key=ALL_DONE_TEXT_KEY, font='Any 12 bold', text_color='green', visible=False),
          sg.StatusBar("Ready. Add files or folders using the buttons.", size=(40, 1), key=STATUS_BAR_KEY, justification='left', expand_x=True)]
    ]
    return layout

# --- Main GUI Function ---

def run_gui():
    """Creates and runs the main GUI window and event loop."""
    try:
        sg.theme("SystemDefaultForReal")
    except:
        print("SystemDefaultForReal theme not available, using SystemDefault.")
        sg.theme("SystemDefault")

    layout = create_layout()
    window = sg.Window("Oz Converter Tool", layout, resizable=True, finalize=True, enable_close_attempted_event=True)
    window.set_min_size((700, 600))

    table_data = []
    sort_order = {i: None for i in range(len(TABLE_HEADINGS))}
    output_visible = False
    conversion_thread = None
    message_queue = queue.Queue()

    # --- Event Loop ---
    while True:
        event, values = window.read(timeout=100)

        # --- Check Queue for thread messages ---
        try:
            message = message_queue.get_nowait()
            if isinstance(message, tuple) and len(message) >= 2:
                message_type = message[0]
                message_data = message[1]
                is_progress = message[2] if len(message) > 2 else False

                if message_type == MSG_STATUS:
                    window[STATUS_BAR_KEY].update(message_data, text_color=None)
                elif message_type == MSG_OUTPUT:
                    window[OUTPUT_TEXT_KEY].update(message_data + '\n', append=True)
                elif message_type == MSG_ERROR:
                    window[OUTPUT_TEXT_KEY].update(f"ERROR: {message_data}\n", append=True, text_color_for_value='red')
                    window[STATUS_BAR_KEY].update("Error occurred during conversion.", text_color='red')
                elif message_type == MSG_DONE:
                    counts = message_data
                    if isinstance(counts, tuple) and len(counts) == 2:
                        success_count, fail_count = counts
                        status_msg = f"Conversion finished. Success: {success_count}, Failed: {fail_count}."
                        status_color = 'green' if fail_count == 0 and success_count > 0 else 'red'
                        window[STATUS_BAR_KEY].update(status_msg, text_color=status_color)
                        window[ALL_DONE_TEXT_KEY].update("ALL DONE", visible=True, text_color=status_color)
                        # Re-enable controls
                        window[CONVERT_BUTTON_KEY].update(disabled=False)
                        window[CLEAR_INPUT_BUTTON_KEY].update(disabled=False)
                        window[ADD_FILES_BUTTON_KEY].update(disabled=False)
                        window[ADD_FOLDER_BUTTON_KEY].update(disabled=False)
                        window[FILE_TYPE_COMBO_KEY].update(disabled=False)
                        window[CONVERSION_COMBO_KEY].update(disabled=False)
                        window[RECURSIVE_CHECKBOX_KEY].update(disabled=False)
                        update_conversion_dropdown(window, table_data, values[FILE_TYPE_COMBO_KEY])
                        conversion_thread = None
                    else:
                        print(f"Error: Invalid data format for MSG_DONE: {counts}")
            else:
                print(f"Warning: Received unexpected message format from queue: {message}")
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error processing queue message: {e}")
            tb = traceback.format_exc()
            print(tb)

        # --- Process GUI Events ---
        if event == sg.TIMEOUT_KEY:
            continue

        # --- Menu Events ---
        if event == 'Settings::-SETTINGS-':
            run_settings_window()
            continue
        elif event == 'Exit::-EXIT-':
            break

        # --- Exit ---
        if event in (sg.WIN_CLOSED, sg.WINDOW_CLOSE_ATTEMPTED_EVENT):
            break

        # --- Add Files Button ---
        elif event == ADD_FILES_BUTTON_KEY:
            valid_ext_str = " ".join([f"*.{ext}" for ext in VALID_EXTENSIONS])
            file_types = [("Convertible Files", valid_ext_str), ("All Files", "*.*")]
            selected_paths = sg.popup_get_file(
                'Select file(s) to convert', multiple_files=True, file_types=file_types, no_window=True
            )
            if selected_paths:
                is_recursive = values[RECURSIVE_CHECKBOX_KEY]
                update_gui_after_input_change(window, table_data, added_paths=selected_paths, recursive=is_recursive)

        # --- Add Folder Button ---
        elif event == ADD_FOLDER_BUTTON_KEY:
            folder_path = sg.popup_get_folder(
                'Select folder containing files to convert', no_window=True
            )
            if folder_path:
                is_recursive = values[RECURSIVE_CHECKBOX_KEY]
                update_gui_after_input_change(window, table_data, added_paths=[folder_path], recursive=is_recursive)

        # --- Table Click ---
        elif isinstance(event, tuple) and event[0] == TABLE_KEY:
            row, col = event[2]
            if row is not None and row != -1:
                selected_file_type = values[FILE_TYPE_COMBO_KEY]
                can_toggle = False
                row_type = ''
                if 0 <= row < len(table_data) and len(table_data[row]) > COL_TYPE:
                    row_type = table_data[row][COL_TYPE].upper()
                    if not selected_file_type or row_type == selected_file_type.upper():
                        can_toggle = True
                else:
                    print(f"Warning: Invalid row index {row} or incomplete data for table click.")

                if can_toggle and (col == COL_CHECK or col == -1):
                    try:
                        current_state = table_data[row][COL_CHECK]
                        table_data[row][COL_CHECK] = CHECKMARK if not current_state else ''
                        window[TABLE_KEY].update(values=table_data, select_rows=[])
                        update_conversion_dropdown(window, table_data, selected_file_type)
                    except IndexError:
                        print(f"Error toggling check for row {row}. Data length: {len(table_data)}")
                elif not can_toggle and (col == COL_CHECK or col == -1):
                    if 0 <= row < len(table_data):
                         window[STATUS_BAR_KEY].update(f"Cannot select file type {row_type} when '{selected_file_type}' is selected.", text_color='orange')

            elif row == -1 and col is not None and col != -1: # Header click
                print(f"Header clicked: {col} ({TABLE_HEADINGS[col]})")
                if col == COL_CHECK:
                    key = lambda x: (x[col] == CHECKMARK)
                elif col == COL_PATH:
                     key = lambda x: x[col] if isinstance(x, (list, tuple)) and len(x) > col else ''
                elif col == COL_TYPE:
                     key = lambda x: x[col] if isinstance(x, (list, tuple)) and len(x) > col else ''
                else:
                     continue

                current_sort = sort_order.get(col)
                if current_sort is None or current_sort is False:
                    reverse_sort = False
                    sort_order[col] = True
                else:
                    reverse_sort = True
                    sort_order[col] = False

                for i in sort_order:
                    if i != col: sort_order[i] = None

                table_data.sort(key=key, reverse=reverse_sort)
                window[TABLE_KEY].update(values=table_data, select_rows=[])
                window[STATUS_BAR_KEY].update(f"Sorted by {TABLE_HEADINGS[col].strip()} {'Descending' if reverse_sort else 'Ascending'}", text_color=None)

        # --- Table Right-Click Remove ---
        elif event == 'Remove from list::-TABLE_REMOVE-':
            selected_row_indices = values[TABLE_KEY]
            if not selected_row_indices:
                window[STATUS_BAR_KEY].update("No rows selected to remove.", text_color='red')
            else:
                selected_row_indices.sort(reverse=True)
                removed_count = 0
                for index in selected_row_indices:
                    if 0 <= index < len(table_data):
                        try:
                            del table_data[index]
                            removed_count += 1
                        except IndexError:
                             print(f"Error removing row at index {index}. Data length: {len(table_data)}")
                    else:
                         print(f"Invalid index {index} selected for removal. Data length: {len(table_data)}")

                update_gui_after_input_change(window, table_data)
                window[STATUS_BAR_KEY].update(f"Removed {removed_count} file(s).", text_color=None)


        # --- Recursive Checkbox ---
        elif event == RECURSIVE_CHECKBOX_KEY:
            is_recursive = values[RECURSIVE_CHECKBOX_KEY]
            window[STATUS_BAR_KEY].update(f"Recursive mode {'enabled' if is_recursive else 'disabled'}. Re-add folders to apply.", text_color=None)


        # --- Clear Input Button ---
        elif event == CLEAR_INPUT_BUTTON_KEY:
            table_data = []
            update_gui_after_input_change(window, table_data)
            window[STATUS_BAR_KEY].update("Input cleared.", text_color=None)

        # --- File Type Dropdown Selection ---
        elif event == FILE_TYPE_COMBO_KEY:
            selected_type = values[FILE_TYPE_COMBO_KEY]
            window[STATUS_BAR_KEY].update(f"File type '{selected_type}' selected.", text_color=None)
            changed = auto_select_files_by_type(window, table_data, selected_type)
            # Update conversion dropdown based on the selected type and new checks
            update_conversion_dropdown(window, table_data, selected_type)
            # Update table visuals AFTER auto-select and dropdown update
            if changed:
                 window[TABLE_KEY].update(values=table_data, select_rows=[])
            window[ALL_DONE_TEXT_KEY].update(visible=False)

        # --- Conversion Dropdown Selection ---
        elif event == CONVERSION_COMBO_KEY:
            selected_conversion_display = values[CONVERSION_COMBO_KEY]
            if selected_conversion_display:
                window[STATUS_BAR_KEY].update(f"Conversion '{selected_conversion_display}' selected.", text_color=None)
                update_conversion_dropdown(window, table_data, values[FILE_TYPE_COMBO_KEY])
                window[ALL_DONE_TEXT_KEY].update(visible=False)
            else:
                window[CONVERT_BUTTON_KEY].update(disabled=True, button_color=None)

        # --- Convert Button ---
        elif event == CONVERT_BUTTON_KEY:
            if conversion_thread and conversion_thread.is_alive():
                sg.popup_error("A conversion is already in progress.", title="Busy")
                continue

            selected_files_to_convert = [row[COL_PATH] for row in table_data if len(row) > COL_CHECK and row[COL_CHECK] == CHECKMARK]
            selected_conversion_display = values[CONVERSION_COMBO_KEY]
            conv_map = window.user_defined_data.get('gui_conversion_display_map', {})
            choice_num = conv_map.get(selected_conversion_display)

            if not selected_files_to_convert:
                window[STATUS_BAR_KEY].update("No files selected for conversion.", text_color='red')
                continue
            if not choice_num or choice_num not in CONVERSION_MAP:
                 window[STATUS_BAR_KEY].update("Invalid conversion selected.", text_color='red')
                 continue

            conversion_details = CONVERSION_MAP[choice_num]

            window[STATUS_BAR_KEY].update(f"Starting conversion for {len(selected_files_to_convert)} file(s)...", text_color=None)
            # Disable controls
            window[CONVERT_BUTTON_KEY].update(disabled=True, button_color=None)
            window[CLEAR_INPUT_BUTTON_KEY].update(disabled=True)
            window[ADD_FILES_BUTTON_KEY].update(disabled=True)
            window[ADD_FOLDER_BUTTON_KEY].update(disabled=True)
            window[FILE_TYPE_COMBO_KEY].update(disabled=True)
            window[CONVERSION_COMBO_KEY].update(disabled=True)
            window[RECURSIVE_CHECKBOX_KEY].update(disabled=True)
            window[TABLE_KEY].update(select_rows=[])
            window[ALL_DONE_TEXT_KEY].update(visible=False)
            window[OUTPUT_TEXT_KEY].update('') # Clear previous output

            # Start the conversion thread
            message_queue = queue.Queue()
            conversion_thread = threading.Thread(
                target=conversion_worker,
                args=(selected_files_to_convert, conversion_details, message_queue),
                daemon=True
            )
            conversion_thread.start()

        # --- Toggle Output Panel ---
        elif event == TOGGLE_OUTPUT_BUTTON_KEY:
            output_visible = not output_visible
            window[OUTPUT_PANEL_KEY].update(visible=output_visible)
            window[TOGGLE_OUTPUT_BUTTON_KEY].update("Hide Log ▲" if output_visible else "Show Log ▼")
            # window.refresh(); window.finalize() # Usually not needed with pin

        # --- Clear Output Button ---
        elif event == CLEAR_OUTPUT_BUTTON_KEY:
            window[OUTPUT_TEXT_KEY].update('')
            window[STATUS_BAR_KEY].update("Output cleared.")


    window.close()

# Allow direct execution for testing
if __name__ == "__main__":
    if os.path.basename(os.getcwd()) == 'convert_tools':
        parent_dir = os.path.dirname(os.getcwd())
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        pass
    run_gui()
