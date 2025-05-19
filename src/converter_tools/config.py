# config.py
import os
import json
import tempfile  # For OS-agnostic temp directory
import platform  # To check OS


# --- SETTINGS FILE ---
_CONFIG_PY_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE_PATH = os.path.join(_CONFIG_PY_DIR, "converter_settings.json")

# --- OS-dependent TEMP DIR ---


def get_default_temp_dir():
    """Returns a default temporary directory based on the OS."""
    if platform.system() == "Windows":
        base_temp = r"C:\TEMP"
        oz_converter_temp = os.path.join(base_temp, "OzConverter")
        try:
            # Attempt to create C:\TEMP\OzConverter
            # os.makedirs will create parent directories if they don't exist (C:\TEMP in this case)
            # if exist_ok=True is used. However, creating C:\TEMP might require admin rights
            # if C:\ is protected. It's often better to let users manage C:\TEMP or use user-specific temp.
            # For now, we will try to create it.
            os.makedirs(oz_converter_temp, exist_ok=True)
            return oz_converter_temp
        except Exception as e:
            print(
                f"Warning: Could not create or access {oz_converter_temp} (Error: {e}). Falling back to system temp.")
            fallback_dir = os.path.join(tempfile.gettempdir(), "OzConverter")
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir
    else:  # For Linux/macOS
        oz_converter_temp = os.path.join(tempfile.gettempdir(), "OzConverter")
        os.makedirs(oz_converter_temp, exist_ok=True)  # Ensure it exists
        return oz_converter_temp


# --- DEFAULT SETTINGS ---
CPU_COUNT = os.cpu_count() or 1

DEFAULT_SETTINGS = {
    # General Tab
    "COPY_LOCALLY": False,
    "MAIN_TEMP_DIR": get_default_temp_dir(),

    # Process Management
    "SUBPROCESS_TIMEOUT": 3600,

    # CHDMAN Tab - General
    "CHDMAN_NUM_PROCESSORS_MODE": "auto",
    "CHDMAN_NUM_PROCESSORS_MANUAL": max(1, CPU_COUNT * 2 // 3),

    # CHDMAN Tab - CD
    "CHDMAN_CD_USE_CUSTOM_HUNKS": False,
    "CHDMAN_CD_HUNKS": 18816,
    "CHDMAN_CD_USE_CUSTOM_COMPRESSION": False,
    "CHDMAN_CD_COMPRESSION_TYPES": "cdlz,cdzl,cdfl",

    # CHDMAN Tab - DVD
    "CHDMAN_DVD_USE_CUSTOM_HUNKS": False,
    "CHDMAN_DVD_HUNKS": 4096,
    "CHDMAN_DVD_USE_CUSTOM_COMPRESSION": False,
    "CHDMAN_DVD_COMPRESSION_TYPES": "lzma,zlib,huff,flac",

    # CHDMAN Tab - LaserDisc
    "CHDMAN_LD_USE_CUSTOM_HUNKS": False,
    "CHDMAN_LD_HUNKS": 4096,
    "CHDMAN_LD_USE_CUSTOM_COMPRESSION": False,
    "CHDMAN_LD_COMPRESSION_TYPES": "avhu",
    "CHDMAN_LD_USE_INPUT_START_FRAME": False,
    "CHDMAN_LD_INPUT_START_FRAME": None,
    "CHDMAN_LD_USE_INPUT_FRAMES": False,
    "CHDMAN_LD_INPUT_FRAMES": None,

    # CHDMAN Tab - Hard Disk
    "CHDMAN_HD_USE_CUSTOM_HUNKS": False,
    "CHDMAN_HD_HUNKS": 4096,
    "CHDMAN_HD_USE_CUSTOM_COMPRESSION": False,
    "CHDMAN_HD_COMPRESSION_TYPES": "lzma,zlib,huff,flac",
    "CHDMAN_HD_USE_SECTOR_SIZE": False,
    "CHDMAN_HD_SECTOR_SIZE": None,
    "CHDMAN_HD_USE_SIZE": False,
    "CHDMAN_HD_SIZE": None,
    "CHDMAN_HD_USE_CHS": False,
    "CHDMAN_HD_CHS_C": None,
    "CHDMAN_HD_CHS_H": None,
    "CHDMAN_HD_CHS_S": None,
    "CHDMAN_HD_USE_TEMPLATE": False,
    "CHDMAN_HD_TEMPLATE_PATH": None,

    # CHDMAN Tab - Raw
    "CHDMAN_RAW_USE_CUSTOM_HUNKS": False,
    "CHDMAN_RAW_HUNKS": 4096,
    "CHDMAN_RAW_USE_CUSTOM_COMPRESSION": False,
    "CHDMAN_RAW_COMPRESSION_TYPES": "lzma,zlib,huff,flac",

    # CHDMAN Tab - Verify
    "CHDMAN_VERIFY_FIX": False,

    # DolphinTool Tab - RVZ
    "DOLPHINTOOL_RVZ_BLOCKSIZE": 131072,
    "DOLPHINTOOL_RVZ_COMPRESSION_TYPE": "zstd",
    "DOLPHINTOOL_RVZ_COMPRESSION_LEVEL": 5,

    # DolphinTool Tab - WIA
    "DOLPHINTOOL_WIA_COMPRESSION_TYPE": "none",
    "DOLPHINTOOL_WIA_COMPRESSION_LEVEL": 5,

    # DolphinTool Tab - GCZ
    "DOLPHINTOOL_GCZ_BLOCKSIZE": 131072,

    # Legacy/Other settings
    "DELETE_SOURCE_ON_SUCCESS": False,
    "VALIDATE_FILE": True,
    "DOLPHIN_COMPRESS_LEVEL": 9,
}

# --- Initialize settings variables with defaults at module level ---
# This ensures they are available as config.VARIABLE_NAME
COPY_LOCALLY = DEFAULT_SETTINGS["COPY_LOCALLY"]
MAIN_TEMP_DIR = DEFAULT_SETTINGS["MAIN_TEMP_DIR"]
DELETE_SOURCE_ON_SUCCESS = DEFAULT_SETTINGS["DELETE_SOURCE_ON_SUCCESS"]
VALIDATE_FILE = DEFAULT_SETTINGS["VALIDATE_FILE"]
# This was missing in your version
SUBPROCESS_TIMEOUT = DEFAULT_SETTINGS["SUBPROCESS_TIMEOUT"]

CHDMAN_NUM_PROCESSORS_MODE = DEFAULT_SETTINGS["CHDMAN_NUM_PROCESSORS_MODE"]
CHDMAN_NUM_PROCESSORS_MANUAL = DEFAULT_SETTINGS["CHDMAN_NUM_PROCESSORS_MANUAL"]
CHDMAN_CD_USE_CUSTOM_HUNKS = DEFAULT_SETTINGS["CHDMAN_CD_USE_CUSTOM_HUNKS"]
CHDMAN_CD_HUNKS = DEFAULT_SETTINGS["CHDMAN_CD_HUNKS"]
CHDMAN_CD_USE_CUSTOM_COMPRESSION = DEFAULT_SETTINGS["CHDMAN_CD_USE_CUSTOM_COMPRESSION"]
CHDMAN_CD_COMPRESSION_TYPES = DEFAULT_SETTINGS["CHDMAN_CD_COMPRESSION_TYPES"]
CHDMAN_DVD_USE_CUSTOM_HUNKS = DEFAULT_SETTINGS["CHDMAN_DVD_USE_CUSTOM_HUNKS"]
CHDMAN_DVD_HUNKS = DEFAULT_SETTINGS["CHDMAN_DVD_HUNKS"]
CHDMAN_DVD_USE_CUSTOM_COMPRESSION = DEFAULT_SETTINGS["CHDMAN_DVD_USE_CUSTOM_COMPRESSION"]
CHDMAN_DVD_COMPRESSION_TYPES = DEFAULT_SETTINGS["CHDMAN_DVD_COMPRESSION_TYPES"]
CHDMAN_LD_USE_CUSTOM_HUNKS = DEFAULT_SETTINGS["CHDMAN_LD_USE_CUSTOM_HUNKS"]
CHDMAN_LD_HUNKS = DEFAULT_SETTINGS["CHDMAN_LD_HUNKS"]
CHDMAN_LD_USE_CUSTOM_COMPRESSION = DEFAULT_SETTINGS["CHDMAN_LD_USE_CUSTOM_COMPRESSION"]
CHDMAN_LD_COMPRESSION_TYPES = DEFAULT_SETTINGS["CHDMAN_LD_COMPRESSION_TYPES"]
CHDMAN_LD_USE_INPUT_START_FRAME = DEFAULT_SETTINGS["CHDMAN_LD_USE_INPUT_START_FRAME"]
CHDMAN_LD_INPUT_START_FRAME = DEFAULT_SETTINGS["CHDMAN_LD_INPUT_START_FRAME"]
CHDMAN_LD_USE_INPUT_FRAMES = DEFAULT_SETTINGS["CHDMAN_LD_USE_INPUT_FRAMES"]
CHDMAN_LD_INPUT_FRAMES = DEFAULT_SETTINGS["CHDMAN_LD_INPUT_FRAMES"]
CHDMAN_HD_USE_CUSTOM_HUNKS = DEFAULT_SETTINGS["CHDMAN_HD_USE_CUSTOM_HUNKS"]
CHDMAN_HD_HUNKS = DEFAULT_SETTINGS["CHDMAN_HD_HUNKS"]
CHDMAN_HD_USE_CUSTOM_COMPRESSION = DEFAULT_SETTINGS["CHDMAN_HD_USE_CUSTOM_COMPRESSION"]
CHDMAN_HD_COMPRESSION_TYPES = DEFAULT_SETTINGS["CHDMAN_HD_COMPRESSION_TYPES"]
CHDMAN_HD_USE_SECTOR_SIZE = DEFAULT_SETTINGS["CHDMAN_HD_USE_SECTOR_SIZE"]
CHDMAN_HD_SECTOR_SIZE = DEFAULT_SETTINGS["CHDMAN_HD_SECTOR_SIZE"]
CHDMAN_HD_USE_SIZE = DEFAULT_SETTINGS["CHDMAN_HD_USE_SIZE"]
CHDMAN_HD_SIZE = DEFAULT_SETTINGS["CHDMAN_HD_SIZE"]
CHDMAN_HD_USE_CHS = DEFAULT_SETTINGS["CHDMAN_HD_USE_CHS"]
CHDMAN_HD_CHS_C = DEFAULT_SETTINGS["CHDMAN_HD_CHS_C"]
CHDMAN_HD_CHS_H = DEFAULT_SETTINGS["CHDMAN_HD_CHS_H"]
CHDMAN_HD_CHS_S = DEFAULT_SETTINGS["CHDMAN_HD_CHS_S"]
CHDMAN_HD_USE_TEMPLATE = DEFAULT_SETTINGS["CHDMAN_HD_USE_TEMPLATE"]
CHDMAN_HD_TEMPLATE_PATH = DEFAULT_SETTINGS["CHDMAN_HD_TEMPLATE_PATH"]
CHDMAN_RAW_USE_CUSTOM_HUNKS = DEFAULT_SETTINGS["CHDMAN_RAW_USE_CUSTOM_HUNKS"]
CHDMAN_RAW_HUNKS = DEFAULT_SETTINGS["CHDMAN_RAW_HUNKS"]
CHDMAN_RAW_USE_CUSTOM_COMPRESSION = DEFAULT_SETTINGS["CHDMAN_RAW_USE_CUSTOM_COMPRESSION"]
CHDMAN_RAW_COMPRESSION_TYPES = DEFAULT_SETTINGS["CHDMAN_RAW_COMPRESSION_TYPES"]
CHDMAN_VERIFY_FIX = DEFAULT_SETTINGS["CHDMAN_VERIFY_FIX"]
DOLPHINTOOL_RVZ_BLOCKSIZE = DEFAULT_SETTINGS["DOLPHINTOOL_RVZ_BLOCKSIZE"]
DOLPHINTOOL_RVZ_COMPRESSION_TYPE = DEFAULT_SETTINGS["DOLPHINTOOL_RVZ_COMPRESSION_TYPE"]
DOLPHINTOOL_RVZ_COMPRESSION_LEVEL = DEFAULT_SETTINGS["DOLPHINTOOL_RVZ_COMPRESSION_LEVEL"]
DOLPHINTOOL_WIA_COMPRESSION_TYPE = DEFAULT_SETTINGS["DOLPHINTOOL_WIA_COMPRESSION_TYPE"]
DOLPHINTOOL_WIA_COMPRESSION_LEVEL = DEFAULT_SETTINGS["DOLPHINTOOL_WIA_COMPRESSION_LEVEL"]
DOLPHINTOOL_GCZ_BLOCKSIZE = DEFAULT_SETTINGS["DOLPHINTOOL_GCZ_BLOCKSIZE"]
DOLPHIN_COMPRESS_LEVEL = DEFAULT_SETTINGS["DOLPHIN_COMPRESS_LEVEL"]


def _apply_default_settings_to_globals():  # This is now more of a reset function if needed
    """Helper to apply all default settings from DEFAULT_SETTINGS to global variables."""
    for key, value in DEFAULT_SETTINGS.items():
        globals()[key] = value
    # Ensure this is re-evaluated
    globals()["MAIN_TEMP_DIR"] = get_default_temp_dir()


def load_app_settings():
    """Loads settings from the JSON file into the global config variables."""
    # Globals are already initialized with defaults at module scope.
    # This function will override them if a settings file is found and valid.

    if os.path.exists(SETTINGS_FILE_PATH):
        try:
            with open(SETTINGS_FILE_PATH, 'r') as f:
                loaded_settings = json.load(f)

            for key, default_value in DEFAULT_SETTINGS.items():
                # Use loaded value if key exists in file, otherwise keep the module-level default
                if key in loaded_settings:
                    globals()[key] = loaded_settings[key]

            # Specific handling for MAIN_TEMP_DIR to ensure it's valid and exists
            loaded_main_temp_dir = loaded_settings.get("MAIN_TEMP_DIR")
            if loaded_main_temp_dir:
                globals()["MAIN_TEMP_DIR"] = loaded_main_temp_dir
                try:
                    os.makedirs(loaded_main_temp_dir, exist_ok=True)
                except Exception as e:
                    print(
                        f"Warning: Could not create loaded MAIN_TEMP_DIR '{loaded_main_temp_dir}': {e}. Using default.")
                    # Fallback
                    globals()["MAIN_TEMP_DIR"] = get_default_temp_dir()
            else:  # If not in file or empty string, ensure default is used and created
                globals()["MAIN_TEMP_DIR"] = get_default_temp_dir()

            # Handle transition from old DOLPHIN_COMPRESS_LEVEL
            if "DOLPHIN_COMPRESS_LEVEL" in loaded_settings and "DOLPHINTOOL_RVZ_COMPRESSION_LEVEL" not in loaded_settings:
                globals()["DOLPHINTOOL_RVZ_COMPRESSION_LEVEL"] = loaded_settings.get(
                    "DOLPHIN_COMPRESS_LEVEL", DEFAULT_SETTINGS["DOLPHINTOOL_RVZ_COMPRESSION_LEVEL"])

            globals()["DOLPHIN_COMPRESS_LEVEL"] = globals()[
                "DOLPHINTOOL_RVZ_COMPRESSION_LEVEL"]

            print(f"Settings loaded from: {SETTINGS_FILE_PATH}")

        except json.JSONDecodeError:
            print(
                f"ERROR: Could not decode JSON from {SETTINGS_FILE_PATH}. Using module-level default settings.")
        except Exception as e:
            print(
                f"ERROR: Could not load settings from {SETTINGS_FILE_PATH}: {e}. Using module-level default settings.")
    else:
        print(
            f"Settings file not found at {SETTINGS_FILE_PATH}. Using module-level default settings. File will be created on next save.")


def save_app_settings():
    """Saves the current global config variables to the JSON file."""
    settings_to_save = {}
    for key in DEFAULT_SETTINGS.keys():
        settings_to_save[key] = globals().get(key)

    settings_to_save["DOLPHIN_COMPRESS_LEVEL"] = globals().get(
        "DOLPHINTOOL_RVZ_COMPRESSION_LEVEL")

    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE_PATH), exist_ok=True)
        main_temp_directory = globals().get("MAIN_TEMP_DIR")
        if main_temp_directory:  # Ensure the specified temp dir exists
            try:
                os.makedirs(main_temp_directory, exist_ok=True)
            except Exception as e:
                print(
                    f"Warning: Could not create specified MAIN_TEMP_DIR '{main_temp_directory}' during save: {e}")

        with open(SETTINGS_FILE_PATH, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
        print(f"Settings saved to: {SETTINGS_FILE_PATH}")
    except Exception as e:
        print(f"ERROR: Could not save settings to {SETTINGS_FILE_PATH}: {e}")


# --- TOOL PATHS ---
TOOLS_DIR = _CONFIG_PY_DIR
TOOL_7ZA = os.path.join(TOOLS_DIR, "ext", '7ZA.exe')
TOOL_DOLPHINTOOL = os.path.join(TOOLS_DIR, "ext", 'DolphinTool.exe')
TOOL_CHDMAN = os.path.join(TOOLS_DIR, "ext", 'chdman.exe')
TOOL_MAXCSO = os.path.join(TOOLS_DIR, "ext", 'maxcso.exe')
TOOL_RECYCLE = os.path.join(TOOLS_DIR, "ext", 'recycle.exe')
ESSENTIAL_TOOLS = [TOOL_7ZA, TOOL_DOLPHINTOOL, TOOL_CHDMAN, TOOL_MAXCSO]

# --- Load settings when the module is imported ---
load_app_settings()
