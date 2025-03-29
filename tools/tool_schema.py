tools = [
    {
        "type": "function",
        "function": {
            "name": "get_bakery_prices",
            "description": "Returns the prices for a given bakery product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bakery_item": {
                        "type": "string",
                        "description": "The name of the bakery item",
                    }
                },
                "required": ["bakery_item"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expert_coder",
            "description": "Generates expert-level Python code snippets based on a given prompt using the Groq LLM model. "
                           "This tool is designed to assist developers by automating the creation of high-quality Python "
                           "code for specific tasks or problems.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt describing the desired Python code."
                    }
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_dockerfile",
            "description": "Generates a clean Dockerfile based on the given prompt. Returns only the Dockerfile instructions without any additional text or explanations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt describing the desired Dockerfile content. The response will contain only Dockerfile instructions."
                    },
                    "model": {
                        "type": "string",
                        "description": "The name of the Groq LLM model to use.",
                        "default": "gemma2-9b-it"
                    }
                },
                "required": ["prompt"]
            }
        }
    }
]