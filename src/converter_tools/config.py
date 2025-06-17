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
    "DEBUG_MODE": True,

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
    "DOLPHIN_COMPRESS_LEVEL": 9, # This will be effectively superseded by DOLPHINTOOL_RVZ_COMPRESSION_LEVEL but kept for transition

    # New settings
    "LOG_DIRECTORY": "./logs/", # Relative to app root or a defined base path
    "LAST_USED_DIRECTORY": None, # Stores the last directory used for input/output
}


class AppSettings:
    """
    Holds all application settings, initialized from DEFAULT_SETTINGS.
    """
    def __init__(self):
        for key, value in DEFAULT_SETTINGS.items():
            setattr(self, key, value)

        # Ensure MAIN_TEMP_DIR is processed by get_default_temp_dir() if it's not already.
        # In the current DEFAULT_SETTINGS, MAIN_TEMP_DIR is already correctly initialized using get_default_temp_dir(),
        # so the loop above is sufficient. If MAIN_TEMP_DIR were a simple path string in DEFAULT_SETTINGS,
        # it might need special handling here, e.g.:
        # if not os.path.isabs(self.MAIN_TEMP_DIR) or not os.path.exists(self.MAIN_TEMP_DIR):
        #     self.MAIN_TEMP_DIR = get_default_temp_dir()
        # However, this is not currently needed due to the structure of DEFAULT_SETTINGS.

    def load(self, file_path):
        """Loads settings from the JSON file into the instance's attributes."""
        if not os.path.exists(file_path):
            print(f"Settings file not found at {file_path}. Using default settings.")
            return

        try:
            with open(file_path, 'r') as f:
                loaded_data = json.load(f)
        except FileNotFoundError: # Should be caught by os.path.exists, but good practice
            print(f"ERROR: Settings file disappeared before it could be read: {file_path}. Using default settings.")
            return
        except json.JSONDecodeError:
            print(f"ERROR: Could not decode JSON from {file_path}. Using default settings.")
            return
        except Exception as e:
            print(f"ERROR: Could not load settings from {file_path}: {e}. Using default settings.")
            return

        for key in DEFAULT_SETTINGS.keys(): # Iterate over known default keys to avoid polluting self with unknown keys
            if key in loaded_data:
                # For now, directly set the attribute. Type validation/coercion can be added later.
                setattr(self, key, loaded_data[key])

        # Special handling for MAIN_TEMP_DIR
        if hasattr(self, "MAIN_TEMP_DIR") and self.MAIN_TEMP_DIR:
            try:
                os.makedirs(self.MAIN_TEMP_DIR, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create loaded MAIN_TEMP_DIR '{self.MAIN_TEMP_DIR}': {e}. Resetting to default.")
                self.MAIN_TEMP_DIR = get_default_temp_dir()
                # Ensure the default one is also created if it somehow wasn't
                try:
                    os.makedirs(self.MAIN_TEMP_DIR, exist_ok=True)
                except Exception as e_default_mkdir:
                    print(f"ERROR: Could not create default MAIN_TEMP_DIR '{self.MAIN_TEMP_DIR}': {e_default_mkdir}. Temp operations may fail.")

        else: # If MAIN_TEMP_DIR is not in settings or is empty, use default
            self.MAIN_TEMP_DIR = get_default_temp_dir()

        # Handle transition from old DOLPHIN_COMPRESS_LEVEL
        if "DOLPHIN_COMPRESS_LEVEL" in loaded_data and "DOLPHINTOOL_RVZ_COMPRESSION_LEVEL" not in loaded_data:
            # Ensure the attribute exists on self first (it should due to __init__)
            if hasattr(self, "DOLPHINTOOL_RVZ_COMPRESSION_LEVEL"):
                self.DOLPHINTOOL_RVZ_COMPRESSION_LEVEL = loaded_data.get("DOLPHIN_COMPRESS_LEVEL", DEFAULT_SETTINGS["DOLPHINTOOL_RVZ_COMPRESSION_LEVEL"])

        # Ensure DOLPHIN_COMPRESS_LEVEL attribute reflects DOLPHINTOOL_RVZ_COMPRESSION_LEVEL
        if hasattr(self, "DOLPHINTOOL_RVZ_COMPRESSION_LEVEL"):
             self.DOLPHIN_COMPRESS_LEVEL = self.DOLPHINTOOL_RVZ_COMPRESSION_LEVEL


        print(f"Settings loaded into AppSettings instance from: {file_path}")

    def save(self, file_path):
        """Saves the current instance attributes to the JSON file."""
        settings_to_save = {}
        for key in DEFAULT_SETTINGS.keys(): # Iterate over known default keys
            if hasattr(self, key):
                settings_to_save[key] = getattr(self, key)
            else: # Should not happen if __init__ ran correctly
                settings_to_save[key] = DEFAULT_SETTINGS[key]

        # Ensure DOLPHIN_COMPRESS_LEVEL in the saved file reflects current RVZ compression level
        if hasattr(self, "DOLPHINTOOL_RVZ_COMPRESSION_LEVEL"):
            settings_to_save["DOLPHIN_COMPRESS_LEVEL"] = self.DOLPHINTOOL_RVZ_COMPRESSION_LEVEL

        try:
            # Ensure parent directory for settings file exists
            parent_dir = os.path.dirname(file_path)
            if parent_dir: # Check if parent_dir is not empty (e.g. for relative file_path in current dir)
                os.makedirs(parent_dir, exist_ok=True)

            # Ensure MAIN_TEMP_DIR exists
            if hasattr(self, "MAIN_TEMP_DIR") and self.MAIN_TEMP_DIR:
                try:
                    os.makedirs(self.MAIN_TEMP_DIR, exist_ok=True)
                except Exception as e:
                    print(f"Warning: Could not create specified MAIN_TEMP_DIR '{self.MAIN_TEMP_DIR}' during save: {e}")

            with open(file_path, 'w') as f:
                json.dump(settings_to_save, f, indent=4)
            print(f"AppSettings instance saved to: {file_path}")
        except Exception as e:
            print(f"ERROR: Could not save AppSettings instance to {file_path}: {e}")


# Create a global instance of AppSettings
settings = AppSettings()


# The old module-level global variables for settings are now removed.
# Access settings via the 'settings' instance, e.g., config.settings.COPY_LOCALLY

# The _apply_default_settings_to_globals function is also removed as it's no longer needed.


def load_app_settings():
    """Loads settings from the JSON file into the global 'settings' instance."""
    settings.load(SETTINGS_FILE_PATH)


def save_app_settings():
    """Saves the current settings from the global 'settings' instance to the JSON file."""
    settings.save(SETTINGS_FILE_PATH)


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
