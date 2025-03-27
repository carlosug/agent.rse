from groq import Groq
from dotenv import dotenv_values
from tools.tool_schema import tools  # Import tools from tool_schema.py
import json

CONFIG = dotenv_values("config/.env")


class groq_model:

    def __init__(self, model_name):
        """
        Initializes the model with the given parameters.
        """
        self.client = Groq(api_key=CONFIG["GROQ_API_KEY"])
        self.model_name = model_name
        self.available_tools = {tool["function"]["name"]: tool for tool in tools}

    def answer(self, system_prompt, prompt, json):
        """
        Generates a response from the model based on the provided prompt.

        Returns:
        tuple: (tool_name, response_content)
        """
        messages = [
            {
                "role": "system",
                "content": f"{system_prompt}"
            },
            {
                "role": "user",
                "content": f"{prompt}"
            }
        ]

        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            tools=list(self.available_tools.values()),  # Convert tools to a list
            tool_choice="auto"
        )

        # Handle tool calls if present
        if "tool_calls" in response.choices[0].message:
            tool_calls = response.choices[0].message["tool_calls"]

            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                function_to_call = self.available_tools.get(function_name)

                if function_to_call:
                    function_args = json.loads(tool_call["function"]["arguments"])
                    try:
                        # Execute the tool function
                        function_response = globals()[function_name](**function_args)
                        return function_name, function_response
                    except Exception as e:
                        return function_name, f"Error: {str(e)}"

        # If no tool calls, return the response content
        response_content = response.choices[0].message.content
        if not response_content:
            response_content = "<output>[]</output>"  # Default empty response
        return "no_tool", response_content
