# config.py
import os

# --- CORE SETTINGS ---
COPY_LOCALLY = False
DELETE_SOURCE_ON_SUCCESS = False
MAIN_TEMP_DIR = r"C:\TEMP"

# --- TOOL-SPECIFIC SETTINGS ---
DOLPHIN_COMPRESS_LEVEL = 9
VALIDATE_FILE = True

# --- TOOL PATHS ---
# Define paths relative to the main script location.
# config.py is INSIDE convert_tools folder.
# The main script (converter.py) is expected to be ONE LEVEL UP.

# Get the directory where config.py resides (which is convert_tools)
CONFIG_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# TOOLS_DIR is the same directory where config.py is located
TOOLS_DIR = os.path.abspath(CONFIG_SCRIPT_DIR)

# Get the directory containing the convert_tools folder (where converter.py should be)
# This might be needed if utils.py needs to reference the main script's location,
# but for tool paths, TOOLS_DIR is sufficient.
# MAIN_SCRIPT_PARENT_DIR = os.path.dirname(TOOLS_DIR)
TOOL_7ZA = os.path.join(TOOLS_DIR, "ext", '7ZA.exe')
TOOL_DOLPHINTOOL = os.path.join(TOOLS_DIR, "ext", 'DolphinTool.exe')
TOOL_CHDMAN = os.path.join(TOOLS_DIR, "ext", 'chdman.exe')
TOOL_MAXCSO = os.path.join(TOOLS_DIR, "ext", 'maxcso.exe')
TOOL_RECYCLE = os.path.join(TOOLS_DIR, "ext", 'recycle.exe')

# List of essential tools for startup check
ESSENTIAL_TOOLS = [TOOL_7ZA, TOOL_DOLPHINTOOL, TOOL_CHDMAN, TOOL_MAXCSO]
