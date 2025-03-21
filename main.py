from tools.utils import list_dirs, clone_repo, remove_file
from models.groq_model import groq_model
from prompts.docker_template import docker_template
from prompts.shell_template import shell_template
from prompts.standalone_template import standalone_template
import json
import re
from termcolor import colored

MAX_ITERATIONS = 2
MAX_FILE_LINES = 1000


def planner(model, dirs, known_info, already_read, system_prompt_planner):
    planner_prompt = {"files": dirs, "already-seen": already_read,
                      "gathered-info": known_info}
    answer_planner = model.answer(
        system_prompt=system_prompt_planner, prompt=str(planner_prompt), json=False)
    json_section = re.search(
        r'<output>\s*(.*?)\s*</output>', answer_planner, re.DOTALL)
    answer_planner = json_section.group(1)
    answer_planner = json.loads(answer_planner)
    already_read.extend(answer_planner)
    print(colored(f"Planner: Files to read -> {answer_planner}", "magenta"))
    return answer_planner, known_info, already_read


def summarizer(model, files, known_info, system_prompt_summarizer):
    for file_to_check in files:
        with open(file_to_check, "r") as file:
            file_contents = file.read()
        answer_summarizer = model.answer(
            system_prompt=system_prompt_summarizer, prompt=f"Here's what we know now: {known_info}\n\nHere's the file to check: {file_to_check}\n" + file_contents, json=False)
        json_section = re.search(
            r'<output>\s*(.*?)\s*</output>', answer_summarizer, re.DOTALL)
        answer_summarizer = json_section.group(1)
        print(colored(
            f"Summarizer: Updated known-info template\n{answer_summarizer}", "cyan"))
        known_info = answer_summarizer
    return known_info


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
        raise ValueError("The model's response did not contain the expected output format.")
    return answer_writer


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
    validator_response = model.answer(
        system_prompt=system_prompt_validator + "\n\n" + template,
        prompt=writer_response,
        json=False
    )
    print(validator_response)
    json_section = re.search(
        r'<output>\s*(.*?)\s*</output>', validator_response, re.DOTALL)
    validator_response = json_section.group(1)
    print(colored(f"Validator: My verdict is -> {validator_response}", "red"))
    return validator_response


def initialization(repo_url):
    """
    Initializes the repository and loads the necessary prompts and templates.

    Args:
        repo_url (str): The URL of the GitHub repository.

    Returns:
        tuple: A tuple containing the repository name, username, system prompts, and directories.
    """
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

    # Load templates based on output type
    with open("./prompts/docker_template.py", "r") as file:
        docker_template = file.read()

    with open("./prompts/shell_template.py", "r") as file:
        shell_template = file.read()

    with open("./prompts/standalone_template.py", "r") as file:
        standalone_template = file.read()

    dirs = list_dirs(repo_name)
    return repo_name, repo_username, system_prompt_planner, system_prompt_summarizer, system_prompt_writer, system_prompt_validator, dirs, docker_template, shell_template, standalone_template


if __name__ == "__main__":
    model_name = "llama-3.3-70b-versatile"
    repo_url = input(
        colored("Welcome to AutoREADME! Input the desired GitHub repository:\n", "green"))
    repo_name, repo_username, system_prompt_planner, system_prompt_summarizer, system_prompt_writer, system_prompt_validator, dirs, docker_template, shell_template, standalone_template = initialization(
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
            known_info = summarizer(
                model=model, files=answer_planner, known_info=known_info, system_prompt_summarizer=system_prompt_summarizer)
            print(colored(f"Summarizer finished!", "green"))
        skip_summarizer = False

        # Extract the suggested output type from the known_info
        suggested_output_match = re.search(
            r'Suggested Output: "(.*?)"', known_info, re.DOTALL)
        if suggested_output_match:
            suggested_output = suggested_output_match.group(1).strip().split('.')[0]
        else:
            suggested_output = "Dev Container"  # Default to Dev Container if no suggestion is found

        print(colored("\nStarting AI Writer...", "green"))
        if suggested_output == "Dev Container":
            writer_response = writer(model=model, known_info=known_info,
                                     system_prompt_writer=system_prompt_writer, output_type=suggested_output, template=docker_template)
            output_file = "my.dockerfile"
        elif suggested_output == "Shell Script":
            writer_response = writer(model=model, known_info=known_info,
                                     system_prompt_writer=system_prompt_writer, output_type=suggested_output, template=shell_template)
            output_file = "install.sh"
        elif suggested_output == "Standalone Executable":
            writer_response = writer(model=model, known_info=known_info,
                                     system_prompt_writer=system_prompt_writer, output_type=suggested_output, template=standalone_template)
            output_file = "standalone_executable.py"
        else:
            raise ValueError(f"Unsupported output type: {suggested_output}")

        print(colored("Writer finished!", "green"))

        print(colored("\nStarting AI Validator...", "green"))
        validator_response = validator(model=model, writer_response=writer_response,
                                       system_prompt_validator=system_prompt_validator, output_type=suggested_output, template=docker_template if suggested_output == "Dev Container" else shell_template if suggested_output == "Shell Script" else standalone_template)
        print(colored("Validator finished!", "green"))

        if (validator_response == "Correct"):
            ended = True
        elif (validator_response == "Format"):
            skip_planner = True
            skip_summarizer = True
        iteration = iteration + 1

    if iteration == MAX_ITERATIONS:
        print(colored("Ended due to excess of iterations.", "green"))

    # Save the generated output file
    with open(output_file, "w") as file:
        file.write(writer_response)

    remove_file(file_name=repo_name)