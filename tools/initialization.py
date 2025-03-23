from tools.utils import list_dirs, clone_repo
from templates.docker_template import docker_template
from templates.shell_template import shell_template
from templates.standalone_template import standalone_template

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

    with open("./prompts/executor.md", "r") as file:
        system_prompt_executor = file.read()

    # Load templates based on output type
    with open("./templates/docker_template.py", "r") as file:
        docker_template = file.read()

    with open("./templates/shell_template.py", "r") as file:
        shell_template = file.read()

    with open("./templates/standalone_template.py", "r") as file:
        standalone_template = file.read()

    dirs = list_dirs(repo_name)
    return repo_name, repo_username, system_prompt_planner, system_prompt_summarizer, system_prompt_writer, system_prompt_validator, system_prompt_executor, dirs, docker_template, shell_template, standalone_template