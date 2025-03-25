tools = [
    {
        "type": "function",
        "function": {
            "name": "initialization",
            "description": "Clone a repo and load relevant templates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "The URL of the GitHub repository."
                    }
                },
                "required": ["repo_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "planner",
            "description": "Decides which files to read next.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "object"},
                    "dirs": {"type": "array"},
                    "known_info": {"type": "string"},
                    "already_read": {"type": "array"},
                    "system_prompt_planner": {"type": "string"}
                },
                "required": ["model","dirs","known_info","already_read","system_prompt_planner"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarizer",
            "description": "Summarizes the contents of the specified files into known_info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "object"},
                    "files": {"type": "array"},
                    "known_info": {"type": "string"},
                    "system_prompt_summarizer": {"type": "string"}
                },
                "required": ["model","files","known_info","system_prompt_summarizer"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "writer",
            "description": "Generates the appropriate output (Dockerfile, Shell Script, Standalone).",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "object"},
                    "known_info": {"type": "string"},
                    "system_prompt_writer": {"type": "string"},
                    "output_type": {"type": "string"},
                    "template": {"type": "string"}
                },
                "required": ["model","known_info","system_prompt_writer","output_type","template"]
            },
            "output": {
                "type": "object",
                "properties": {
                    "Dev Container": {
                        "type": "string",
                        "description": "Dockerfile content for the Dev Container",
                        "pattern": r"FROM fedora:latest\n.*"
                    },
                    "Shell Script": {
                        "type": "string",
                        "description": "Shell script content",
                        "pattern": r"#!/bin/bash\n.*"
                    },
                    "Standalone Executable": {
                        "type": "string",
                        "description": "Standalone executable content",
                        "pattern": r"# Entry point: .*\n# Dependencies: .*"
                    }
                },
                "required": ["Dev Container", "Shell Script", "Standalone Executable"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validator",
            "description": "Validates the generated output based on its type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "object"},
                    "writer_response": {"type": "string"},
                    "system_prompt_validator": {"type": "string"},
                    "output_type": {"type": "string"},
                    "template": {"type": "string"}
                },
                "required": ["model","writer_response","system_prompt_validator","output_type","template"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_script",
            "description": "Executes a shell script in a Docker container",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_path": {"type": "string"},
                    "packages": {"type": "array"}
                },
                "required": ["script_path", "packages"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python_script",
            "description": "Executes a Python script in a Docker container",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_path": {"type": "string"},
                    "packages": {"type": "array"}
                },
                "required": ["script_path", "packages"]
            }
        }
    }
]

from pydantic import BaseModel, Field, validator
from typing import List, Dict

class DevContainerConfig(BaseModel):
    name: str
    dockerFile: str
    context: str
    appPort: List[int]
    postCreateCommand: str
    settings: Dict[str, str]
    extensions: List[str]

    @validator('name', 'dockerFile', 'context', 'postCreateCommand')
    def non_empty_string(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('must be a non-empty string')
        return v

    @validator('appPort', 'extensions')
    def non_empty_list(cls, v):
        if not v or not isinstance(v, list) or not all(isinstance(i, (int, str)) for i in v):
            raise ValueError('must be a non-empty list of integers or strings')
        return v

    @validator('settings')
    def non_empty_dict(cls, v):
        if not v or not isinstance(v, dict) or not all(isinstance(k, str) and isinstance(val, str) for k, val in v.items()):
            raise ValueError('must be a non-empty dictionary with string keys and values')
        return v

class ShellScriptConfig(BaseModel):
    commands: List[str]

    @validator('commands')
    def non_empty_list(cls, v):
        if not v or not isinstance(v, list) or not all(isinstance(i, str) for i in v):
            raise ValueError('must be a non-empty list of strings')
        return v

class StandaloneExecutableConfig(BaseModel):
    entry_point: str
    dependencies: List[str]

    @validator('entry_point')
    def non_empty_string(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('must be a non-empty string')
        return v

    @validator('dependencies')
    def non_empty_list(cls, v):
        if not v or not isinstance(v, list) or not all(isinstance(i, str) for i in v):
            raise ValueError('must be a non-empty list of strings')
        return v