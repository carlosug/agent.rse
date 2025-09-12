from enum import Enum
from pydantic import BaseModel, Field, validator
import re
from typing import Optional, List, Dict, Tuple, Any, Union

# Standard installation methods as constants for reference
class StandardInstallationMethod(str, Enum):
    """Standard installation methods for reference."""
    PIP = "pip"
    DOCKER = "docker"
    SOURCE = "source"
    SOURCE_GIT = "source_git"
    CONDA = "conda"
    NPM = "npm"
    YARN = "yarn"
    APT = "apt"
    YUM = "yum"
    BREW = "brew"
    MANUAL = "manual"
    OTHER = "other"

class InstallationMethod(str, Enum):
    """Enumeration of supported installation methods."""
    PIP = "pip"
    CONDA = "conda"
    DOCKER = "docker"
    SOURCE = "source"
    UNKNOWN = "unknown"
    
    # Add this validator method to handle case mismatches
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            # Try case-insensitive matching
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return cls.UNKNOWN

class DynamicInstallationMethod(BaseModel):
    """Flexible model for handling custom installation methods."""
    name: str = Field(..., description="Name of installation method")
    description: Optional[str] = Field(None, description="Description of this installation method")
    standard: bool = Field(default=False, description="Whether this is a standard method")
    commands: List[str] = Field(default_factory=list, description="Common commands for this method")
    
    @classmethod
    def from_string(cls, method_string: str) -> "DynamicInstallationMethod":
        """Create a DynamicInstallationMethod from a string."""
        method_lower = method_string.lower()
        
        # Check if it's a standard method
        for method in StandardInstallationMethod:
            if method.value == method_lower:
                return cls(
                    name=method.value,
                    description=f"Standard {method.value} installation",
                    standard=True,
                    commands=cls.get_standard_commands(method.value)
                )
        
        # If not a standard method, create a custom one
        return cls(
            name=method_string,
            description=f"Custom installation method: {method_string}",
            standard=False
        )
    
    @staticmethod
    def get_standard_commands(method: str) -> List[str]:
        """Get standard commands for common installation methods."""
        commands_map = {
            "pip": ["pip install package_name"],
            "docker": ["docker pull image_name", "docker run image_name"],
            "conda": ["conda install package_name"],
            "npm": ["npm install package_name"],
            "yarn": ["yarn add package_name"],
            "apt": ["apt-get update", "apt-get install package_name"],
            "yum": ["yum install package_name"],
            "brew": ["brew install package_name"],
            "source": ["git clone repository_url", "cd repository", "./configure", "make", "make install"]
        }
        
        return commands_map.get(method, [])

class InstallationMethodRegistry:
    """Registry for managing dynamically discovered installation methods."""
    _methods = {}
    
    @classmethod
    def register(cls, method_name: str, description: Optional[str] = None, commands: Optional[List[str]] = None):
        """Register a new installation method."""
        method_name = method_name.lower()
        
        if method_name not in cls._methods:
            cls._methods[method_name] = DynamicInstallationMethod(
                name=method_name,
                description=description or f"Installation method: {method_name}",
                commands=commands or []
            )
        
        return cls._methods[method_name]
    
    @classmethod
    def get_method(cls, method_name: str) -> DynamicInstallationMethod:
        """Get a method by name, registering it if it doesn't exist."""
        method_name = method_name.lower()
        
        if method_name not in cls._methods:
            return cls.register(method_name)
        
        return cls._methods[method_name]
    
    @classmethod
    def list_methods(cls) -> List[str]:
        """List all registered method names."""
        # Start with standard methods
        all_methods = [method.value for method in StandardInstallationMethod]
        
        # Add custom methods that aren't standard
        for method in cls._methods:
            if method not in all_methods:
                all_methods.append(method)
                
        return all_methods

class DockerfileRequest(BaseModel):
    """Request model for Dockerfile generation."""
    prompt: str = Field(
        description="The prompt describing the desired Dockerfile content"
    )
    model: str = Field(
        default="deepseek-r1-distill-llama-70b",
        description="The name of the Groq LLM model to use"
    )
    temperature: float = Field(
        default=0.1,
        description="Temperature for the LLM response (controls randomness)"
    )
    max_tokens: int = Field(
        default=2000,
        description="Maximum number of tokens for the LLM response"
    )

class DockerfileContent(BaseModel):
    """Model for parsing and validating Dockerfile content."""
    raw_content: str = Field(..., description="Raw response from the LLM")
    
    @property
    def dockerfile_code(self) -> str:
        """Extract only the Dockerfile code from the content."""
        # Look for content between <dockerfile> and </dockerfile> markers
        dockerfile_pattern = r'<dockerfile>\s*(.*?)\s*</dockerfile>'
        dockerfile_match = re.search(dockerfile_pattern, self.raw_content, re.DOTALL)
        
        if dockerfile_match:
            return dockerfile_match.group(1).strip()
        
        # Alternative pattern for Dockerfile-like content
        dockerfile_lines = []
        for line in self.raw_content.split('\n'):
            line = line.strip()
            if re.match(r'^(FROM|RUN|COPY|ADD|WORKDIR|ENV|EXPOSE|CMD|ENTRYPOINT)\s+', line, re.IGNORECASE):
                dockerfile_lines.append(line)
        
        if dockerfile_lines:
            return '\n'.join(dockerfile_lines).strip()
        
        # If no valid Dockerfile content is found, raise an error
        raise ValueError("No valid Dockerfile content found in the response")

class DockerfileResponse(BaseModel):
    """Response model for Dockerfile generation."""
    reasoning: str = Field(..., description="Reasoning provided by the LLM")
    dockerfile_code: str = Field(..., description="The cleaned Dockerfile content")
    raw_content: str = Field(..., description="Raw response from the LLM")
    status: str = Field(default="success", description="Generation status")
    error: Optional[str] = Field(None, description="Error message if any")

    @validator("dockerfile_code")
    def validate_dockerfile_code(cls, value):
        """Ensure the Dockerfile code contains essential instructions."""
        required_instructions = ["FROM", "WORKDIR", "COPY", "RUN", "CMD"]
        missing_instructions = [instr for instr in required_instructions if instr not in value]
        if missing_instructions:
            raise ValueError(f"Dockerfile must contain the following instructions: {', '.join(missing_instructions)}")
        return value

    def validate_structure(self) -> None:
        """Validate the structure of the Dockerfile."""
        if not self.dockerfile_code.startswith("FROM"):
            raise ValueError("Dockerfile must start with a FROM instruction")
        if "CMD" not in self.dockerfile_code:
            raise ValueError("Dockerfile must include a CMD instruction")

class InstallScriptResponse(BaseModel):
    """Response model for installation script generation."""
    reasoning: str = Field(..., description="Reasoning provided by the LLM")
    script_content: str = Field(..., description="The generated installation script")
    raw_content: str = Field(..., description="Raw response from the LLM")
    status: str = Field(default="success", description="Generation status")
    error: Optional[str] = Field(None, description="Error message if any")

    @validator("script_content")
    def validate_script_content(cls, value):
        """Ensure the script starts with #!/bin/bash and includes essential commands."""
        if not value.startswith("#!/bin/bash"):
            raise ValueError("Installation script must start with #!/bin/bash")
        if "set -e" not in value:
            raise ValueError("Installation script must include 'set -e' for error handling")
        return value

    def validate_structure(self) -> None:
        """Validate the structure of the installation script."""
        if not self.script_content.startswith("#!/bin/bash"):
            raise ValueError("Installation script must start with #!/bin/bash")
        if "set -e" not in self.script_content:
            raise ValueError("Installation script must include 'set -e' for error handling")

class InstallStep(BaseModel):
    """Model for a single installation step."""
    method: str = Field(..., description="Installation method type")
    order: int = Field(..., description="Step order number")
    instruction: str = Field(..., description="Installation instruction")
    commands: List[str] = Field(
        default_factory=list,
        description="List of commands to execute for this step"
    )

class UsageExample(BaseModel):
    """Model for a usage example."""
    description: str = Field(..., description="Description of the use case")
    code: str = Field(..., description="Example code or configuration")
    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions and considerations for this example"
    )
    expected_output: Optional[str] = Field(
        None,
        description="Expected output or result"
    )

class InvocationCommand(BaseModel):
    """Model for software invocation commands."""
    command: str = Field(..., description="The execution command")
    purpose: str = Field(..., description="What this command does")
    arguments: Dict[str, str] = Field(
        default_factory=dict,
        description="Command arguments and their descriptions"
    )
    requirements: List[str] = Field(
        default_factory=list,
        description="Requirements needed before running this command"
    )

class ReadmeAnalysisContent(BaseModel):
    """Model for parsed README analysis content."""
    summary: str = Field(
        default="",
        description="Brief overview of installation process"
    )
    methods: List[str] = Field(
        default_factory=list,
        description="List of installation methods"
    )
    installation_instructions_per_method: List[InstallStep] = Field(
        default_factory=list,
        description="Ordered list of installation steps per method"
    )
    prerequisites: List[str] = Field(
        default_factory=list,
        description="List of prerequisites"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of required dependencies"
    )
    operating_system: str = Field(
        default="",
        description="Operating system requirements or compatibility"
    )
    commands: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of installation and usage commands with metadata"
    )
    config_files: List[str] = Field(
        default_factory=list,
        description="List of configuration files"
    )
    usage_examples: List[UsageExample] = Field(
        default_factory=list,
        description="List of documented usage examples with assumptions"
    )
    invocation_commands: List[InvocationCommand] = Field(
        default_factory=list,
        description="List of execution commands for running the software"
    )
    environment: List[str] = Field(
        default_factory=list,
        description="List of required environment variables"
    )
    important_links: List[str] = Field(
        default_factory=list,
        description="List of relevant documentation links"
    )
    
    def __init__(self, **data):
        """Initialize with dynamic method registration."""
        super().__init__(**data)
        
        # Register any methods found in the data
        if self.methods:
            for method in self.methods:
                InstallationMethodRegistry.register(method)

class ReadmeAnalysisResponse(BaseModel):
    """Response model for README analysis."""
    status: str = Field(
        default="success",
        description="Analysis status (success/error)"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if any occurred"
    )
    analysis: ReadmeAnalysisContent = Field(
        default_factory=ReadmeAnalysisContent,
        description="Structured analysis of the README content"
    )

class PlanStep(BaseModel):
    """Model for a planned installation step."""
    order: int = Field(..., description="Step order in the plan")
    method: str = Field(..., description="Installation method this step belongs to")
    description: str = Field(..., description="What this step does")
    command: Optional[Union[str, List[str]]] = Field(None, description="Command(s) to execute")
    dependencies: List[str] = Field(
        default_factory=list,
        description="Dependencies needed for this step"
    )
    verification: Optional[str] = Field(None, description="How to verify this step succeeded")
    validation_results: Optional[Dict[str, Any]] = Field(
        None, description="Validation results from web search"
    )
    
    @classmethod
    def safe_create(cls, **data):
        """Safely create a PlanStep handling problematic data types."""
        # Handle command field that could be string, list, or dict
        if "command" in data:
            cmd = data["command"]
            if isinstance(cmd, dict):
                # Handle dictionary format
                if "cmd" in cmd:
                    data["command"] = cmd["cmd"]
                elif "command" in cmd:
                    data["command"] = cmd["command"]
                elif "commands" in cmd and isinstance(cmd["commands"], list):
                    data["command"] = cmd["commands"]
                else:
                    # Convert dict to string as fallback
                    data["command"] = str(cmd)
            elif isinstance(cmd, list):
                # Already a list of commands, keep as is
                # But ensure all elements are strings
                data["command"] = [str(item) if item is not None else "" for item in cmd]
            elif cmd is not None:
                # Single command as string
                data["command"] = str(cmd)
        
        # Handle dependencies field
        if "dependencies" in data:
            deps = data["dependencies"]
            if deps is None:
                data["dependencies"] = []
            elif isinstance(deps, str):
                data["dependencies"] = [deps]
            elif isinstance(deps, list):
                # Convert non-string items to strings
                clean_deps = []
                for item in deps:
                    if isinstance(item, (dict, list)):
                        # Skip complex objects
                        pass
                    elif item is not None:
                        clean_deps.append(str(item))
                data["dependencies"] = clean_deps
            else:
                # Convert any other type to string and wrap in list
                data["dependencies"] = [str(deps)]
        else:
            data["dependencies"] = []
            
        # Handle required fields
        if "order" not in data or data["order"] is None:
            data["order"] = 1
        if "method" not in data or data["method"] is None:
            data["method"] = "unknown"
        if "description" not in data or data["description"] is None:
            data["description"] = "No description provided"
            
        return cls(**data)
    
    def get_commands_as_list(self) -> List[str]:
        """Convert command to list format, regardless of original type."""
        if self.command is None:
            return []
        elif isinstance(self.command, str):
            return [self.command]
        elif isinstance(self.command, list):
            return self.command
        else:
            return [str(self.command)]

class InstallationPlan(BaseModel):
    """Model for installation plan details."""
    chosen_method: str = Field(..., description="Selected installation method")
    reason: str = Field(..., description="Why this method was chosen")
    steps: List[PlanStep] = Field(
        default_factory=list,
        description="Ordered steps to follow"
    )
    fallback_method: Optional[str] = Field(
        None,
        description="Alternative method if primary fails"
    )
    operating_systems: List[str] = Field(
        default_factory=list,
        description="Compatible operating systems"
    )
    language: Optional[str] = Field(None, description="Programming language")
    version: Optional[str] = Field(None, description="Programming language version")
    usage_examples: List[UsageExample] = Field(
        default_factory=list,
        description="Examples of how to use the software"
    )
    invocation_commands: List[InvocationCommand] = Field(
        default_factory=list,
        description="Commands to run the software"
    )
    installation_commands: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Raw installation commands from README"
    )
    usage_summary: Optional[Dict[str, Any]] = Field(
        None, 
        description="Summarized usage information"
    )

    @validator('chosen_method')
    def normalize_method(cls, v):
        """Normalize installation method names."""
        if not v:
            return "not_specified"
        
        # Lowercase for consistency
        v_lower = v.lower()
        
        # Check if it's a standard method and normalize it
        for method in StandardInstallationMethod:
            if method.value == v_lower or method.value in v_lower:
                return method.value
                
        # If it's not a standard method, keep it as is
        return v

    @classmethod
    def create_default(cls) -> 'InstallationPlan':
        """Create a default installation plan."""
        return cls(
            chosen_method="not_specified",
            reason="No method chosen yet",
            steps=[],
            fallback_method=None,
            operating_systems=["Linux"],
            usage_examples=[],
            invocation_commands=[],
            installation_commands=[]
        )

    def validate_plan(self, package_name: str) -> None:
        """Validate the installation plan using web search."""
        from tools.terminal import validate_installation_plan
        validation_results = validate_installation_plan(package_name, self.dict())
        
        # Update steps with validation results
        for step in self.steps:
            step_validation = next(
                (v for v in validation_results.get('step_validations', [])
                 if v['step'] == step.order),
                None
            )
            if step_validation:
                step.validation_results = step_validation

class ReasoningAnalysis(BaseModel):
    """Model for the reasoning part of the analysis."""
    analysis: str = Field(..., description="Brief description of installation requirements")
    method_choice: str = Field(..., description="Reasoning for chosen installation method")
    next_steps: str = Field(..., description="Planned next steps")
    installation_plan: InstallationPlan = Field(
        default_factory=lambda: InstallationPlan(
            chosen_method="",
            reason="",
            steps=[],
            fallback_method=None
        ),
        description="Detailed installation plan"
    )

class ToolCommand(BaseModel):
    """Model for the tool command execution."""
    name: str = Field(..., description="Name of the tool (linux_terminal)")
    args: Dict[str, str] = Field(..., description="Tool arguments including command")

class AnalysisResponse(BaseModel):
    """Base model for analysis responses."""
    status: str = Field(default="success", description="Analysis status")
    error: Optional[str] = Field(None, description="Error message if any")

class InstallationAnalysisResponse(AnalysisResponse):
    """Model for the complete installation analysis response."""
    reasoning: ReasoningAnalysis = Field(..., description="Reasoning about installation")
    tool: ToolCommand = Field(..., description="Tool command to execute")
    installation_method: str = Field(..., description="Installation method")  # Changed from enum to str
    safe_to_execute: bool = Field(default=False, description="Whether command is safe to execute")

    @validator('installation_method')
    def normalize_method(cls, v):
        """Normalize and validate installation method."""
        if not v:
            return "not_specified"
            
        v_lower = v.lower()
        
        # Check if it's a standard method
        for method in StandardInstallationMethod:
            if method.value == v_lower or method.value in v_lower:
                return method.value
                
        # If not standard, accept it as is
        return v

class ContainerType(str, Enum):
    """Supported container types."""
    DOCKER = "docker"
    GUIX = "guix"
    SINGULARITY = "singularity"

class ContainerStep(BaseModel):
    """Model for container build/run steps."""
    order: int = Field(..., description="Step order")
    command: str = Field(..., description="Command to execute")
    description: str = Field(..., description="Step description")
    validation: Optional[str] = Field(None, description="Validation command")

class ContainerConfig(BaseModel):
    """Container configuration details."""
    type: ContainerType = Field(..., description="Type of container")
    base_image: str = Field(..., description="Base image or system")
    build_steps: List[ContainerStep] = Field(
        default_factory=list,
        description="Steps to build container"
    )
    run_steps: List[ContainerStep] = Field(
        default_factory=list,
        description="Steps to run container"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables"
    )
    ports: List[str] = Field(
        default_factory=list,
        description="Ports to expose"
    )
    volumes: List[str] = Field(
        default_factory=list,
        description="Volumes to mount"
    )

class ContainerBestPractice(BaseModel):
    """Class representing a container best practice."""
    category: str = Field(..., description="Practice category")
    recommendation: str = Field(..., description="Practice description")
    source: str = Field(..., description="Source of recommendation")
    priority: int = Field(..., description="Priority level")

    def __str__(self) -> str:
        """String representation of the best practice."""
        return self.recommendation

    @classmethod
    def safe_create(cls, value, index=0) -> 'ContainerBestPractice':
        """Safely create a ContainerBestPractice from various input formats."""
        if isinstance(value, cls):
            # Already the right type
            return value
            
        if isinstance(value, dict):
            # Handle dictionary format
            return cls(
                category=value.get('category', 'container'),
                recommendation=value.get('recommendation', 'Missing recommendation'),
                source=value.get('source', 'container_analysis'),
                priority=value.get('priority', index + 1)
            )
            
        if isinstance(value, str):
            # Handle string format
            return cls(
                category='container',
                recommendation=value,
                source='container_analysis',
                priority=index + 1
            )
        
        # Last resort - convert to string
        return cls(
            category='container',
            recommendation=str(value),
            source='unknown',
            priority=index + 1
        )
        
    @classmethod
    def from_list(cls, items) -> List['ContainerBestPractice']:
        """Convert a list of items (strings, dicts, etc.) to ContainerBestPractice objects."""
        if not items:
            return []
            
        result = []
        for idx, item in enumerate(items):
            try:
                result.append(cls.safe_create(item, idx))
            except Exception as e:
                # Skip items that can't be converted
                continue
                
        return result

class ContainerRecommendations(BaseModel):
    """Model for container recommendations."""
    container_type: str
    installation_type: str
    project_type: str = "python"
    repository: str
    operating_system: str = "Linux"
    method_source: str
    guidelines: str
    confidence_scores: Dict[str, float]
    best_practices: List[ContainerBestPractice]
    documentation_url: Optional[str] = None
    web_results: List[Dict[str, str]] = Field(default_factory=list)

class ValidationResponse(BaseModel):
    """Container validation response."""
    status: str = Field(..., description="Validation status")
    container_config: ContainerConfig = Field(..., description="Container configuration")
    best_practices: List[ContainerBestPractice] = Field(
        default_factory=list,
        description="Best practices applied"
    )
    files_generated: List[str] = Field(
        default_factory=list,
        description="Generated file paths"
    )
    error: Optional[str] = Field(None, description="Error message if any")

class GenerationResponse(BaseModel):
    """Model for generation results."""
    status: str = Field(..., description="Status of generation (success/error)")
    files_generated: List[str] = Field(default_factory=list, description="List of generated files")
    error: Optional[str] = Field(None, description="Error message if status is error")
    dockerfile_path: Optional[str] = Field(None, description="Path to generated Dockerfile")
    install_script_path: Optional[str] = Field(None, description="Path to generated install script")
    reasoning: Dict[str, str] = Field(default_factory=dict, description="Reasoning for generated files")

    def validate_files(self) -> None:
        """Validate that all required files were generated."""
        required_files = ["install.sh", "Dockerfile"]
        missing_files = [file for file in required_files if file not in self.files_generated]
        if missing_files:
            raise ValueError(f"Missing required files: {', '.join(missing_files)}")