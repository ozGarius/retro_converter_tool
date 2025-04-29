# convert_tools/menu_definitions.py
"""
Defines the menu structure and conversion options for the tool.
Includes separate display text for GUI dropdowns.
"""
import os

# Import the conversion functions
try:
    import conversions
except ImportError:
    print("ERROR: menu_definitions.py could not import conversions.py")
    pass


# Menu data structure:
# [Category, [
#    [Number, CLI Text, GUI Text, [Input Formats], Output Format, Output Format2, Function]
# ]]
# GUI Text: Simplified text like "to CHD", "to ISO"
menu_data = [
    ["Nintendo GameCube / Nintendo Wii", [
        ['10', "ISO to RVZ",        "to RVZ",                      ['iso'],               'rvz', None, conversions.convert_iso_to_rvz_routine],
        ['11', "RVZ to ISO",        "to ISO",                      ['rvz'],               'iso', None, conversions.convert_rvz_to_iso_routine],
        ['12', "7Z/ZIP/RAR to RVZ", "Extract and convert to RVZ",  ['7z', 'zip', 'rar'],  'rvz', None, conversions.convert_archive_to_rvz_routine],
    ]],
    ["Sony Playstation 1 / Sega Saturn / Sega CD", [
        ['20', "ISO/CUE/IMG to CHD", "to CHD",                     ['iso', 'cue', 'img'], 'chd', None, conversions.convert_discimage_to_chd_routine],
        ['21', "7Z/ZIP/RAR to CHD",  "Extract and convert to CHD", ['7z', 'zip', 'rar'],  'chd', None, conversions.convert_archive_to_chd_routine],
        ['23', "CHD to CUE/BIN",     "to CUE/BIN",                 ['chd'],               'cue', 'bin', conversions.convert_chd_to_cuebin_routine],
        ['24', "CHD to CD ISO",      "to CD ISO",                  ['chd'],               'iso', None, conversions.convert_chd_to_cdiso_routine],
    ]],
    ["Sega Dreamcast", [
        ['30', "GDI/CUE to CHD",    "to CHD",                      ['gdi', 'cue'],        'chd', None, conversions.convert_discimage_to_chd_routine],
        ['31', "7Z/ZIP/RAR to CHD", "Extract and convert to CHD",  ['7z', 'zip', 'rar'],  'chd', None, conversions.convert_archive_to_chd_routine],
        ['32', "CHD to GDI",        "to GDI",                      ['chd'],               'gdi', None, conversions.convert_chd_to_gdi_routine],
    ]],
    ["Sony Playstation 2", [
        ['40', "ISO to CHD",        "to CHD",                      ['iso'],               'chd', None, conversions.convert_discimage_to_chd_routine],
        ['41', "7Z/ZIP/RAR to CHD", "Extract and convert to CHD",  ['7z', 'zip', 'rar'],  'chd', None, conversions.convert_archive_to_chd_routine],
        ['42', "CSO to CHD",        "to CHD",                      ['cso'],               'chd', None, conversions.convert_cso_to_chd_routine],
        ['24', "CHD to CD ISO",     "to CD ISO",                   ['chd'],               'iso', None, conversions.convert_chd_to_cdiso_routine],
        ['24', "CHD to DVD ISO",    "to DVD ISO",                  ['chd'],               'iso', None, conversions.convert_chd_to_dvdiso_routine],
    ]],
    ["Playstation Portable", [
        ['50', "ISO to CSO",        "to CSO",                      ['iso'],               'cso', None, conversions.convert_iso_to_cso_routine],
        ['51', "7Z/ZIP/RAR to CSO", "Extract and convert to CSO",  ['7z', 'zip', 'rar'],  'cso', None, conversions.convert_archive_to_cso_routine],
    ]],
    ["Archiving", [
        ['90', "ZIP/RAR to 7Z",     "Archive to 7Z",               ['zip', 'rar'],        '7z', None, conversions.convert_archive_to_7z_routine],
    ]],
    ["Audio", [
        # These are handled specially and don't need GUI text here
        ['80', "Audio to Audio (Specify Formats)", None, [], None, None, None],
        ['81', "Folder to FLAC", None, [], 'flac', None, None],
    ]],
]

def get_all_input_extensions():
    """Extracts all unique possible input extensions from menu_data."""
    extensions = set()
    for category, options in menu_data:
        for option in options:
            # Index 3 now holds the list of input formats
            input_formats = option[3]
            if input_formats:
                for fmt in input_formats:
                    extensions.add(fmt.lower())
    return extensions

VALID_INPUT_EXTENSIONS = get_all_input_extensions()

def get_conversion_map():
    """Creates a map of {choice_num: details} including GUI text."""
    conv_map = {}
    for category, options in menu_data:
        for option in options:
            # Unpack including the new GUI text at index 2
            num, cli_text, gui_text, fmts_in, fmt_out, fmt_out2, func = option
            conv_map[num] = {
                'cli_text': cli_text,
                'gui_text': gui_text, # Store the GUI text
                'func': func,
                'formats_in': fmts_in,
                'format_out': fmt_out,
                'format_out2': fmt_out2
            }
    return conv_map

CONVERSION_MAP = get_conversion_map()

# Function needed by CLI still
def get_cli_menu_data():
     """Returns data structured for the original CLI menu function."""
     cli_map = {}
     for category, options in menu_data:
         for option in options:
             num, cli_text, _, fmts_in, fmt_out, fmt_out2, func = option
             cli_map[num] = {'text': cli_text, 'func': func, 'formats_in': fmts_in, 'format_out': fmt_out, 'format_out2': fmt_out2}
     return menu_data, cli_map

