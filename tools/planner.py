import json
import re
from termcolor import colored

def planner(model, dirs, known_info, already_read, system_prompt_planner):
    """
    Uses the AI model to determine which files to read next.

    Args:
        model: The AI model to use for planning.
        dirs (list): List of directories to consider.
        known_info (str): The known information gathered so far.
        already_read (list): List of files already read.
        system_prompt_planner (str): The system prompt for the Planner Agent.

    Returns:
        tuple: A tuple containing the files to read, updated known information, and updated already read list.
    """
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