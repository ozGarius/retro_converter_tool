def prepare_job_parameters(selected_job_name, selected_media_name, input_paths,
                           output_format, output_directory, overwrite_files):
    """
    Common logic to prepare job parameters for both GUI and CLI.
    Returns a dictionary with validated parameters or error message.
    """
    job_details = None
    media_type_details = None

    for job in menu_definitions.JOB_DEFINITIONS:
        if job["job_name"] == selected_job_name:
            job_details = job
            for media in job.get("media_types", []):
                if media["media_name"] == selected_media_name:
                    media_type_details = media
                    break
            break

    if not job_details or not media_type_details:
        return {"error": "Invalid job or media type selection"}

    # Calculate output formats
    primary_out_ext = output_format
    secondary_out_ext = None

    possible_primary_outputs = media_type_details.get("output_ext", [])
    possible_secondary_outputs = media_type_details.get("output_ext_secondary")

    # Logic to determine secondary output format based on primary
    if primary_out_ext and isinstance(possible_primary_outputs, list) and primary_out_ext in possible_primary_outputs:
        idx = possible_primary_outputs.index(primary_out_ext)
        if isinstance(possible_secondary_outputs, list) and idx < len(possible_secondary_outputs):
            secondary_out_ext = possible_secondary_outputs[idx]
        elif isinstance(possible_secondary_outputs, str) and idx == 0:
            secondary_out_ext = possible_secondary_outputs

    # Filter input paths to ensure they match expected types
    valid_input_paths = []
    input_extensions = media_type_details.get("input_ext", [])
    for path in input_paths:
        if os.path.isdir(path):
            # Handle directories based on needs
            valid_input_paths.append(path)
        else:
            ext = os.path.splitext(path)[1].lower().lstrip('.')
            if not input_extensions or ext in input_extensions:
                valid_input_paths.append(path)

    return {
        "media_type_details": media_type_details,
        "valid_input_paths": valid_input_paths,
        "primary_out_ext": primary_out_ext,
        "secondary_out_ext": secondary_out_ext,
        "output_directory": output_directory,
        "overwrite_files": overwrite_files,
    }
