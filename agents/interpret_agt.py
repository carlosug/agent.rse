import os
import json
from typing import Dict, Optional, Any
from groq import Groq
from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import sys
from pathlib import Path
import traceback
from datetime import datetime
import re

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from tools.tool_models import ReadmeAnalysisContent, ReadmeAnalysisResponse

console = Console()

def analyze_readme(repo_path: str) -> ReadmeAnalysisResponse:
    """
    Analyzes README.md file from a repository and extracts installation information.
    
    Args:
        repo_path (str): Path to the repository
        
    Returns:
        ReadmeAnalysisResponse: Structured analysis response
    """
    try:
        # Check for README.md
        readme_path = os.path.join(repo_path, "README.md")
        if not os.path.exists(readme_path):
            return ReadmeAnalysisResponse(
                status="error",
                error="README.md not found in repository"
            )

        # Load Groq API key
        CONFIG = dotenv_values("config/.env")
        api_key = CONFIG.get("GROQ_API_KEY")
        if not api_key:
            return ReadmeAnalysisResponse(
                status="error",
                error="GROQ_API_KEY not found in environment variables"
            )

        # Initialize Groq client
        client = Groq(api_key=api_key)

        # Read README content
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        # Update system message to enforce strict JSON format
        system_message = {
            "role": "system",
            "content": """You are an expert at analyzing repository documentation.
            Extract installation-related instructions from README.md and return ONLY a valid JSON object with exactly these keys:
            {
                "summary": "Brief overview of installation-relevant information",
                "methods": ["List", "of", "methods"],
                "installation_instructions_per_method": [
                    {"method": "Type 1", "order": 1, "instruction": "First step", "commands": ["command1", "command2"]},
                    {"method": "Type 1", "order": 2, "instruction": "Second step", "commands": ["command3", "command4"]}
                ],
                "prerequisites": ["List of prerequisites"],
                "dependencies": ["List of dependencies"],
                "operating_system": "Operating system",
                "config_files": ["List of files"],
                "usage_examples": [
                    {
                        "description": "Description of the use case",
                        "code": "Example code or configuration",
                        "assumptions": ["List of assumptions and considerations"],
                        "expected_output": "Expected result (optional)"
                    }
                ],
                "invocation_commands": [
                    {
                        "command": "Execution command",
                        "purpose": "What this command does",
                        "steps": ["Step associated with the command"],
                        "arguments": {
                            "arg1": "description of arg1",
                            "arg2": "description of arg2"
                        },
                        "requirements": ["Required conditions before running"]
                    }
                ],
                "environment": ["List of environment variables"],
                "important_links": ["List of links"]
            }
            
            IMPORTANT: For each installation step in "installation_instructions_per_method", always include the specific shell commands needed to execute that step in the "commands" array. Extract actual commands from code blocks or inline code sections in the README. If a step doesn't have explicit commands, make your best attempt to infer what commands would be needed.
            
            Differentiate between usage examples (how to use features) and invocation commands (how to run the software).
            Do not include any explanatory text or markdown formatting."""
        }

        # Prepare user message with README content
        user_message = {
            "role": "user",
            "content": f"Analyze this README.md for installation-relevant information:\n\n{readme_content}"
        }

        # Get analysis from Groq
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Changed to more reliable model deepseek-r1-distill-llama-70b
            messages=[system_message, user_message],
            max_tokens=2000,
            temperature=0.1
        )

        # Parse the response using Pydantic
        try:
            content = response.choices[0].message.content.strip()
            # Remove any markdown formatting
            content = content.replace('```json\n', '').replace('\n```', '').strip()
            
            try:
                # First parse as JSON
                json_data = json.loads(content)
                # Then validate with Pydantic
                analysis = ReadmeAnalysisContent.model_validate(json_data)
            except json.JSONDecodeError as json_error:
                console.print("[red]Invalid JSON format in response[/red]")
                console.print(Panel(content, title="Raw Response"))
                raise ValueError(f"Invalid JSON: {str(json_error)}")
            except Exception as validate_error:
                console.print("[red]Validation error in response[/red]")
                console.print(Panel(json.dumps(json_data, indent=2), title="Parsed JSON"))
                raise ValueError(f"Validation error: {str(validate_error)}")
            
            # Look for additional configuration files
            config_patterns = ['.env', 'config.', 'setup.cfg', 'requirements.txt']
            for root, _, files in os.walk(repo_path):
                for file in files:
                    if any(pattern in file.lower() for pattern in config_patterns):
                        rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                        if rel_path not in analysis.config_files:
                            analysis.config_files.append(rel_path)

            # Validate final result
            return ReadmeAnalysisResponse(
                status="success",
                analysis=analysis
            )

        except Exception as parse_error:
            # Add debug information
            console.print("[yellow]Debug: Model Response[/yellow]")
            console.print(content)
            return ReadmeAnalysisResponse(
                status="error",
                error=f"Failed to parse model response: {str(parse_error)}",
                analysis=ReadmeAnalysisContent(
                    summary="",
                    methods=[],  # Updated field name
                    installation_instructions_per_method=[],  # Updated field name
                    prerequisites=[],
                    dependencies=[],
                    operating_system="",
                    commands=[],
                    config_files=[],
                    usage_examples=[],
                    invocation_commands=[],
                    environment=[],
                    important_links=[]
                )
            )

    except Exception as e:
        return ReadmeAnalysisResponse(
            status="error",
            error=str(e),
            analysis=ReadmeAnalysisContent()
        )

def extract_plan_of_installation(self) -> Dict[str, Any]:
    """Extract and create an installation plan."""
    try:
        # Only look for files from extract_agt.py outputs
        installation_analysis = None
        
        # Look in the project's output directory
        analysis_file = os.path.join(self.outputs_path, "installation_analysis.json")
        
        # Load data if it exists
        if os.path.exists(analysis_file):
            try:
                with open(analysis_file, "r") as f:
                    installation_analysis = json.load(f)
                    console.print(f"[green]Loaded installation analysis from {analysis_file}[/green]")
            except:
                console.print(f"[yellow]Could not parse installation analysis from {analysis_file}[/yellow]")
        
        # Use the installation analysis or create an empty one
        analysis_data = installation_analysis or {}
        
        # If we have data, use it, otherwise generate from LLM
        if analysis_data:
            # Process existing analysis data
            console.print("[green]Using existing installation analysis[/green]")
            
            # Extract structured installation steps
            installation_steps = []
            commands = []
            
            # Extract installation steps from the analysis
            if "installation_instructions_per_method" in analysis_data:
                for instruction in analysis_data["installation_instructions_per_method"]:
                    # Create a step entry
                    step = {
                        "order": instruction.get("order", 0),
                        "description": instruction.get("instruction", ""),
                        "method": instruction.get("method", "Default"),
                        "commands": instruction.get("commands", [])
                    }
                    installation_steps.append(step)
                    
                    # Add commands to the command list
                    if instruction.get("commands"):
                        for cmd in instruction["commands"]:
                            commands.append({
                                "command": cmd,
                                "description": instruction.get("instruction", ""),
                                "method": instruction.get("method", "Default")
                            })
            
            # Extract usage information
            usage_info = self._extract_usage_information(analysis_data)
            
            # Create final installation plan
            installation_plan = {
                "status": "success",
                "summary": analysis_data.get("summary", ""),
                "prerequisites": analysis_data.get("prerequisites", []),
                "dependencies": analysis_data.get("dependencies", []),
                "operating_system": analysis_data.get("operating_system", ""),
                "steps": installation_steps,
                "methods": analysis_data.get("methods", []),
                "commands": commands,
                "usage": usage_info,
                "environment_vars": analysis_data.get("environment", []),
                "config_files": analysis_data.get("config_files", [])
            }
            
            # Save the plan to the outputs directory
            plan_file = os.path.join(self.outputs_path, "installation_plan.json")
            with open(plan_file, 'w') as f:
                json.dump(installation_plan, f, indent=2)
            
            console.print(f"[green]Installation plan created at: {plan_file}[/green]")
            
            return installation_plan
        else:
            # Generate new analysis by calling analyze_readme directly
            console.print("[yellow]No existing analysis found, generating new analysis...[/yellow]")
            
            # Get the README.md path
            readme_path = os.path.join(self.workspace_path, "README.md")
            if not os.path.exists(readme_path):
                return {
                    "status": "error",
                    "output": "",
                    "error": "README.md not found in repository"
                }
                
            # Call the analyze_readme function to generate a new analysis
            result = analyze_readme(self.workspace_path)
            
            if result.status == "success":
                # Convert Pydantic model to dictionary
                analysis_dict = json.loads(result.analysis.model_dump_json())
                
                # Save the generated analysis
                output_path = os.path.join(self.outputs_path, "installation_analysis.json")
                with open(output_path, 'w') as f:
                    json.dump(analysis_dict, f, indent=2)
                console.print(f"[green]Generated analysis saved to: {output_path}[/green]")
                
                # Now recursively call this function to use the newly created analysis
                return self.extract_plan_of_installation()
            else:
                return {
                    "status": "error",
                    "output": "",
                    "error": f"Failed to generate analysis: {result.error}"
                }
        
    except Exception as e:
        console.print(f"[red]Error creating installation plan: {str(e)}[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")
        return {
            "status": "error",
            "output": "",
            "error": str(e)
        }

def _extract_usage_information(self, analysis_data: Dict) -> Dict:
    """Extract a concise usage summary from analysis data."""
    usage_info = {
        "basic_usage": [],
        "examples": [],
        "commands": []
    }
    
    if not analysis_data:
        return {}
    
    # Extract usage examples
    if "usage_examples" in analysis_data and analysis_data["usage_examples"]:
        for example in analysis_data["usage_examples"]:
            usage_info["examples"].append({
                "description": example.get("description", ""),
                "code": example.get("code", ""),
                "expected_output": example.get("expected_output", "")
            })
    
    # Extract invocation commands
    if "invocation_commands" in analysis_data and analysis_data["invocation_commands"]:
        for cmd in analysis_data["invocation_commands"]:
            cmd_info = {
                "command": cmd.get("command", ""),
                "purpose": cmd.get("purpose", ""),
                "arguments": cmd.get("arguments", {})
            }
            usage_info["commands"].append(cmd_info)
    
    # Extract summary from installation methods
    if "summary" in analysis_data and analysis_data["summary"]:
        usage_info["summary"] = analysis_data["summary"]
    
    # Include basic usage instructions if available
    if "commands" in analysis_data and analysis_data["commands"]:
        # Get the latest commands (likely to be usage commands)
        latest_commands = sorted(analysis_data["commands"], 
                                key=lambda x: x.get("step_order", 0), 
                                reverse=True)[:3]
        
        for cmd in latest_commands:
            usage_info["basic_usage"].append({
                "command": cmd.get("command", ""),
                "description": cmd.get("description", "")
            })
    
    return usage_info

if __name__ == "__main__":
    try:
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
        
        # Create outputs directory
        outputs_path = os.path.join(workspace_path, "outputs")
        if not os.path.exists(outputs_path):
            os.makedirs(outputs_path)
        
        console.print(f"[blue]Analyzing repository at: {workspace_path}[/blue]")
        
        # Run analysis
        result = analyze_readme(workspace_path)
        
        if result.status == "success":
            # Format installation steps for better readability
            analysis_dict = json.loads(result.analysis.model_dump_json())
            
            # Sort and process installation instructions
            if analysis_dict.get("installation_instructions_per_method"):
                analysis_dict["installation_instructions_per_method"].sort(
                    key=lambda x: (x["method"], x["order"])
                )
                
                # Extract all commands into a separate list for easier access
                all_commands = []
                for instruction in analysis_dict.get("installation_instructions_per_method", []):
                    if "commands" in instruction and instruction["commands"]:
                        for cmd in instruction["commands"]:
                            all_commands.append({
                                "command": cmd,
                                "method": instruction["method"],
                                "step_order": instruction["order"],
                                "description": instruction["instruction"]
                            })
                
                # Add the extracted commands to the output
                analysis_dict["commands"] = all_commands
            
            # Group instructions by method
            methods_dict = {}
            for instruction in analysis_dict.get("installation_instructions_per_method", []):
                method = instruction["method"]
                if method not in methods_dict:
                    methods_dict[method] = []
                methods_dict[method].append(instruction)
            
            analysis_dict["installation_by_method"] = methods_dict
            
            # Format for display
            formatted_json = json.dumps(analysis_dict, indent=2)
            
            # Print formatted analysis
            console.print(Panel(
                Syntax(
                    formatted_json,
                    "json",
                    theme="monokai",
                    line_numbers=True
                ),
                title="Installation Analysis",
                expand=False
            ))
            
            # Save analysis to outputs directory
            output_path = os.path.join(outputs_path, "installation_analysis.json")
            with open(output_path, 'w') as f:
                f.write(formatted_json)
            console.print(f"[green]Analysis saved to: {output_path}[/green]")
        else:
            console.print(f"[red]Analysis failed: {result.error}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error running analysis: {str(e)}[/red]")
        sys.exit(1)