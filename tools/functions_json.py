CONTAINER_FUNCTIONS = {
    "search_container_practices": {
        "type": "function",  # Add type field
        "function": {
            "name": "search_container_practices",
            "description": "Search for container best practices and implementations",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_type": {
                        "type": "string",
                        "enum": ["docker", "guix", "singularity"],
                        "description": "Type of container technology"
                    },
                    "project_type": {
                        "type": "string",
                        "description": "Type of project (e.g., python, java)"
                    },
                    "operating_system": {
                        "type": "string",
                        "description": "Target operating system"
                    },
                    "requirements": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of project requirements"
                    }
                },
                "required": ["container_type", "project_type"]
            }
        }
    },
    "generate_container_config": {
        "name": "generate_container_config",
        "description": "Generate container configuration based on best practices",
        "parameters": {
            "type": "object",
            "properties": {
                "container_type": {
                    "type": "string",
                    "enum": ["docker", "guix", "singularity"]
                },
                "base_image": {
                    "type": "string",
                    "description": "Base container image"
                },
                "install_steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "order": {"type": "integer"},
                            "command": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                },
                "environment": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["container_type", "install_steps"]
        }
    }
}