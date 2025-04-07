from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

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
    """Model for tool calls from LLM."""
    name: str = Field(description="The name of the tool to call")
    arguments: Dict[str, Any] = Field(description="Tool parameters")

class LLMResponse(BaseModel):
    """Model for LLM responses."""
    status: str = Field(description="Success or error status")
    content: str = Field(description="The LLM's response content")
    tool_calls: Optional[List[ToolCall]] = Field(default_factory=list, description="List of tool calls")