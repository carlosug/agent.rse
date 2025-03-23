import subprocess
import os
from termcolor import colored
import shutil

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
RUN pip3 install -r requirements.txt

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
        file.write(DOCKERFILE_TEMPLATE.format(script_name=script_name, execution_command=execution_command))

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

def execute_in_docker(script_path, script_type):
    """
    Executes the given script in a Docker container.

    Args:
        script_path (str): The path to the script to execute.
        script_type (str): The type of the script (shell or python).

    Returns:
        str: The output of the script execution.
    """
    create_dockerfile(script_path, script_type)
    copy_files_to_context(script_path)

    try:
        # Build the Docker image
        subprocess.run(["docker", "build", "-t", "script_executor", "."], check=True)
        
        # Run the Docker container and capture the output
        result = subprocess.run(["docker", "run", "--rm", "script_executor"], capture_output=True, text=True, check=True)
        print(colored(f"Script executed successfully in Docker:\n{result.stdout}", "blue"))
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(colored(f"Error executing script in Docker: {e.stderr}", "red"))
        return e.stderr
    finally:
        # Clean up Dockerfile and copied files
        os.remove("Dockerfile")
        clean_up_context(script_path)

def execute_script(script_path):
    """
    Executes the given shell script in a Docker container.

    Args:
        script_path (str): The path to the shell script to execute.

    Returns:
        str: The output of the script execution.
    """
    return execute_in_docker(script_path, "shell")

def execute_python_script(script_path):
    """
    Executes the given Python script in a Docker container.

    Args:
        script_path (str): The path to the Python script to execute.

    Returns:
        str: The output of the script execution.
    """
    return execute_in_docker(script_path, "python")