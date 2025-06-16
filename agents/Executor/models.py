from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import json

@dataclass
class ExecutionResult:
    """Result of a tool execution."""
    status: str  # success, error
    output: str
    error: Optional[str] = None
    returncode: Optional[int] = None
    path: Optional[str] = None
    
    @classmethod
    def success(cls, output: str, **kwargs):
        return cls(status="success", output=output, **kwargs)
    
    @classmethod
    def error(cls, error: str, output: str = "", **kwargs):
        return cls(status="error", output=output, error=error, **kwargs)

@dataclass
class StepResult:
    """Result of a step execution."""
    step: str
    status: str  # success, error
    output: str
    tool_used: Optional[str] = None
    tool_args: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    action: Optional[str] = None

@dataclass
class LogEntry:
    """Log entry with timestamp."""
    timestamp: str
    level: str
    message: str
    
    @classmethod
    def create(cls, message: str, level: str = "info"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return cls(timestamp=timestamp, level=level, message=message)

@dataclass
class InstallationStatus:
    """Status of the installation."""
    status: str  # success, warning, error
    message: str
    indicators: Dict[str, bool] = field(default_factory=dict)
    setup_py_exists: bool = False
    requirements_txt_exists: bool = False
    main_file: Optional[str] = None
    test_files: List[str] = field(default_factory=list)

class ToolCall(BaseModel):
    """Model for a tool call."""
    name: str
    arguments: Union[str, Dict]
    
    @field_validator('arguments', mode='before')
    def validate_arguments(cls, value):
        """Convert dict to JSON string if necessary."""
        if isinstance(value, dict):
            return json.dumps(value)
        return value

class LLMResponse(BaseModel):
    """Model for LLM response."""
    status: str = "success"
    content: str = ""
    tool_calls: List[ToolCall] = []
    
    @field_validator('tool_calls', mode='before') 
    def validate_tool_calls(cls, tool_calls):
        """Handle tool calls format conversion."""
        if not tool_calls:
            return []
        
        result = []
        for tool in tool_calls:
            if isinstance(tool, dict):
                # Ensure arguments is a string if it's a dict
                if 'arguments' in tool and isinstance(tool['arguments'], dict):
                    tool['arguments'] = json.dumps(tool['arguments'])
                result.append(tool)
            else:
                result.append(tool)
        return result

    def model_dump(self) -> Dict[str, Any]:
        """Override model_dump to handle custom serialization."""
        return {
            "status": self.status,
            "content": self.content,
            "tool_calls": [
                {
                    "name": tool.name,
                    "arguments": tool.arguments
                } for tool in self.tool_calls
            ]
        }