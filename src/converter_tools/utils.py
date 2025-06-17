import os
import re
import sys
import ctypes # For Windows hidden attribute
import shutil # For Unix rename (if chosen over just creating dot-prefixed)

def clean_filename_for_playlist(filename: str) -> str:
    if not filename:
        return "playlist" # Default if input is empty

    name = str(filename) # Ensure it's a string

    # Patterns from M3UCreatorWindow._temporary_clean_filename
    patterns = [
        r'\s*\(Disc\s*\d+(?:\s*of\s*\d+)?\)\s*', r'\s*\(CD\s*\d*(?:\s*of\s*\d+)?\)\s*',
        r'\s*\(Disk\s*\d+(?:\s*of\s*\d+)?\)\s*', r'\s*\[.*?\]\s*', # Square brackets and content
        r'\s*\(.*Version.*\)\s*', r'\s*\(Beta\)\s*', r'\s*\(Proto\)\s*',
        r'\s*\((?:USA|US|Europe|EU|Japan|JP|World)\)\s*', # Region tags
        r'\s*\((?:En|Fr|De|Es|It|Nl|Pt|Sv|No|Da|Fi)\)\s*', # Common language tags
        r'\s*\(Rev\s*[\w\.]+\)\s*', r'\s*\(Alternative?\)\s*', r'\s*\(Alt\)\s*', # Revision/Alt tags
        r'\s*\(Unl(?:icensed)?\)\s*', # Unlicensed
        r'\s*\(Track\s*\d+\)\s*', r'\s*\(Bonus Disc\)\s*', r'\s*\(Game\s*\d*\)\s*',
        r'\s*\(Side\s*[AB12]\)\s*',
        r'\(Demo\)\s*', r'\(Sample\)\s*', r'\(Promo\)\s*',
        r'\(Enhanced\)\s*', r'\(Remastered\)\s*', r'\(Limited Edition\)\s*',
        r'\(Collector's Edition\)\s*',
        # Specific example from issue
        r'\s*\(\s*CD\s*\d+\s*of\s*\d+\s*\)\s*',
        r'\s*\(\s*Disc\s*\d+\s*of\s*\d+\s*\)\s*',
    ]
    for pattern in patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # Remove any leading/trailing spaces, underscores, hyphens
    name = name.strip(' _-')
    # Replace multiple spaces or underscores with a single space
    name = re.sub(r'[\s_]+', ' ', name)
    # Normalize spacing around hyphens (e.g., "name - subtitle" to "name-subtitle" if desired, or keep space)
    # For now, just ensure single space around them if they are meant to be word separators
    name = re.sub(r'\s*-\s*', ' - ', name) # Ensures space around hyphen if present
    name = name.strip() # Final strip

    # If after all cleaning the name is empty, return a default
    return name if name else "playlist"

def set_folder_hidden_attribute(folder_path: str):
    """
    Sets the hidden attribute for a folder.
    On Windows, uses ctypes to call SetFileAttributesW.
    On Unix-like systems (Linux, macOS), prepends a '.' to the folder name if not already present.
    Note: Renaming on Unix might fail if the target name exists or due to permissions.
    """
    if not os.path.isdir(folder_path):
        # Or raise ValueError("Folder does not exist or is not a directory.")
        print(f"Warning: Folder '{folder_path}' not found or is not a directory. Cannot set hidden attribute.", file=sys.stderr)
        return False

    system_platform = sys.platform.lower()

    try:
        if system_platform.startswith("win"): # Windows
            FILE_ATTRIBUTE_HIDDEN = 0x02
            # Ensure path is unicode for ctypes
            ret = ctypes.windll.kernel32.SetFileAttributesW(str(folder_path), FILE_ATTRIBUTE_HIDDEN)
            if not ret: # SetFileAttributes returns 0 on failure
                # You might want to raise an exception here or get last error
                # For now, just print error from ctypes.WinError()
                error_code = ctypes.get_last_error()
                ctypes_error = ctypes.WinError(error_code)
                print(f"Error setting hidden attribute on '{folder_path}': {ctypes_error} (Code: {error_code})", file=sys.stderr)
                return False
            return True

        elif system_platform.startswith("linux") or system_platform.startswith("darwin"): # Linux or macOS
            folder_basename = os.path.basename(folder_path)
            folder_dirname = os.path.dirname(folder_path)

            if not folder_basename.startswith("."):
                new_hidden_name = "." + folder_basename
                new_full_path = os.path.join(folder_dirname, new_hidden_name)

                if os.path.exists(new_full_path):
                    print(f"Warning: Cannot make '{folder_path}' hidden by renaming. "
                          f"Target '{new_full_path}' already exists.", file=sys.stderr)
                    return False # Or True if it's already hidden effectively by existing dot folder

                shutil.move(folder_path, new_full_path) # shutil.move can rename directories
                print(f"Info: Folder '{folder_path}' renamed to '{new_full_path}' to make it hidden.")
                # Important: The calling code needs to be aware that folder_path has changed if this succeeds.
                # This function should ideally return the new path if it changes.
                # However, the plan was just to set it hidden.
                # For now, this function's contract is just to try and hide it.
                # The caller (M3UCreatorWindow) already has the new_folder_path which would be the dot-prefixed one
                # if the playlist name itself started with a dot.
                # This function is called AFTER the folder is created with its final name.
                # So, if the final name was ".myplaylist", this function on Unix would do nothing.
                # If the final name was "myplaylist", this renames it to ".myplaylist".
            else:
                # Folder already starts with a dot, considered hidden by convention
                print(f"Info: Folder '{folder_path}' already starts with '.', considered hidden on Unix-like systems.")
            return True

        else:
            print(f"Unsupported platform: {system_platform}. Cannot set hidden attribute.", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Exception while trying to set hidden attribute on '{folder_path}': {e}", file=sys.stderr)
        return False

# Example of how to get free disk space (already in gui_main_window.py, but good for utils.py)
def get_free_disk_space_gb(folder_path: str) -> float | None:
    """Returns free disk space in GB for the drive containing folder_path."""
    try:
        stat = os.statvfs(os.path.abspath(folder_path))
        # Calculate free space in GB
        # stat.f_frsize is fundamental file system block size
        # stat.f_bavail is free blocks available to non-superuser
        free_gb = (stat.f_frsize * stat.f_bavail) / (1024 * 1024 * 1024)
        return free_gb
    except AttributeError: # os.statvfs not available on all platforms (e.g. Windows)
        if sys.platform.startswith("win"):
            try:
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(folder_path),
                    ctypes.byref(free_bytes),
                    ctypes.byref(total_bytes),
                    None) # Third param (total_free_bytes) can be None
                return free_bytes.value / (1024 * 1024 * 1024)
            except Exception:
                return None # Failed to get free space on Windows
        return None # Not Windows and no statvfs
    except Exception:
        return None # Other errors

if __name__ == '__main__':
    # Test clean_filename_for_playlist
    test_names = [
        "My Game (Disc 1 of 2) [USA]",
        "Another Game (CD2)",
        "Game Name (Europe) (Rev A) (Track 01)",
        "Test [Proto] (Unknown Version)",
        "  leading and trailing spaces  ",
        "Game_With_Underscores",
        "Empty () [] Test",
        "",
        "My Awesome Game (Demo) (Limited Edition) (Enhanced)",
        "Final Game (Side A)",
        "Game (CD 1 of 4)",
    ]
    for tn in test_names:
        print(f"Original: '{tn}' -> Cleaned: '{clean_filename_for_playlist(tn)}'")

    # Test set_folder_hidden_attribute (manual testing needed for actual effect)
    # Create dummy folders for testing
    test_folder_plain = "test_visible_folder"
    test_folder_dot = ".test_hidden_folder_unix"
    test_folder_win = "test_hidden_folder_win"

    for tf in [test_folder_plain, test_folder_dot, test_folder_win]:
        if os.path.exists(tf):
            if os.path.isdir(tf): shutil.rmtree(tf) # Remove if it's a dir
            else: os.remove(tf) # Remove if it's a file

    os.makedirs(test_folder_plain, exist_ok=True)
    os.makedirs(test_folder_dot, exist_ok=True)
    os.makedirs(test_folder_win, exist_ok=True)

    print(f"\nAttempting to hide '{test_folder_plain}':")
    set_folder_hidden_attribute(test_folder_plain) # On Unix, this should become ".test_visible_folder"

    print(f"Attempting to hide '{test_folder_dot}' (already dot-prefixed for Unix):")
    set_folder_hidden_attribute(test_folder_dot)

    print(f"Attempting to hide '{test_folder_win}' (Windows specific):")
    set_folder_hidden_attribute(test_folder_win) # This will use ctypes on Windows

    # Note: actual verification of hidden status needs manual check or platform-specific commands
    print("\nManual verification needed for hidden status of test folders.")
    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        if os.path.exists(os.path.join(os.path.dirname(test_folder_plain), "." + os.path.basename(test_folder_plain))):
            print(f"'{test_folder_plain}' likely renamed to '.{os.path.basename(test_folder_plain)}'")

    # Clean up test folders
    # for tf in [test_folder_plain, test_folder_dot, test_folder_win, ".test_visible_folder"]: # Also remove renamed one
    #     if os.path.exists(tf) and os.path.isdir(tf):
    #         try:
    #             # On Windows, hidden files might need attribute change before rmtree
    #             if sys.platform.startswith("win") and os.path.basename(tf) == test_folder_win:
    #                 # Attempt to unhide before deleting if it was hidden
    #                 ctypes.windll.kernel32.SetFileAttributesW(str(tf), 0x80) # FILE_ATTRIBUTE_NORMAL
    #             shutil.rmtree(tf)
    #         except Exception as e_clean:
    #             print(f"Error cleaning up test folder {tf}: {e_clean}")
