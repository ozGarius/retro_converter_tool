ADDING NEW CONVERSION FORMATS
=============================

This guide explains how to add support for a new file conversion type to the modular converter tool.

Prerequisites:
--------------
* You need a command-line tool capable of performing the desired conversion (e.g., xyz_converter.exe).
* Place the executable file for the tool inside the 'convert_tools' directory.

Steps:
------

1. Add Tool Path (if necessary):
   -----------------------------
   * Open the 'convert_tools/config.py' file.
   * If you are using a *new* command-line tool that isn't already listed (like 7za.exe, chdman.exe, etc.), add a new variable pointing to it. Follow the existing pattern:

     # Example for a new tool
     TOOL_XYZCONVERTER = os.path.join(TOOLS_DIR, 'xyz_converter.exe')

   * Also, add this new tool variable to the `ESSENTIAL_TOOLS` list in `config.py` if the script should check for its existence on startup:

     ESSENTIAL_TOOLS = [..., TOOL_XYZCONVERTER]

2. Create Conversion Function:
   --------------------------
   * Open the 'convert_tools/conversions.py' file.
   * Define a new Python function that will handle the specific steps for your conversion. Name it descriptively, following the pattern `convert_input_to_output_routine`.
   * This function must accept three arguments: `processing_path` (path to the input file, potentially in a temp dir), `temp_dir` (path to the temporary directory), and `name` (original base filename without extension).
   * Inside the function:
     * Use `utils.run_command()` to execute the necessary command-line tool(s). Reference tool paths from the `config` module (e.g., `config.TOOL_XYZCONVERTER`).
     * Construct input and output file paths using `os.path.join()`. Often, output files should be placed in the `temp_dir`.
     * Check if the command was successful and if the expected output file(s) were created in `temp_dir` and are not empty (`os.path.exists()` and `os.path.getsize()`).
     * Return `True` on success, `False` on failure.

   * Example Function Structure:

     # In convert_tools/conversions.py
     import os
     import config
     import utils

     def convert_abc_to_xyz_routine(processing_path, temp_dir, name):
         """Converts ABC files to XYZ format."""
         print(f">> Converting ABC to XYZ: \"{os.path.basename(processing_path)}\"")
         output_xyz_path = os.path.join(temp_dir, f"{name}.xyz") # Define expected output

         # Construct the command using config variables
         command = [
             config.TOOL_XYZCONVERTER,
             '-i', processing_path,      # Input file
             '-o', output_xyz_path,     # Output file in temp dir
             '--some-option'            # Other necessary tool options
         ]

         # Execute the command
         if not utils.run_command(command):
             print(f"ERROR: xyz_converter.exe failed.")
             return False # Indicate failure

         # Verify output exists and is not empty
         if not os.path.exists(output_xyz_path) or os.path.getsize(output_xyz_path) == 0:
             print(f"ERROR: Output file \"{os.path.basename(output_xyz_path)}\" was not created or is empty.")
             return False # Indicate failure

         print(f"Successfully created {os.path.basename(output_xyz_path)}.")
         return True # Indicate success


3. Add Menu Option:
   ---------------
   * Open the main 'converter.py' file.
   * Locate the `menu_data` list inside the `print_menu()` function.
   * Find the appropriate category list (e.g., `["Archiving", [...]]`) or create a new one.
   * Add a new list entry for your conversion within the category list. Follow this structure:

     # Example entry in menu_data
     ['99', "ABC to XYZ", ['abc'], 'xyz', None, conversions.convert_abc_to_xyz_routine],
     #  ^     ^           ^        ^      ^      ^
     #  |     |           |        |      |      |
     # Choice | Menu Text | Input  | Pri. | Sec. | Function in conversions.py
     # Number |           | Ext(s) | Out  | Out  | (Use None for special handling
     #        |           | (List) | Ext  | Ext  |  like audio options 80/81)

     * Assign a unique `Choice Number` (string).
     * Provide descriptive `Menu Text`.
     * List the valid `Input Ext(s)` (lowercase strings, without the dot).
     * Specify the primary `Pri. Out Ext` (lowercase string, without the dot) that `utils.process_file` should look for to move back from the temp directory.
     * Specify the `Sec. Out Ext` only if the conversion produces a second essential file type (like `.bin` for CUE/BIN). Otherwise, use `None`.
     * Reference the conversion function you created in `conversions.py` using the `conversions.` prefix (e.g., `conversions.convert_abc_to_xyz_routine`).

4. Test:
   ----
   * Run `converter.py`.
   * Verify your new option appears correctly in the menu.
   * Test the conversion with appropriate input files/folders.

By following these steps, you can integrate new conversion capabilities while maintaining the modular structure of the tool.
