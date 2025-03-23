import os
import subprocess
from termcolor import colored

def validate_dockerfile(dockerfile_content):
    """
    Validates the Dockerfile content using the Hadolint CLI.

    Args:
        dockerfile_content (str): The content of the Dockerfile to validate.

    Returns:
        str: The validation status ("Correct", "Information", or "Format").
    """
    with open("Dockerfile.temp", "w") as file:
        file.write(dockerfile_content)

    try:
        result = subprocess.run(['hadolint', 'Dockerfile.temp'], capture_output=True, text=True, check=True)
        print(colored(f"Dockerfile validation passed:\n{result.stdout}", "green"))
        return "Correct"
    except subprocess.CalledProcessError as e:
        print(colored(f"Dockerfile validation failed:\n{e.stderr}", "red"))
        return "Format"
    finally:
        os.remove("Dockerfile.temp")

def validator(model, writer_response, system_prompt_validator, output_type, template):
    """
    Validates the generated output file based on its type.

    Args:
        model: The AI model to use for validation.
        writer_response (str): The generated output file.
        system_prompt_validator (str): The system prompt for the Validator Agent.
        output_type (str): The type of output to validate (Dockerfile, Shell Script, or Standalone Executable).
        template (str): The template for the output file.

    Returns:
        str: The validation status ("Correct", "Information", or "Format").
    """
    if output_type == "Dev Container":
        validation_status = validate_dockerfile(writer_response)
    elif output_type == "Shell Script":
        # Add shell script validation logic here
        validation_status = "Correct"  # Placeholder
    elif output_type == "Standalone Executable":
        # Add standalone executable validation logic here
        validation_status = "Correct"  # Placeholder
    else:
        raise ValueError(f"Unsupported output type: {output_type}")

    print(colored(f"Validator: My verdict is -> {validation_status}", "red"))
    return validation_status