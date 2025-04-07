from typing import Dict, Any, List, Optional

tools = {
    "terminal": {
        "description": "Execute terminal commands",
        "parameters": {
            "command": "Command to execute"
        }
    },
    "files": {
        "description": "Read or write files",
        "parameters": {
            "action": "read|write",
            "path": "Path to file",
            "content": "Content to write (for write actions)"
        }
    },
    "dockerfile": {
        "description": "Generate a Dockerfile",
        "parameters": {
            "base_image": "Base Docker image",
            "dependencies": "List of dependencies",
            "commands": "Commands to include"
        }
    },
    "container_recommendations": {
        "description": "Get container best practices and recommendations",
        "parameters": {
            "action": "Type of recommendation (dockerfile, script, search)",
            "container_type": "Type of container (docker, guix, singularity)",
            "project_type": "Type of project",
            "context": "Additional context for recommendation"
        }
    }
}