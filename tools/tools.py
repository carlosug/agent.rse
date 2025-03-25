import subprocess
import os
import shutil
import re
from termcolor import colored
from pydantic import BaseModel, ValidationError
import jsonschema
from jsonschema import validate
from .tool_schema import tools, DevContainerConfig, ShellScriptConfig, StandaloneExecutableConfig

# ------------------------------------------------------------------------------
# UTILS
# ------------------------------------------------------------------------------
def clone_repo(repo_url):
    command = ["git", "clone", "-q", repo_url]
    subprocess.run(command, check=True)

def remove_file(file_name):
    try:
        os.remove(file_name)
        print(f"File {file_name} removed successfully.")
    except OSError as e:
        print(f"Error: {e.strerror} - {e.filename}")

def list_dirs(directory, prefix=""):
    file_paths = []
    for root, _, files in os.walk(directory):
        if ".git" in root:
            continue
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    return file_paths

# ------------------------------------------------------------------------------
# EXECUTOR
# ------------------------------------------------------------------------------
DOCKERFILE_TEMPLATE = """
FROM fedora:latest

# Install necessary packages
RUN dnf install -y python3 python3-pip bash ncurses git

# Copy the script and requirements file to the container
COPY {script_name} /app/{script_name}
COPY requirements.txt /app/requirements.txt

# Set the working directory
WORKDIR /app

# Install Python dependencies
RUN pip3 install -r requirements.txt --root-user-action=ignore

# Execute the script
CMD {execution_command}
"""

def create_dockerfile(script_path, script_type):
    """
    Creates a Dockerfile with the specified script and execution command.

    Args:
        script_path (str): The path to the script to execute.
        script_type (str): The type of the script (shell or python).
    """
    script_name = os.path.basename(script_path)
    if script_type == "shell":
        execution_command = f"bash /app/{script_name}"
    elif script_type == "python":
        execution_command = f"python3 /app/{script_name}"
    else:
        raise ValueError("Unsupported script type")

    with open("Dockerfile", "w") as file:
        file.write(f"""
FROM python:3.8-slim

WORKDIR /app

COPY {script_name} /app/
COPY requirements.txt /app/

RUN apt-get update && apt-get install -y git
RUN pip install --no-cache-dir -r requirements.txt
RUN chmod +x /app/{script_name}

CMD {execution_command}
        """)

def create_requirements_file(packages):
    with open("requirements.txt", "w") as file:
        for package in packages:
            file.write(f"{package}\n")

def copy_files_to_context(script_path):
    """
    Copies the script and requirements.txt to the Docker build context.

    Args:
        script_path (str): The path to the script to copy.
    """
    script_name = os.path.basename(script_path)
    shutil.copy(script_path, script_name)
    if os.path.exists("requirements.txt") and not os.path.exists("requirements_copy.txt"):
        shutil.copy("requirements.txt", "requirements_copy.txt")

def clean_up_context(script_path):
    """
    Cleans up the Docker build context by removing copied files.

    Args:
        script_path (str): The path to the script to remove.
    """
    script_name = os.path.basename(script_path)
    os.remove(script_name)
    if os.path.exists("requirements_copy.txt"):
        os.remove("requirements_copy.txt")

def analyze_test_results(output):
    """
    Analyzes the test execution results and summarizes them.

    Args:
        output (str): The output of the test execution.

    Returns:
        dict: A summary of the test results.
    """
    executed = len(re.findall(r'Ran \d+ tests', output))
    passed = len(re.findall(r'OK', output))
    failed = len(re.findall(r'FAILED', output))
    return {
        "executed": executed,
        "passed": passed,
        "failed": failed
    }

def execute_in_docker(script_path, script_type, packages):
    """
    Executes the given script in a Docker container.

    Args:
        script_path (str): The path to the script to execute.
        script_type (str): The type of the script (shell or python).
        packages (list): A list of packages to include in the requirements.txt file.

    Returns:
        str: The output of the script execution.
    """
    create_dockerfile(script_path, script_type)
    create_requirements_file(packages)
    copy_files_to_context(script_path)

    try:
        # Build the Docker image
        subprocess.run(["docker", "build", "-t", "script_executor", "."], check=True)
        
        # Run the Docker container and capture the output
        result = subprocess.run(["docker", "run", "--rm", "script_executor"], capture_output=True, text=True, check=True)
        print(colored(f"Script executed successfully in Docker:\n{result.stdout}", "blue"))
        
        # Analyze test results
        test_summary = analyze_test_results(result.stdout)
        print(colored(f"Test Summary: Executed: {test_summary['executed']}, Passed: {test_summary['passed']}, Failed: {test_summary['failed']}", "green"))
        
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(colored(f"Error executing script in Docker: {e.stderr}", "red"))
        return e.stderr
    finally:
        # Clean up Dockerfile and copied files
        os.remove("Dockerfile")
        clean_up_context(script_path)

def execute_script(script_path, packages):
    """
    Executes the given shell script in a Docker container.

    Args:
        script_path (str): The path to the shell script to execute.
        packages (list): A list of packages to include in the requirements.txt file.

    Returns:
        str: The output of the script execution.
    """
    return execute_in_docker(script_path, "shell", packages)

def execute_python_script(script_path, packages):
    """
    Executes the given Python script in a Docker container.

    Args:
        script_path (str): The path to the Python script to execute.
        packages (list): A list of packages to include in the requirements.txt file.

    Returns:
        str: The output of the script execution.
    """
    return execute_in_docker(script_path, "python", packages)

# ------------------------------------------------------------------------------
# INITIALIZATION
# ------------------------------------------------------------------------------
def initialization(repo_url):
    repo_name = (repo_url.rstrip("/").split("/")[-1])[:-4]
    repo_username = repo_url.rstrip("/").split("/")[-2]
    clone_repo(repo_url)

    with open("./prompts/planner.md", "r") as file:
        system_prompt_planner = file.read()

    with open("./prompts/summarizer.md", "r") as file:
        system_prompt_summarizer = file.read()

    with open("./prompts/writer.md", "r") as file:
        system_prompt_writer = file.read()

    with open("./prompts/validator.md", "r") as file:
        system_prompt_validator = file.read()

    with open("./prompts/executor.md", "r") as file:
        system_prompt_executor = file.read()

    with open("./templates/docker_template.py", "r") as file:
        docker_template_content = file.read()

    with open("./templates/shell_template.py", "r") as file:
        shell_template_content = file.read()

    with open("./templates/standalone_template.py", "r") as file:
        standalone_template_content = file.read()

    dirs = list_dirs(repo_name)
    return (
        repo_name,
        repo_username,
        system_prompt_planner,
        system_prompt_summarizer,
        system_prompt_writer,
        system_prompt_validator,
        system_prompt_executor,
        dirs,
        docker_template_content,
        shell_template_content,
        standalone_template_content
    )

# ------------------------------------------------------------------------------
# PLANNER
# ------------------------------------------------------------------------------
def planner(model, dirs, known_info, already_read, system_prompt_planner):
    planner_prompt = {"files": dirs, "already-seen": already_read, "gathered-info": known_info}
    answer_planner = model.answer(
        system_prompt=system_prompt_planner,
        prompt=str(planner_prompt),
        json=False
    )
    json_section = re.search(r'<output>\s*(.*?)\s*</output>', answer_planner, re.DOTALL)
    if not json_section:
        raise ValueError("Planner response did not contain a valid <output> block with JSON data.")
    extracted_text = json_section.group(1)
    import json
    files_to_read = json.loads(extracted_text)

    already_read.extend(files_to_read)
    print(colored(f"Planner: Files to read -> {files_to_read}", "magenta"))

    return files_to_read, known_info, already_read

# ------------------------------------------------------------------------------
# SUMMARIZER
# ------------------------------------------------------------------------------
def summarizer(model, files, known_info, system_prompt_summarizer):
    for file_to_check in files:
        with open(file_to_check, "r") as f:
            file_contents = f.read()

        answer_summarizer = model.answer(
            system_prompt=system_prompt_summarizer,
            prompt=f"Here's what we know now: {known_info}\n\nHere's the file to check: {file_to_check}\n" + file_contents,
            json=False
        )
        json_section = re.search(r'<output>\s*(.*?)\s*</output>', answer_summarizer, re.DOTALL)
        if not json_section:
            raise ValueError(f"Summarizer response did not contain a valid <output> block for file {file_to_check}.")
        updated_info = json_section.group(1)

        print(colored(f"Summarizer: Updated known-info template\n{updated_info}", "cyan"))
        known_info = updated_info

    return known_info

# ------------------------------------------------------------------------------
# VALIDATOR
# ------------------------------------------------------------------------------
def validate_dockerfile(dockerfile_content):
    with open("Dockerfile.temp", "w") as file:
        file.write(dockerfile_content)

    try:
        result = subprocess.run(["hadolint", "Dockerfile.temp"], capture_output=True, text=True, check=True)
        print(colored(f"Dockerfile validation passed:\n{result.stdout}", "green"))
        return "Correct"
    except subprocess.CalledProcessError as e:
        print(colored(f"Dockerfile validation failed:\n{e.stderr}", "red"))
        return "Format"
    finally:
        if os.path.exists("Dockerfile.temp"):
            os.remove("Dockerfile.temp")

def validator(model, writer_response, system_prompt_validator, output_type, template):
    if output_type == "Dev Container":
        validation_status = validate_dockerfile(writer_response)
    elif output_type == "Shell Script":
        validation_status = "Correct"
    elif output_type == "Standalone Executable":
        validation_status = "Correct"
    else:
        raise ValueError(f"Unsupported output type: {output_type}")

    print(colored(f"Validator: My verdict is -> {validation_status}", "red"))
    return validation_status

# ------------------------------------------------------------------------------
# WRITER
# ------------------------------------------------------------------------------
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
    
    # Extract the code section from the model's response
    code_section = re.search(
        r'```(?:bash|python)?\s*(.*?)\s*```', answer_writer, re.DOTALL)
    if code_section:
        answer_writer = code_section.group(1).strip()
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