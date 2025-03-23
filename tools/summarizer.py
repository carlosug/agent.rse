import re
from termcolor import colored

def summarizer(model, files, known_info, system_prompt_summarizer):
    """
    Summarizes the contents of the specified files.

    Args:
        model: The AI model to use for summarizing.
        files (list): List of files to summarize.
        known_info (str): The known information gathered so far.
        system_prompt_summarizer (str): The system prompt for the Summarizer Agent.

    Returns:
        str: The updated known information.
    """
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