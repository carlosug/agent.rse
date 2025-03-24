from tools.planner import planner
from tools.summarizer import summarizer
from tools.writer import writer, fetch_template  # Import fetch_template
from tools.validator import validator
from tools.executor import execute_script, execute_python_script  # Import executor functions
from tools.initialization import initialization
from tools.utils import remove_file  # Import the remove_file function
from models.groq_model import groq_model
from termcolor import colored
import re
import os
import shutil

MAX_ITERATIONS = 2
MAX_FILE_LINES = 1000
OUTPUT_DIR = "output"

if __name__ == "__main__":
    model_name = "llama-3.3-70b-versatile"  # "qwen-qwq-32b"
    repo_url = input(
        colored("Welcome to AutoREADME! Input the desired GitHub repository:\n", "green"))
    repo_name, repo_username, system_prompt_planner, system_prompt_summarizer, system_prompt_writer, system_prompt_validator, system_prompt_executor, dirs, docker_template, shell_template, standalone_template = initialization(
        repo_url=repo_url)

    known_info = f"""
    User: {repo_username}
    Repo name: {repo_name}
    Installation: [Empty]
    Usage: [Empty]
    License: [Empty]
    Suggested Output: [Empty]
    """
    already_read = []
    model = groq_model(model_name=model_name)
    iteration = 0
    ended = False
    skip_planner = False
    skip_summarizer = False

    # Create the output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    while (not ended and iteration < MAX_ITERATIONS):
        if (not skip_planner):
            print(colored("\nStarting AI Planner...", "green"))
            answer_planner, known_info, already_read = planner(model=model, dirs=dirs,
                                                               known_info=known_info, already_read=already_read,
                                                               system_prompt_planner=system_prompt_planner)
            print(colored("Planner finished!", "green"))
        skip_planner = False

        if (not skip_summarizer):
            print(colored("\nStarting AI Summarizer...", "green"))
            try:
                known_info = summarizer(
                    model=model, files=answer_planner, known_info=known_info, system_prompt_summarizer=system_prompt_summarizer)
                print(colored(f"Summarizer finished!", "green"))
            except FileNotFoundError as e:
                print(colored(f"Error: {e}", "red"))
                break
        skip_summarizer = False

        # Extract the suggested output type from the known_info
        suggested_output_match = re.search(
            r'Suggested Output: "(.*?)(\.|,)', known_info, re.DOTALL)
        if suggested_output_match:
            suggested_output = suggested_output_match.group(1).strip()
        else:
            suggested_output = "Dev Container"  # Default to Dev Container if no suggestion is found

        print(colored("\nStarting AI Writer...", "green"))
        template = fetch_template(suggested_output)  # Fetch the template
        writer_response = writer(model=model, known_info=known_info,
                                 system_prompt_writer=system_prompt_writer, output_type=suggested_output, template=template)
        if suggested_output == "Dev Container":
            output_file = os.path.join(OUTPUT_DIR, "my.dockerfile")
        elif suggested_output == "Shell Script":
            output_file = os.path.join(OUTPUT_DIR, "install.sh")
        elif suggested_output == "Standalone Executable":
            output_file = os.path.join(OUTPUT_DIR, "standalone_executable.py")
        else:
            raise ValueError(f"Unsupported output type: {suggested_output}")

        print(colored("Writer finished!", "green"))

        print(colored("\nStarting AI Validator...", "green"))
        validator_response = validator(model=model, writer_response=writer_response,
                                       system_prompt_validator=system_prompt_validator, output_type=suggested_output, template=template)
        print(colored("Validator finished!", "green"))

        if validator_response == "Correct":
            ended = True
        elif validator_response == "Format":
            skip_planner = True
            skip_summarizer = True
        elif validator_response == "Information":
            print(colored("Validator returned 'Information'. Ending process.", "yellow"))
            break
        iteration = iteration + 1

    if iteration == MAX_ITERATIONS:
        print(colored("Ended due to excess of iterations.", "green"))

    # Save the generated output file
    with open(output_file, "w") as file:
        file.write(writer_response)

    # Save the generated output file into the output folder
    output_path = os.path.join(OUTPUT_DIR, os.path.basename(output_file))
    try:
        shutil.move(output_file, output_path)
        print(f"Output file saved to {output_path} successfully.")
    except OSError as e:
        print(f"Error saving output file: {e.strerror} - {e.filename}")

    # Execute the generated output file
    print(colored("\nStarting AI Executor...", "green"))
    if suggested_output == "Shell Script":
        execution_result = execute_script(output_path)
    elif suggested_output == "Standalone Executable":
        execution_result = execute_python_script(output_path)
    else:
        execution_result = "Execution not supported for this output type."
    print(colored("Executor finished!", "green"))

    try:
        shutil.rmtree(repo_name)
        print(f"Repository directory {repo_name} removed successfully.")
    except OSError as e:
        print(f"Error removing repository directory: {e.strerror} - {e.filename}")
