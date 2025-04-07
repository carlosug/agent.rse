from typing import List, Dict, Any

# Define tool schemas for Groq API
tools = [
    {
        "type": "function",
        "function": {
            "name": "ensure_workspace_exists",
            "description": "Create and verify workspace directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_path": {
                        "type": "string",
                        "description": "Base directory path to create workspace"
                    }
                },
                "required": ["base_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_install_script",
            "description": "Search for installation scripts in workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to search for install scripts"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_install_script",
            "description": "Execute an installation script and save logs automatically",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_path": {
                        "type": "string",
                        "description": "Full path to the install.sh script"
                    }
                },
                "required": ["script_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "formulate_error_search_prompt",
            "description": "Analyze installation errors and create search prompt",
            "parameters": {
                "type": "object",
                "properties": {
                    "error_file": {
                        "type": "string",
                        "description": "Path to error log file"
                    }
                },
                "required": ["error_file"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_tool_in_terminal",
            "description": "REQUIRED: Execute installation steps in terminal",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": [
                            "ensure_workspace_exists",
                            "find_install_script",
                            "run_install_script",
                            "formulate_error_search_prompt"
                        ],
                        "description": "The tool to execute"
                    },
                },
                "required": ["name"]
            }
        }
    }
]
