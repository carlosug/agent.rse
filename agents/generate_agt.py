import os
import json
from typing import Dict, Any, List, Tuple
from pathlib import Path
from groq import Groq
from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
import sys
from jinja2 import Template
import re
import traceback
from rich.syntax import Syntax
from rich import print
from rich.console import Group
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from tools.tool_models import (
    ContainerConfig,
    ContainerType,
    ContainerStep,
    GenerationResponse,  # Now properly imported
    DockerfileRequest,
    DockerfileContent,
    DockerfileResponse,
    InstallScriptResponse
)
from pydantic import field_validator  # Import the new decorator

console = Console()

class ContainerGenerationAgent:
    """Agent for generating container and installation files."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.ensure_workspace()
        self.init_groq_client()
        self.load_prompts()
        
    def ensure_workspace(self) -> None:
        """Ensure workspace directory exists."""
        if not os.path.exists(self.workspace_path):
            os.makedirs(self.workspace_path)

    def init_groq_client(self) -> None:
        """Initialize Groq client."""
        config = dotenv_values("config/.env")
        api_key = config.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY in config/.env")
        self.client = Groq(api_key=api_key.strip())

    def load_prompts(self) -> None:
        """Load prompt templates."""
        prompts_path = Path(__file__).parent / "prompts"
        
        # Load Docker prompts
        docker_path = prompts_path / "docker"
        with open(docker_path / "010_system_prompt.md") as f:
            content = f.read()
            self.docker_system_prompt = content.replace('<!--', '').replace('-->', '').strip()
        
        with open(docker_path / "020_user_prompt.md") as f:
            content = f.read()
            self.docker_user_prompt = content.replace('<!--', '').replace('-->', '').strip()
            
        # Load install prompt
        with open(prompts_path / "install" / "010_install_prompt.sh") as f:
            self.install_prompt = f.read().strip()

    def load_context(self) -> Dict[str, Any]:
        """Load analysis and recommendation files from outputs directory."""
        context = {}
        
        # Create outputs directory if it doesn't exist
        outputs_path = os.path.join(self.workspace_path, "outputs")
        if not os.path.exists(outputs_path):
            os.makedirs(outputs_path)
        
        # Load files from outputs directory
        files = {
            'plan': 'installation_plan.json',
            'analysis': 'installation_analysis.json',
            'recommendations': 'write_recommendations.json'
        }
        
        for key, filename in files.items():
            filepath = os.path.join(outputs_path, filename)
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Required file not found: {filename} in outputs directory")
            with open(filepath) as f:
                context[key] = json.load(f)
                
        return context

    def generate_install_script(self, context: Dict[str, Any]) -> InstallScriptResponse:
        """Generate installation script that will run inside the container."""
        try:
            # Unified prompt for reasoning and script generation
            message_content = {
                "role": "system",
                "content": """You are creating an installation script that will run INSIDE a container.
Your response must contain TWO sections:

1. <think> Your reasoning about installation steps
2. <script> The actual installation script

The script MUST:
- Start with #!/bin/bash
- Include error handling (e.g., set -e)
- Show progress with echo statements
- Install all dependencies in the correct order
- Set up the project environment
- Configure the application
- Execute the application
- Use only standard shell commands
- NOT include container-specific commands
- Focus on application setup only"""
            }

            user_content = {
                "role": "user",
                "content": f"""Create an installation script for the following project:

Installation Plan: {json.dumps(context['plan'], indent=2)}
Analysis: {json.dumps(context['analysis'], indent=2)}

Return ONLY:
<think>
Your reasoning about installation steps
</think>

<script>
#!/bin/bash
set -e
# Installation commands here
</script>"""
            }
            
            # Get response from LLM
            response = self.client.chat.completions.create(
                model="deepseek-r1-distill-llama-70b",
                messages=[message_content, user_content],
                temperature=0.2,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract reasoning and script
            reasoning_match = re.search(r'<think>\s*(.*?)\s*</think>', content, re.DOTALL)
            script_match = re.search(r'<script>\s*(.*?)\s*</script>', content, re.DOTALL)
            
            if not script_match:
                raise ValueError("No valid script content found in response")
            
            script_content = script_match.group(1).strip()
            reasoning_text = reasoning_match.group(1).strip() if reasoning_match else "No explicit reasoning provided"
            
            return InstallScriptResponse(
                reasoning=reasoning_text,
                script_content=script_content,
                raw_content=content
            )
            
        except Exception as e:
            console.print(f"[red]Error generating install script: {str(e)}[/red]")
            return InstallScriptResponse(
                reasoning="",
                script_content="",
                raw_content="",
                status="error",
                error=str(e)
            )

    def generate_dockerfile(self, context: Dict[str, Any]) -> DockerfileResponse:
        """Generate Dockerfile that uses the install script."""
        try:
            # Unified prompt for reasoning and Dockerfile generation
            dockerfile_request = DockerfileRequest(
                prompt="""You are a Dockerfile expert. Generate a valid Dockerfile to install and execute the install.sh script.
The response MUST contain:
1. A <think> section with your reasoning
2. A <dockerfile> section with ONLY valid Dockerfile instructions

Rules:
- The Dockerfile MUST include the following instructions: FROM, WORKDIR, COPY, RUN, CMD
- The Dockerfile MUST NOT include generic patterns like requirements.txt unless explicitly mentioned in the installation plan
- Use the steps and dependencies from the installation plan
- No markdown formatting
- No code block markers
- No explanatory text in the <dockerfile> section
- Each instruction must be properly capitalized
- Include comments with '#' where necessary
- Focus on setting up the environment and running the install.sh script""",
                model="deepseek-r1-distill-llama-70b",
                temperature=0.1,
                max_tokens=2000
            )

            user_content = {
                "role": "user",
                "content": f"""Generate a Dockerfile for the following project:

Installation Plan: {json.dumps(context['plan'], indent=2)}
Analysis: {json.dumps(context['analysis'], indent=2)}

Return ONLY:
<think>
Your reasoning about the Dockerfile structure
</think>

<dockerfile>
# Dockerfile content here:
</dockerfile>"""
            }

            # Get response from LLM
            response = self.client.chat.completions.create(
                model=dockerfile_request.model,
                messages=[
                    {"role": "system", "content": dockerfile_request.prompt},
                    {"role": "user", "content": user_content["content"]}
                ],
                temperature=dockerfile_request.temperature,
                max_tokens=dockerfile_request.max_tokens
            )
            
            raw_content = response.choices[0].message.content.strip()
            
            # Extract Dockerfile content starting from "# Dockerfile content here:"
            dockerfile_start = raw_content.find("# Dockerfile content here:")
            if dockerfile_start == -1:
                # Log invalid response for debugging
                debug_path = os.path.join(self.workspace_path, "outputs", "invalid_dockerfile_response.txt")
                with open(debug_path, 'w') as debug_file:
                    debug_file.write(raw_content)
                console.print(f"[yellow]Invalid Dockerfile response saved to {debug_path}[/yellow]")
                raise ValueError("No valid Dockerfile content found in response")
            
            dockerfile_content = raw_content[dockerfile_start + len("# Dockerfile content here:"):].strip()
            
            # Validate Dockerfile content
            required_instructions = ["FROM", "WORKDIR", "COPY", "RUN", "CMD"]
            missing_instructions = [instr for instr in required_instructions if instr not in dockerfile_content]
            if missing_instructions:
                raise ValueError(f"Dockerfile must contain the following instructions: {', '.join(missing_instructions)}")
            
            return DockerfileResponse(
                reasoning="Reasoning extracted successfully",
                dockerfile_code=dockerfile_content,
                raw_content=raw_content
            )
            
        except Exception as e:
            console.print(f"[red]Error generating Dockerfile: {str(e)}[/red]")
            return DockerfileResponse(
                reasoning="",
                dockerfile_code="",
                raw_content="",
                status="error",
                error=str(e)
            )

    @field_validator("dockerfile_code")
    def validate_dockerfile_code(cls, value):
        """Ensure the Dockerfile code contains essential instructions and no invalid tags."""
        if "<think>" in value or "</think>" in value:
            raise ValueError("Dockerfile contains invalid <think> tags")
        required_instructions = ["FROM", "WORKDIR", "COPY", "RUN", "CMD"]
        missing_instructions = [instr for instr in required_instructions if instr not in value]
        if missing_instructions:
            raise ValueError(f"Dockerfile must contain the following instructions: {', '.join(missing_instructions)}")
        return value

    def generate(self) -> GenerationResponse:
        """Generate container files and reasoning."""
        try:
            console.print("[blue]Loading context files...[/blue]")
            context = self.load_context()
            
            console.print("[blue]Generating installation script...[/blue]")
            install_script_response = self.generate_install_script(context)
            
            if install_script_response.status == "error":
                raise ValueError(install_script_response.error)
            
            install_script = install_script_response.script_content
            install_reasoning = install_script_response.reasoning
            
            console.print("[blue]Generating Dockerfile...[/blue]")
            dockerfile_response = self.generate_dockerfile(context)
            
            if dockerfile_response.status == "error":
                raise ValueError(dockerfile_response.error)
            
            dockerfile = dockerfile_response.dockerfile_code
            docker_reasoning = dockerfile_response.reasoning
            
            # Create outputs directory if it doesn't exist
            outputs_path = os.path.join(self.workspace_path, "outputs")
            if not os.path.exists(outputs_path):
                os.makedirs(outputs_path)
            
            # Save reasoning to JSON in outputs directory
            reasoning_path = os.path.join(outputs_path, "generation_reasoning.json")
            reasoning_content = {
                "install_script": install_reasoning,
                "dockerfile": docker_reasoning,
                "timestamp": datetime.now().isoformat(),
                "context_files": list(context.keys())
            }
            
            with open(reasoning_path, 'w') as f:
                json.dump(reasoning_content, f, indent=2)
            
            # Save generated files to outputs directory
            script_path = os.path.join(outputs_path, "install.sh")
            with open(script_path, 'w') as f:
                f.write(install_script)
            os.chmod(script_path, 0o755)
            
            dockerfile_path = os.path.join(outputs_path, "Dockerfile")
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile)
            
            return GenerationResponse(
                status="success",
                files_generated=[
                    "outputs/install.sh",
                    "outputs/Dockerfile",
                    "outputs/generation_reasoning.json"
                ],
                dockerfile_path=dockerfile_path,
                install_script_path=script_path
            )
            
        except Exception as e:
            console.print(f"[red]Generation error: {str(e)}[/red]")
            return GenerationResponse(
                status="error",
                error=str(e)
            )

def generate_container_files(workspace_path: str) -> Dict[str, Any]:
    """Main generation function."""
    try:
        agent = ContainerGenerationAgent(workspace_path)
        results = agent.generate()
        
        if results.status == "success":
            console.print("[green]Container files generated successfully![/green]")
            console.print(Panel(
                "\n".join(f"- {file}" for file in results.files_generated),
                title="Generated Files"
            ))
            
            # Convert Pydantic model to dict
            return {
                "status": results.status,
                "files_generated": results.files_generated,
                "dockerfile_path": results.dockerfile_path,
                "install_script_path": results.install_script_path
            }
        
        return {"status": "error", "error": results.error}
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    try:
        # Check for environment file
        if not os.path.exists("config/.env"):
            console.print("[red]Error: config/.env file not found[/red]")
            console.print("Please create config/.env file with your GROQ_API_KEY")
            sys.exit(1)
            
        # Get base experimental workspace path
        experimental_workspace = os.path.abspath(os.path.join(
            Path(__file__).parent.parent,
            "experimental_workspace"
        ))

        # Find all directories in experimental_workspace
        project_name = None
        if os.path.exists(experimental_workspace):
            # Get list of directories (excluding files)
            project_dirs = [d for d in os.listdir(experimental_workspace) 
                          if os.path.isdir(os.path.join(experimental_workspace, d))]
            
            if project_dirs:
                # If multiple projects exist, use the most recently modified one
                project_name = max(project_dirs, 
                                  key=lambda d: os.path.getmtime(os.path.join(experimental_workspace, d)))
                console.print(f"[green]Using most recent project: {project_name}[/green]")
                
                # Check if it has a metadata file to confirm it's a valid project
                metadata_path = os.path.join(experimental_workspace, project_name, "project_meta_data.json")
                if os.path.exists(metadata_path):
                    console.print(f"[green]Found project metadata for {project_name}[/green]")
                    
                    # Optionally read project details from metadata
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            console.print(f"[blue]Project GitHub URL: {metadata.get('github_url', 'Not specified')}[/blue]")
                    except:
                        console.print("[yellow]Could not read project metadata[/yellow]")
                else:
                    console.print("[yellow]No project metadata found, but continuing with most recent folder[/yellow]")
            else:
                console.print("[red]No project directories found in experimental_workspace[/red]")
                sys.exit(1)
        else:
            console.print(f"[red]Error: Experimental workspace not found at {experimental_workspace}[/red]")
            sys.exit(1)
            
        # Get absolute path to the selected project
        workspace_path = os.path.join(experimental_workspace, project_name)
        
        # Create outputs directory if it doesn't exist
        outputs_path = os.path.join(workspace_path, "outputs")
        if not os.path.exists(outputs_path):
            os.makedirs(outputs_path)
            console.print(f"[yellow]Created outputs directory: {outputs_path}[/yellow]")
        
        # Check for required input files
        required_files = ["installation_plan.json", "installation_analysis.json", "write_recommendations.json"]
        missing_files = []
        for file in required_files:
            file_path = os.path.join(outputs_path, file)
            if not os.path.exists(file_path):
                missing_files.append(file)
        
        if missing_files:
            console.print("[red]Error: Required files not found:[/red]")
            for file in missing_files:
                console.print(f"[red]- {file}[/red]")
            console.print("[yellow]Have you run analyze_agt.py and validation_agt.py first?[/yellow]")
            sys.exit(1)
        
        # Run container file generation
        console.print(f"[blue]Generating container files for project: {project_name}[/blue]")
        results = generate_container_files(workspace_path)
        
        if results["status"] == "success":
            console.print("[green]Container files generated successfully![/green]")
            console.print(Panel(
                "\n".join(f"- {file}" for file in results["files_generated"]),
                title="Generated Files"
            ))
            
            # Show next steps
            console.print("\n[blue]Next steps:[/blue]")
            console.print("[green]1. Navigate to the outputs directory:[/green]")
            console.print(f"   cd {outputs_path}")
            console.print("[green]2. Build the Docker container:[/green]")
            console.print(f"   docker build -t {project_name} .")
            console.print("[green]3. Run the container:[/green]")
            console.print(f"   docker run {project_name}")
        else:
            console.print(f"[red]Generation failed: {results.get('error', 'Unknown error')}[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")
        sys.exit(1)