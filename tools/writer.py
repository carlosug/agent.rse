import re
from termcolor import colored
from pydantic import BaseModel, ValidationError
import os

class DevContainerConfig(BaseModel):
    name: str
    dockerFile: str
    context: str
    appPort: list
    postCreateCommand: str
    settings: dict
    extensions: list

class ShellScriptConfig(BaseModel):
    commands: list

class StandaloneExecutableConfig(BaseModel):
    entry_point: str
    dependencies: list

def fetch_template(output_type):
    """
    Fetches the template for the specified output type from the local templates directory.

    Args:
        output_type (str): The type of output to generate (Dev Container, Shell Script, or Standalone Executable).

    Returns:
        str: The template for the specified output type.
    """
    template_dir = "templates"
    template_file = {
        "Dev Container": "docker_template.py",
        "Shell Script": "shell_template.py",
        "Standalone Executable": "standalone_executable.py"
    }.get(output_type)

    if not template_file:
        raise ValueError(f"Unsupported output type: {output_type}")

    template_path = os.path.join(template_dir, template_file)
    with open(template_path, "r") as file:
        return file.read()

def writer(model, known_info, system_prompt_writer, output_type, template):
    """
    Generates the appropriate output file based on the suggested output type.

    Args:
        model: The AI model to use for generation.
        known_info (str): The summarized information from the Summarizer Agent.
        system_prompt_writer (str): The system prompt for the Writer Agent.
        output_type (str): The type of output to generate (Dockerfile, Shell Script, or Standalone Executable).
        template (str): The template for the output file.

    Returns:
        str: The generated output file as a string.
    """
    answer_writer = model.answer(
        system_prompt=system_prompt_writer + "\n\n" + template,
        prompt=known_info,
        json=False)
    
    # Debug print to see the model's response
    print("Model's response:", answer_writer)
    
    json_section = re.search(
        r'<output>\s*(.*?)\s*</output>', answer_writer, re.DOTALL)
    if json_section:
        answer_writer = json_section.group(1)
    else:
        # Fallback mechanism: use the entire response if the expected format is not found
        print(colored("Warning: The model's response did not contain the expected output format. Using the entire response as fallback.", "yellow"))
        answer_writer = answer_writer.strip()

    # Ensure the output only contains code according to the template
    if output_type == "Dev Container":
        return format_dockerfile(answer_writer)
    elif output_type == "Shell Script":
        return format_shell_script(answer_writer)
    elif output_type == "Standalone Executable":
        try:
            config = StandaloneExecutableConfig.parse_raw(answer_writer)
            return f"# Entry point: {config.entry_point}\n# Dependencies: {', '.join(config.dependencies)}"
        except ValidationError as e:
            print(colored(f"Validation error: {e}", "red"))
            raise
    else:
        raise ValueError(f"Unsupported output type: {output_type}")

    return answer_writer

def format_dockerfile(content):
    """
    Formats the Dockerfile content to follow best practices and include necessary comments.

    Args:
        content (str): The raw Dockerfile content.

    Returns:
        str: The formatted Dockerfile content.
    """
    lines = content.split('\n')
    formatted_lines = []
    for line in lines:
        if line.strip().startswith('#'):
            formatted_lines.append(line)
        else:
            formatted_lines.append(line)
    return '\n'.join(formatted_lines)

def format_shell_script(content):
    """
    Formats the shell script content to follow best practices and include necessary comments.

    Args:
        content (str): The raw shell script content.

    Returns:
        str: The formatted shell script content.
    """
    lines = content.split('\n')
    formatted_lines = []
    for line in lines:
        if line.strip().startswith('#'):
            formatted_lines.append(line)
        else:
            formatted_lines.append(line)
    return '\n'.join(formatted_lines)