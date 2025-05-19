# converter_tools/menu_definitions.py
"""
Defines the job structure and conversion options for the tool,
mapping them to conversion functions and UI elements.
"""
import os
try:
    # This import is primarily for type hinting or if we later want to
    # store actual function references directly, though getattr() is safer for loose coupling.
    import conversions
except ImportError:
    print("ERROR: menu_definitions.py could not import conversions.py (this might be okay if only names are used)")
    pass  # Allow to proceed if only function names are stored

# --- NEW JOB-BASED DEFINITIONS ---

JOB_DEFINITIONS = [
    {
        "job_name": "Compress media",
        "action_text": "COMPRESS",
        "media_types": [
            {
                "media_name": "CD image",
                "input_ext": ["iso", "img", "cue", "toc", "gdi", "7z", "zip", "rar"],
                "output_ext": ["chd"],
                "output_ext_secondary": None,
                "conversion_func_name": "compress_discimage_to_chd_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "DVD image",
                "input_ext": ["iso", "7z", "zip", "rar", "gz"],
                "output_ext": ["chd"],
                "output_ext_secondary": None,
                "conversion_func_name": "compress_dvdimage_to_chd_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "GameCube/Wii",
                "input_ext": ["iso", "gcz", "wia", "rvz", "7z", "zip", "rar"],
                "output_ext": ["rvz", "gcz", "wia"],
                "output_ext_secondary": None,
                "conversion_func_name": "compress_dolphin_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "Hard Disk image",
                "input_ext": ["img", "7z", "zip", "rar"],
                "output_ext": ["chd"],
                "output_ext_secondary": None,
                "conversion_func_name": "compress_harddisk_to_chd_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "LaserDisc image",
                "input_ext": ["raw", "7z", "zip", "rar"],
                "output_ext": ["chd"],
                "output_ext_secondary": None,
                "conversion_func_name": "compress_laserdisc_to_chd_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "Raw image",
                "input_ext": ["img", "raw", "7z", "zip", "rar"],
                "output_ext": ["chd"],
                "output_ext_secondary": None,
                "conversion_func_name": "compress_raw_to_chd_routine",
                "requires_output_folder": True,
            }
        ]
    },
    {
        "job_name": "Extract media",
        "action_text": "EXTRACT",
        "media_types": [
            {
                "media_name": "CD image",
                "input_ext": ["chd"],
                "output_ext": ["cue", "toc", "gdi", "iso"],
                "output_ext_secondary": ["bin", "bin", "bin", None],
                "conversion_func_name": "extract_chd_to_cd_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "DVD image",
                "input_ext": ["chd"],
                "output_ext": ["iso"],
                "output_ext_secondary": None,
                "conversion_func_name": "extract_chd_to_dvd_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "GameCube/Wii",
                "input_ext": ["rvz", "gcz", "wia"],
                "output_ext": ["iso"],
                "output_ext_secondary": None,
                "conversion_func_name": "extract_dolphin_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "Hard Disk image",
                "input_ext": ["chd"],
                "output_ext": ["img"],
                "output_ext_secondary": None,
                "conversion_func_name": "extract_chd_to_harddisk_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "LaserDisc image",
                "input_ext": ["raw"],
                "output_ext": ["iso"],
                "output_ext_secondary": None,
                "conversion_func_name": "extract_chd_to_laserdisc_routine",
                "requires_output_folder": True,
            },
            {
                "media_name": "Raw image",
                "input_ext": ["chd"],
                "output_ext": ["img", "raw"],
                "output_ext_secondary": None,
                "conversion_func_name": "extract_chd_to_raw_routine",
                "requires_output_folder": True,
            }
        ]
    },
    {
        "job_name": "Get info from media",
        "action_text": "GET INFO",
        "media_types": [
            {
                "media_name": "CHD Info (CD/DVD/HD/LD)",
                "input_ext": ["chd"],
                "output_ext": [],  # No file output, text goes to log
                "output_ext_secondary": None,
                "action_text": "GET INFO",
                "conversion_func_name": "get_chd_info_routine",
                "requires_output_folder": False,  # No output folder needed
            },
            # # This job might not produce output files in the same way.
            # # The 'conversion_func_name' would point to a new function in conversions.py
            # # that runs e.g. 'chdman info ...' and returns the info string.
            # # 'requires_output_folder' would likely be False.
            # {
            #     "media_name": "CHD info",
            #     "input_ext": ["chd"],
            #     "output_ext": [], # Or None, as it's info
            #     "action_text": "GET INFO",
            #     "conversion_func_name": "get_chd_info_routine", # Example new function
            #     "requires_output_folder": False,
            # }
        ]
    },
    {
        "job_name": "Verify media",
        "action_text": "VERIFY",
        "media_types": [
            {
                "media_name": "Verify CHD (CD/DVD/HD/LD)",
                "input_ext": ["chd"],
                "output_ext": [],  # No file output, result goes to log
                "output_ext_secondary": None,
                "action_text": "VERIFY MEDIA",
                "conversion_func_name": "verify_chd_routine",
                "requires_output_folder": False,  # No output folder needed
            },
            # Example for other verify types:
            # {
            #     "media_name": "Verify RVZ (if tool supports)",
            #     "input_ext": ["rvz"],
            #     "output_ext": [],
            #     "action_text": "VERIFY MEDIA",
            #     "conversion_func_name": "verify_rvz_routine", # Needs to be created
            #     "requires_output_folder": False,
            # }
        ]
    },
]


# --- Helper function to get all possible input extensions from JOB_DEFINITIONS ---
def get_all_job_input_extensions():
    """Retrieves a list of all unique input file extensions used across all defined jobs."""
    extensions = set()
    for job in JOB_DEFINITIONS:
        for media_type in job.get("media_types", []):
            for ext in media_type.get("input_ext", []):
                extensions.add(ext.lower())
    return list(extensions)


ALL_VALID_INPUT_EXTENSIONS = get_all_job_input_extensions()


def get_job_media_details(job_name_selected, media_name_selected):
    """Retrieves the details for a specific job and media type."""
    for job in JOB_DEFINITIONS:
        if job["job_name"] == job_name_selected:
            for media_type in job["media_types"]:
                if media_type["media_name"] == media_name_selected:
                    return media_type
    return None
