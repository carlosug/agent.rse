import os
import json
from typing import Dict, Any
from groq import Groq
from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from pathlib import Path
import sys
import instructor  # Add this import at the top of your file, with your other imports

sys.path.append(str(Path(__file__).parent.parent))
from tools.tool_models import (
    AnalysisResponse,
    ToolCommand,
    InstallationAnalysisResponse,
    InstallationMethod,
    ReasoningAnalysis,
    InstallationPlan,
    ReadmeAnalysisContent,
    PlanStep
)
from tools.linux_terminal import get_terminal
from tools.terminal import search_error_solutions

console = Console()

def clean_json_response(content: str) -> str:
    """Cleans the JSON response from markdown and formatting."""
    try:
        # Remove markdown code block markers
        content = content.replace('```json', '').replace('```', '')
        # Remove any leading/trailing whitespace
        content = content.strip()
        
        # Try to find JSON-like content between curly braces
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx >= 0 and end_idx > start_idx:
            content = content[start_idx:end_idx + 1]
            
        # Validate JSON structure
        json.loads(content)  # This will raise JSONDecodeError if invalid
        return content
        
    except json.JSONDecodeError:
        raise ValueError(
            f"Invalid JSON structure in response. Raw content:\n{content}"
        )

def validate_installation_plan_structure(plan_dict: Dict) -> None:
    """Validates the installation plan structure."""
    if not plan_dict:
        raise ValueError("Installation plan is empty")
        
    required_fields = ["chosen_method", "reason", "steps"]
    missing = [f for f in required_fields if f not in plan_dict]
    if missing:
        raise ValueError(f"Missing required installation plan fields: {missing}")
        
    if not plan_dict["steps"]:
        raise ValueError("Installation plan steps list is empty")
        
    for idx, step in enumerate(plan_dict["steps"], 1):
        required_step_fields = ["order", "method", "description"]
        missing_step = [f for f in required_step_fields if f not in step]
        if missing_step:
            raise ValueError(f"Step {idx} missing required fields: {missing_step}")
        
        # Warn if command is missing but not fail
        if "command" not in step:
            console.print(f"[yellow]Warning: Step {idx} is missing command field[/yellow]")
    
    # Warn if usage examples are missing
    if "usage_examples" not in plan_dict or not plan_dict["usage_examples"]:
        console.print("[yellow]Warning: Installation plan is missing usage examples[/yellow]")
        # Create default usage example if missing
        plan_dict["usage_examples"] = [{"description": "Basic usage", "code": "See project documentation"}]

def analyze_readme_content(readme_content: str) -> Dict[str, Any]:
    """
    Analyze README content to extract installation information using Instructor pattern.
    
    Args:
        readme_content: Content of the README.md file
        
    Returns:
        Dict with analysis results
    """
    try:
        # Load Groq API key with better error handling
        CONFIG = dotenv_values("config/.env")
        api_key = CONFIG.get("GROQ_API_KEY")
        if not api_key or not api_key.strip():
            raise ValueError(
                "Invalid GROQ_API_KEY in config/.env\n"
                "Please ensure you have a valid API key from https://console.groq.com"
            )

        # Initialize Groq client with validation
        client = Groq(api_key=api_key.strip())
        
        # Initialize the instructor client
        instructor_client = instructor.from_groq(client)
        
        # Update the system message to explain the flexibility with methods
        prompt = f"""Analyze this README.md for installation-relevant information. 
Be flexible with installation methods - if you discover non-standard installation methods 
beyond common ones like pip, conda, docker, etc., include them in the 'methods' list 
with their actual names as found in the README.

README content:

{readme_content}"""
        
        try:
            # Use Instructor to get structured output
            console.print("[cyan]Requesting analysis from GROQ using Instructor...[/cyan]")
            analysis = instructor_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                response_model=ReadmeAnalysisContent,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing repository documentation. Extract installation-related instructions from README.md, including ANY custom or non-standard installation methods."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            # Convert to dict for consistency
            analysis_dict = json.loads(analysis.model_dump_json())
            console.print(f"[green]Successfully parsed README into structured format[/green]")
            
            return {
                "status": "success",
                "analysis": analysis_dict
            }
            
        except Exception as instructor_error:
            console.print(f"[red]Error using Instructor: {str(instructor_error)}[/red]")
            
            # Try without instructor as fallback
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing repository documentation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            
            # Try to extract JSON
            try:
                # Extract text between curly braces
                import re
                json_pattern = re.compile(r"\{.*\}", re.DOTALL)
                match = json_pattern.search(content)
                
                if match:
                    json_content = match.group(0)
                    analysis_data = json.loads(json_content)
                    return {
                        "status": "success",
                        "analysis": analysis_data
                    }
                else:
                    return {
                        "status": "error",
                        "error": "Could not extract JSON from response"
                    }
            except Exception as json_error:
                return {
                    "status": "error", 
                    "error": f"Error parsing response: {str(json_error)}"
                }
            
    except Exception as e:
        console.print(f"[red]Error preparing README analysis: {str(e)}[/red]")
        return {
            "status": "error",
            "error": f"Error in README analysis: {str(e)}"
        }

def analyze_project_files(workspace_path: str) -> Dict[str, Any]:
    """Analyzes installation requirements and suggests next steps."""
    try:
        # Create outputs directory if it doesn't exist
        outputs_path = os.path.join(workspace_path, "outputs")
        if not os.path.exists(outputs_path):
            os.makedirs(outputs_path)

        # Initialize terminal
        terminal = get_terminal(workspace_path)
        
        # Load installation analysis from outputs directory
        analysis_path = os.path.join(outputs_path, "installation_analysis.json") #input from interpret_agt.py
        if not os.path.exists(analysis_path):
            raise FileNotFoundError("installation_analysis.json not found in outputs directory")
            
        with open(analysis_path, 'r') as f:
            install_analysis = json.load(f)

        # Collect installation-related files content - BUT LIMIT SIZE
        files_content = {}
        
        # Read README.md if exists - limit to first 1000 characters
        readme_path = os.path.join(workspace_path, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, 'r') as f:
                readme_content = f.read()
                # Truncate to reduce tokens
                files_content["readme"] = readme_content[:1000] + ("..." if len(readme_content) > 1000 else "")

        # Check for key installation files - with size limits
        key_files = ["requirements.txt", "setup.py", "Dockerfile", ".env.example", "install.sh"]
        # Add any other relevant files you want to check
        for file in key_files:
            file_path = os.path.join(workspace_path, file)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    file_content = f.read()
                    # Truncate to reduce tokens
                    files_content[file] = file_content[:500] + ("..." if len(file_content) > 500 else "")

        # Process and simplify installation analysis to reduce tokens
        simplified_analysis = {
            "dependencies": install_analysis.get("dependencies", [])[:20],  # Limit dependencies 
            "language": install_analysis.get("language", "unknown"),
            "environment": install_analysis.get("environment", "unknown"),
            "installation_options": install_analysis.get("installation_options", [])[:5],  # Limit options
            "commands": install_analysis.get("commands", [])[:10],  # Add commands list
            "usage_examples": install_analysis.get("usage_examples", []),
            "invocation_commands": install_analysis.get("invocation_commands", [])
        }

        # Extract commands from installation instructions if available
        commands_list = []

        if "installation_instructions_per_method" in install_analysis:
            for instruction in install_analysis.get("installation_instructions_per_method", []):
                if "commands" in instruction and instruction["commands"]:
                    for cmd in instruction["commands"]:
                        commands_list.append({
                            "command": cmd,
                            "method": instruction.get("method", "unknown"),
                            "step_order": instruction.get("order", 0),
                            "description": instruction.get("instruction", "")
                        })
                        
        # Add extracted commands to simplified analysis
        simplified_analysis["commands"] = commands_list[:10]  # Limit to 10 commands

        # If installation instructions exist, add them with commands
        if "installation_instructions_per_method" in install_analysis:
            # Group instructions by method and include commands
            methods_with_commands = {}
            for instruction in install_analysis.get("installation_instructions_per_method", [])[:5]:
                method = instruction.get("method")
                if method not in methods_with_commands:
                    methods_with_commands[method] = []
                    
                # Find matching command for this instruction if possible
                command = ""
                for cmd in install_analysis.get("commands", []):
                    # Simple heuristic - if command contains keywords from instruction
                    instruction_text = instruction.get("instruction", "")
                    if all(keyword in cmd for keyword in instruction_text.split()):
                        command = cmd
                        break
                
                methods_with_commands[method].append({
                    "instruction": instruction_text,
                    "command": command
                })
            
            simplified_analysis["installation_instructions_per_method"] = methods_with_commands

        if "installation_steps" in install_analysis:
            simplified_analysis["installation_steps"] = install_analysis["installation_steps"][:3]  # Limit steps
            
        if "config_files" in install_analysis:
            simplified_analysis["config_files"] = install_analysis["config_files"][:5]  # Limit config files

        # Load Groq API key with better error handling
        CONFIG = dotenv_values("config/.env")
        api_key = CONFIG.get("GROQ_API_KEY")
        if not api_key or not api_key.strip():
            raise ValueError(
                "Invalid GROQ_API_KEY in config/.env\n"
                "Please ensure you have a valid API key from https://console.groq.com"
            )

        # Initialize Groq client with validation
        client = Groq(api_key=api_key.strip())
        
        # Prepare context for analysis - simplified to reduce tokens
        project_context = {
            "installation_analysis": simplified_analysis,
            "files_found": list(files_content.keys()),
            "files_content": files_content
        }

        # Modify system message to be more concise
        system_message = {
            "role": "system",
            "content": """You are an expert at analyzing software installation requirements. Your tasks is to create a detailed plan of actions in order to install and run the software based on the provided context.
            Return a JSON object with these fields: reasoning (analysis, method_choice, next_steps, installation_plan), 
            tool, installation_method, and safe_to_execute."""
        }

        # Update the user message to explicitly request usage examples and testing instructions
        example_single_command = '{"order": 1, "method": "pip", "description": "Install requirements", "command": "pip install -r requirements.txt"}'
        example_multiple_commands = '{"order": 3, "method": "source", "description": "Install and activate", "command": ["pip install poetry", "poetry install", "poetry shell"]}'
        example_usage_example = '{"description": "Basic usage", "code": "python nemesis.py --target your_target"}'

        user_message = {
            "role": "user",
            "content": f"""Analyze these installation requirements:
            {json.dumps(project_context, indent=1)}
            
            Return a JSON object with:
            - reasoning (analysis, method_choice, next_steps, installation_plan)
            - tool (name, args with cmd)
            - installation_method (pip|docker|source)
            - safe_to_execute (boolean)
            
            The installation_plan must include: 
            - chosen_method: preferred installation method
            - reason: why this method was chosen
            - steps: an array of step objects, each with:
                - order: integer step number
                - method: installation method this step uses
                - description: what this step does
                - command: EITHER a string for a single command OR an array of strings for multiple commands
                - dependencies: optional array of dependencies required for this step
            - usage_examples: array of usage example objects with description and code fields
            - invocation_commands: array of commands to run the software
            - operating_systems: array of compatible OS names
            
            IMPORTANT: For steps that require multiple commands, use an array of command strings rather than concatenating them.
            IMPORTANT: Always include usage examples and commands for running the software after installation.
            
            Example step with single command:
            {example_single_command}
            
            Example step with multiple commands:
            {example_multiple_commands}
            
            Example usage example:
            {example_usage_example}
            """
        }

        # Try with a different model that has higher token limits
        console.print("[yellow]Attempting analysis with llama-3.3-70b-versatile model...[/yellow]")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Change to a model with higher token limits
            messages=[system_message, user_message],
            temperature=0.3,  # Lower temperature for more structured output
            max_tokens=2000,
            top_p=0.95
        )

        # Update robust response parsing with cleaning
        try:
            content = response.choices[0].message.content.strip()
            
            # Debug output of original response
            console.print("[yellow]Original Response:[/yellow]")
            console.print(Panel(content, title="Raw Response"))
            
            # Clean the response
            cleaned_content = clean_json_response(content)
            
            # Debug output of cleaned response
            console.print("[yellow]Cleaned Response:[/yellow]")
            console.print(Panel(cleaned_content, title="Cleaned JSON"))
            
            try:
                # Parse the cleaned JSON
                analysis_dict = json.loads(cleaned_content)
                
                # Debug the structure
                console.print("[yellow]Parsed JSON structure:[/yellow]")
                console.print(Panel(json.dumps(analysis_dict, indent=2), title="JSON Structure"))
                
                # Validate required fields and structure
                required_fields = ["reasoning", "tool", "installation_method"]
                if not all(field in analysis_dict for field in required_fields):
                    missing = [f for f in required_fields if f not in analysis_dict]
                    raise ValueError(f"Missing required fields: {missing}")
                
                required_reasoning = ["analysis", "method_choice", "next_steps"]
                if not all(field in analysis_dict["reasoning"] for field in required_reasoning):
                    missing = [f for f in required_reasoning if f not in analysis_dict["reasoning"]]
                    raise ValueError(f"Missing reasoning fields: {missing}")
                
                required_tool = ["name", "args"]
                if not all(field in analysis_dict["tool"] for field in required_tool):
                    missing = [f for f in required_tool if f not in analysis_dict["tool"]]
                    raise ValueError(f"Missing tool fields: {missing}")
                
                # Create installation plan from response
                plan_dict = analysis_dict["reasoning"].get("installation_plan")
                if not plan_dict:
                    console.print("[red]Debug: Reasoning section contains:[/red]")
                    console.print(Panel(json.dumps(analysis_dict["reasoning"], indent=2)))
                    raise ValueError("Missing installation plan in response")

                # Validate plan structure
                validate_installation_plan_structure(plan_dict)

                # Convert steps to PlanStep objects
                steps = []
                for idx, step_dict in enumerate(plan_dict["steps"], 1):
                    try:
                        # Use our safer creation method
                        step = PlanStep.safe_create(**step_dict)
                        steps.append(step)
                        
                        # Add command warning only if we actually need to warn
                        if "command" not in step_dict or step_dict["command"] is None:
                            console.print(f"[yellow]Warning: Step {idx} is missing command field[/yellow]")
                        
                    except Exception as step_error:
                        console.print(f"[red]Error parsing step {idx}: {str(step_error)}[/red]")
                        console.print(Panel(str(step_dict), title=f"Problem Step {idx}"))
                        # Use a bare minimum step as fallback
                        try:
                            fixed_step = PlanStep(
                                order=idx,
                                method="undefined",
                                description=f"Step {idx} (parsing failed)",
                                command=None,
                                dependencies=[]
                            )
                            steps.append(fixed_step)
                            console.print(f"[green]Added placeholder for step {idx}[/green]")
                        except Exception as e:
                            console.print(f"[red]Could not create placeholder for step {idx}: {str(e)}[/red]")

                installation_plan = InstallationPlan(
                    chosen_method=plan_dict["chosen_method"],
                    reason=plan_dict["reason"],
                    steps=steps,
                    fallback_method=plan_dict.get("fallback_method")
                )

                # Convert tool args to appropriate format
                tool_args = analysis_dict["tool"]["args"]
                if isinstance(tool_args, list):
                    if analysis_dict["tool"]["name"] == "docker":
                        tool_args = {"cmd": "docker " + " ".join(tool_args)}
                    else:
                        tool_args = {"cmd": " ".join(tool_args)}

                # Create analysis object from the parsed dict
                analysis = AnalysisResponse(
                    status="success",
                    reasoning=ReasoningAnalysis(
                        analysis=analysis_dict["reasoning"]["analysis"],
                        method_choice=analysis_dict["reasoning"]["method_choice"],
                        next_steps=analysis_dict["reasoning"]["next_steps"]
                    ),
                    tool=ToolCommand(
                        name=analysis_dict["tool"]["name"],
                        args=tool_args
                    ),
                    installation_method=InstallationMethod(analysis_dict["installation_method"]),
                    safe_to_execute=analysis_dict.get("safe_to_execute", False),
                    installation_plan=installation_plan
                )

                # Update the plan path to use outputs directory
                plan_path = os.path.join(outputs_path, "installation_plan.json")

                # Create plan data with proper command handling
                plan_data = {
                    "chosen_method": plan_dict["chosen_method"],
                    "reason": plan_dict["reason"],
                    "steps": [
                        {
                            # Use model_dump() to convert to dict, but manually handle the command field
                            **{k: v for k, v in step.model_dump().items() if k != "command"},
                            # Ensure command is always a list format in the JSON output
                            "command": step.get_commands_as_list()
                        } 
                        for step in steps
                    ],
                    "fallback_method": plan_dict.get("fallback_method"),
                    "safe_to_execute": analysis_dict.get("safe_to_execute", False),
                    # Add usage examples and commands
                    "usage_examples": plan_dict.get("usage_examples", []),
                    "invocation_commands": plan_dict.get("invocation_commands", []),
                    "operating_systems": plan_dict.get("operating_systems", ["Linux"]),
                }
                
                with open(plan_path, 'w') as f:
                    json.dump(plan_data, f, indent=2)
                
                console.print(f"[green]Installation plan saved to: {plan_path}[/green]")
                
                # Display the installation analysis summary
                console.print(Panel(
                    f"[yellow]Analysis:[/yellow]\n{analysis_dict['reasoning']['analysis']}\n\n" +
                    f"[yellow]Method Choice:[/yellow]\n{analysis_dict['reasoning']['method_choice']}\n\n" +
                    f"[yellow]Next Steps:[/yellow]\n{analysis_dict['reasoning']['next_steps']}",
                    title="Installation Requirements Analysis",
                    expand=False
                ))

                # Display plan summary
                console.print(Panel(
                    f"[blue]Chosen Method:[/blue] {plan_dict['chosen_method']}\n" +
                    f"[blue]Reason:[/blue] {plan_dict['reason']}\n" +
                    f"[blue]Steps:[/blue] {len(steps)}\n" +
                    f"[blue]Safe to Execute:[/blue] {analysis_dict.get('safe_to_execute', False)}",
                    title="Installation Plan Summary"
                ))

                console.print("\n[green]Analysis completed. Run validation_agt.py to validate the installation plan.[/green]")
                
                return analysis.model_dump()

            except json.JSONDecodeError as json_err:
                console.print("[red]Failed to parse JSON response[/red]")
                console.print(Panel(cleaned_content, title="Invalid JSON"))
                raise ValueError(f"Invalid JSON in response: {str(json_err)}")
            
        except Exception as parse_error:
            console.print(f"[red]Error parsing model response: {str(parse_error)}[/red]")
            raise

    except Exception as e:
        error_message = str(e)
        console.print(f"[red]Error analyzing installation requirements: {error_message}[/red]")
        return {
            "status": "error",
            "error": error_message,
            "reasoning": {
                "analysis": "",
                "method_choice": "",
                "next_steps": ""
            },
            "tool": {
                "name": "linux_terminal",
                "args": {"cmd": ""}
            },
            "installation_method": "unknown",
            "safe_to_execute": False
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
        workspace_path = os.path.abspath(os.path.join(experimental_workspace, project_name))
        
        # Create outputs directory
        outputs_path = os.path.join(workspace_path, "outputs")
        if not os.path.exists(outputs_path):
            os.makedirs(outputs_path)
        
        # Verify installation_analysis.json exists in outputs directory
        analysis_file = os.path.join(outputs_path, "installation_analysis.json")
        if not os.path.exists(analysis_file):
            console.print("[red]Error: installation_analysis.json not found[/red]")
            console.print(f"Expected at: {analysis_file}")
            sys.exit(1)
            
        try:
            with open(analysis_file) as f:
                json.load(f)  # Validate JSON structure
        except json.JSONDecodeError:
            console.print("[red]Error: Invalid JSON in installation_analysis.json[/red]")
            sys.exit(1)
            
        console.print(f"[blue]Analyzing project at: {workspace_path}[/blue]")
        analysis = analyze_project_files(workspace_path)
        
        if not analysis:
            console.print("[red]Analysis failed: No response received[/red]")
            sys.exit(1)
            
        if analysis.get("status") == "error":
            error_message = analysis.get("error", "Unknown error")
            console.print(f"[red]Analysis failed: {error_message}[/red]")
            
            # Search for solutions
            console.print("\n[yellow]Searching for solutions to the error...[/yellow]")
            solutions = search_error_solutions(error_message)
            
            if not solutions['stackoverflow'] and not solutions['google']:
                console.print("[red]No solutions found[/red]")
            
            sys.exit(1)
            
        console.print("[green]Analysis completed successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)