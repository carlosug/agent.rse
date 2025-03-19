import json
from pydantic import BaseModel
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT

class Action(BaseModel):
    name: str
    description: str
    command: str

class TaskRunAgent:
    def __init__(self, api_key):
        self.api_key = api_key
        self.anthropic = Anthropic(api_key=api_key)

    def generate_action_list(self, readme_text):
        prompt = f"""
        {HUMAN_PROMPT} Given the following README text, generate a list of actions to set up the project environment. Each action should include a name, description, and command.
        README:
        {readme_text}
        {AI_PROMPT}
        """
        response = self.anthropic.completions.create(
            model="claude-v1",
            prompt=prompt,
            max_tokens_to_sample=300
        )
        actions = json.loads(response['completion'])
        return [Action(**action) for action in actions]

    def format_actions(self, actions):
        return "\n".join([f"{action.name}: {action.description}\nCommand: {action.command}" for action in actions])