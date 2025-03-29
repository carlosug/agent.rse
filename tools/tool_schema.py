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
            "description": "Generates a Dockerfile based on the given prompt using the Groq API and saves it to the experimental_workplace folder. Returns a structured response with the Dockerfile content, file path, and status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt describing the desired Dockerfile content"
                    },
                    "model": {
                        "type": "string",
                        "description": "The name of the Groq LLM model to use",
                        "default": "gemma2-9b-it"
                    }
                },
                "required": ["prompt"]
            },
            "returns": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The cleaned Dockerfile content"
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path where the Dockerfile was saved"
                    },
                    "status": {
                        "type": "string",
                        "description": "Generation status (success/error)"
                    },
                    "error": {
                        "type": "string",
                        "description": "Error message if any occurred"
                    }
                }
            }
        }
    }
]