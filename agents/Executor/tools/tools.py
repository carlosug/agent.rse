import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.syntax import Syntax
import json
import os
import sys
import shutil
import traceback
from groq import Groq
from dotenv import dotenv_values

# Add parent directory to path to import from agent.py
sys.path.append(str(Path(__file__).parent.parent))
try:
    from agent import init_groq_client
except ImportError:
    # Define the function locally if import fails
    def init_groq_client():
        """Initialize and return a Groq API client."""
        try:
            # Try to load from config/.env first
            config = dotenv_values("config/.env")
            api_key = config.get("GROQ_API_KEY")
            
            # Fallback to environment variable if not in .env
            if not api_key:
                api_key = os.environ.get("GROQ_API_KEY")
                
            if not api_key:
                raise ValueError("GROQ_API_KEY not found in config/.env or environment")
                
            return Groq(api_key=api_key.strip())
            
        except Exception as e:
            raise ValueError(f"Failed to initialize Groq client: {str(e)}")

console = Console()

# Define both workspace folders
EXPERIMENTAL_WORKSPACE = "experimental_workspace"
WORKSPACE_FOLDER = "execution_agent_workspace"
OUTPUT_DIR = "outputs"  # This matches the actual directory name


def ensure_workspace_exists(base_path: str) -> Dict[str, str]:
    """Verify workspace directory structure exists and copy necessary files."""
    try:
        console.print(f"[cyan]Setting up workspace structure: {base_path}[/cyan]")
        
        # Use WORKSPACE_FOLDER as base and append the relative path
        root_workspace = Path(base_path).resolve()  # Get absolute path
        output_path = root_workspace / OUTPUT_DIR
        
        # Create directories if they don't exist
        root_workspace.mkdir(exist_ok=True)
        console.print(f"[green]Created or verified directory: {root_workspace}[/green]")
        
        output_path.mkdir(exist_ok=True)
        console.print(f"[green]Created or verified outputs directory: {output_path}[/green]")
        
        # Find source install.sh in experimental workspace
        experimental_path = Path(EXPERIMENTAL_WORKSPACE).resolve()
        
        # Try multiple potential source locations
        potential_sources = [
            experimental_path / "somef" / OUTPUT_DIR,  # Primary location
            experimental_path / OUTPUT_DIR,          # Alternative location
        ]
        
        source_path = None
        for path in potential_sources:
            if path.exists() and (path / "install.sh").exists():
                source_path = path
                break
        
        if not source_path:
            # Search all subdirectories for outputs/install.sh if not found in expected locations
            for subdir in experimental_path.iterdir():
                if not subdir.is_dir():
                    continue
                potential_source = subdir / OUTPUT_DIR / "install.sh"
                if potential_source.exists():
                    source_path = subdir / OUTPUT_DIR
                    break
        
        if not source_path:
            return {
                "status": "error",
                "message": f"Could not find install.sh in {experimental_path}"
            }
            
        console.print(f"[green]Found source files at: {source_path}[/green]")
        
        # Copy install.sh and Dockerfile if they exist
        files_copied = []
        for file_name in ["install.sh", "Dockerfile"]:
            source_file = source_path / file_name
            if source_file.exists():
                dest_file = output_path / file_name
                shutil.copy2(source_file, dest_file)
                console.print(f"[green]Copied {file_name} to {dest_file}[/green]")
                
                # Make executable if it's a script
                if file_name.endswith(".sh"):
                    os.chmod(dest_file, 0o755)  # Make executable
                    console.print(f"[green]Made {file_name} executable[/green]")
                
                files_copied.append(file_name)
        
        if not files_copied:
            return {
                "status": "error",
                "message": f"No files found to copy from {source_path}"
            }
            
        # All directories exist and files copied
        return {
            "status": "success",
            "workspace_path": str(root_workspace),
            "output_path": str(output_path),
            "files_copied": files_copied,
            "message": f"Workspace structure prepared successfully. Copied: {', '.join(files_copied)}"
        }
            
    except Exception as e:
        console.print(f"[red]Error preparing workspace: {str(e)}[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")
        return {
            "status": "error",
            "message": f"Error preparing workspace: {str(e)}"
        }

def find_install_script(path: str) -> Dict[str, str]:
    """Locate install.sh script in outputs directory."""
    try:
        script_path = Path(path) / "outputs" / "install.sh"
        
        if script_path.is_file():
            return {
                "status": "success",
                "script_path": str(script_path),
                "message": f"Found install.sh at: {script_path}"
            }
        
        return {
            "status": "error",
            "message": f"install.sh not found at: {script_path}"
        }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error finding install script: {str(e)}"
        }

def run_install_script(script_path: str) -> Dict[str, Any]:
    """Execute install.sh and save logs."""
    try:
        console.print(f"[cyan]Running installation script: {script_path}[/cyan]")
        
        script_path_obj = Path(script_path)
        
        # Check if script exists at absolute path
        if not script_path_obj.is_absolute():
            # Try relative to current directory
            script_path_obj = Path.cwd() / script_path_obj
        
        # Also check relative to workspace root
        if not script_path_obj.exists():
            alt_path = Path(WORKSPACE_FOLDER) / 'outputs' / 'install.sh'
            console.print(f"[yellow]Script not found at {script_path_obj}, trying {alt_path}[/yellow]")
            if alt_path.exists():
                script_path_obj = alt_path
            else:
                # Try experimental workspace as a last resort
                exp_path = Path(EXPERIMENTAL_WORKSPACE) / 'somef' / 'outputs' / 'install.sh' #TO DO: make it more flexible sice it has to be modified the repo name
                console.print(f"[yellow]Script not found at {alt_path}, trying {exp_path}[/yellow]")
                if exp_path.exists():
                    # Copy to execution workspace first
                    target_dir = Path(WORKSPACE_FOLDER) / 'outputs'
                    target_dir.mkdir(exist_ok=True)
                    target_path = target_dir / 'install.sh'
                    shutil.copy2(exp_path, target_path)
                    os.chmod(target_path, 0o755)
                    script_path_obj = target_path
                    console.print(f"[green]Copied script from {exp_path} to {target_path}[/green]")
                else:
                    raise FileNotFoundError(f"Script not found: {script_path}")
        
        if not script_path_obj.is_file():
            raise FileNotFoundError(f"Script path is not a file: {script_path_obj}")
        
        # Display script content
        console.print(f"[yellow]Script content:[/yellow]")
        with open(script_path_obj, 'r') as f:
            script_content = f.read()
            console.print(script_content[:500] + ("..." if len(script_content) > 500 else ""))
        
        # Setup log files in the same directory as the script
        log_dir = script_path_obj.parent
        log_file = log_dir / "installation.log"
        error_file = log_dir / "installation_errors.log"
        
        # Make sure script is executable
        os.chmod(script_path_obj, 0o755)
        console.print(f"[green]Made script executable: {script_path_obj}[/green]")
        
        # Create a modified version of the script that redirects output
        temp_script = log_dir / "wrapped_install.sh"
        with open(temp_script, 'w') as f:
            f.write(f"""#!/bin/bash
# Wrapper script to capture output
cd {script_path_obj.parent}
exec 1> {log_file} 2> {error_file}
echo "Starting installation at $(date)"
./$(basename {script_path_obj})
exit_code=$?
echo "Installation finished at $(date) with exit code $exit_code"
exit $exit_code
""")
        os.chmod(temp_script, 0o755)
        
        console.print(f"[yellow]Running script with output redirected to {log_file} and {error_file}[/yellow]")
        
        # Run the wrapper script
        process = subprocess.run(
            f"{temp_script}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Check for output even if redirected
        if process.stdout:
            console.print("[yellow]Script output:[/yellow]")
            console.print(process.stdout)
        if process.stderr:
            console.print("[red]Script errors:[/red]")
            console.print(process.stderr)
        
        # Check if log files were created
        if log_file.exists():
            with open(log_file, 'r') as f:
                log_content = f.read()
                console.print(f"[green]Installation log ({len(log_content)} bytes)[/green]")
                if len(log_content) < 1000:
                    console.print(log_content)
        
        if error_file.exists():
            with open(error_file, 'r') as f:
                error_content = f.read()
                if error_content.strip():
                    console.print(f"[red]Installation errors ({len(error_content)} bytes)[/red]")
                    if len(error_content) < 1000:
                        console.print(error_content)
        
        if process.returncode == 0:
            return {
                "status": "success",
                "returncode": process.returncode,
                "output_log": str(log_file),
                "error_log": str(error_file),
                "message": "Installation completed successfully"
            }
        else:
            return {
                "status": "error",
                "returncode": process.returncode,
                "output_log": str(log_file),
                "error_log": str(error_file),
                "message": f"Installation failed with code {process.returncode}"
            }
            
    except Exception as e:
        console.print(f"[red]Error running install script: {str(e)}[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")
        return {
            "status": "error",
            "message": f"Error running install script: {str(e)}"
        }

def formulate_error_search_prompt(error_file: str) -> Dict[str, str]:
    """Create search query from error logs using GROQ."""
    try:
        error_path = Path(error_file)
        if not error_path.is_file():
            return {
                "status": "error",
                "message": f"Error log not found: {error_path}"
            }

        error_content = error_path.read_text().strip()
        if not error_content:
            return {
                "status": "error",
                "message": "Error log is empty"
            }

        # Use GROQ to analyze error
        client = init_groq_client()
        response = client.chat.completions.create(
            model= "qwen/qwen3-32b", # at 12.09.2025 deprecated "qwen-qwq-32b", # deprecarted "qwen-2.5-32b",
            messages=[
                {"role": "system", "content": "We are tring to install the <REP_URL> repository. An error has arised. Inspect error_content and suggest a prompt for searching in solution in the web:"},
                {"role": "user", "content": error_content}
            ]
        )
        
        return {
            "status": "success",
            "search_query": response.choices[0].message.content.strip(),
            "error_content": error_content[:200],
            "message": "Search query created"
        }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error creating search query: {str(e)}"
        }

def copy_missing_files(source_path: str, target_path: str, files_to_copy: List[str]) -> Dict[str, Any]:
    """Copy missing files from source to target path."""
    try:
        console.print(f"[cyan]Copying missing files from {source_path} to {target_path}[/cyan]")
        
        # Ensure paths exist
        source_path_obj = Path(source_path)
        target_path_obj = Path(target_path)
        
        if not source_path_obj.exists():
            return {
                "status": "error",
                "message": f"Source path not found: {source_path}"
            }
            
        # Create target directory if it doesn't exist
        target_path_obj.mkdir(exist_ok=True, parents=True)
        console.print(f"[green]Ensured target directory exists: {target_path_obj}[/green]")
        
        # Try to find files in multiple locations
        copied_files = []
        not_found_files = []
        
        # First try the provided source path
        for filename in files_to_copy:
            source_file = source_path_obj / filename
            
            if not source_file.exists():
                # Try in experimental_workspace with different subdirectories
                exp_path = Path(EXPERIMENTAL_WORKSPACE)
                
                # Try a few common locations
                potential_locations = [
                    exp_path / "somef" / "outputs" / filename, # todo: make it more flexible since it has to be modified the repo name
                    exp_path / "outputs" / filename,
                    exp_path / filename
                ]
                
                # Also search in any subdirectory
                for subdir in exp_path.glob("**/"):
                    if subdir.is_dir() and not any(str(subdir).startswith(str(p)) for p in potential_locations):
                        potential_locations.append(subdir / filename)
                
                # Try all potential locations
                found = False
                for location in potential_locations:
                    if location.exists():
                        source_file = location
                        found = True
                        console.print(f"[green]Found {filename} at alternative location: {location}[/green]")
                        break
                        
                if not found:
                    not_found_files.append(filename)
                    console.print(f"[yellow]Could not find {filename} in any location[/yellow]")
                    continue
            
            # File found, copy it
            target_file = target_path_obj / filename
            shutil.copy2(source_file, target_file)
            console.print(f"[green]Copied {filename} to {target_file}[/green]")
            copied_files.append(filename)
        
        # Return results without creating fallback files
        if copied_files:
            return {
                "status": "success",
                "copied_files": copied_files,
                "not_found_files": not_found_files,
                "message": f"Successfully copied {len(copied_files)} files."
            }
        else:
            return {
                "status": "error",
                "not_found_files": not_found_files,
                "message": f"No files were found to copy. Please check error logs for more details."
            }
            
    except Exception as e:
        console.print(f"[red]Error copying missing files: {str(e)}[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")
        return {
            "status": "error",
            "message": f"Error copying missing files: {str(e)}"
        }

def execute_tool_in_terminal(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a requested tool directly."""
    try:
        console.print(f"[cyan]🔧 Executing tool: {name}[/cyan]")
        console.print(f"[dim]With arguments: {arguments}[/dim]")
        
        # Handle nested tool structure (used by the agent)
        # This is the pattern {"name": "tool_name", "arguments": {...}}
        if name == "execute_tool_in_terminal":
            if "name" in arguments and "arguments" in arguments:
                nested_name = arguments["name"]
                nested_args = arguments["arguments"]
                console.print(f"[yellow]Unwrapping nested tool: {nested_name}[/yellow]")
                
                # Recursively call with the inner tool
                return execute_tool_in_terminal(nested_name, nested_args)
        
        # Direct tool execution
        if name == "ensure_workspace_exists":
            return ensure_workspace_exists(arguments.get("base_path", WORKSPACE_FOLDER))
            
        elif name == "find_install_script":
            return find_install_script(arguments.get("path", WORKSPACE_FOLDER))
            
        elif name == "run_install_script":
            return run_install_script(arguments.get("script_path", f"{WORKSPACE_FOLDER}/{OUTPUT_DIR}/install.sh"))
            
        elif name == "formulate_error_search_prompt":
            return formulate_error_search_prompt(
                arguments.get("error_file", f"{WORKSPACE_FOLDER}/{OUTPUT_DIR}/installation_errors.log")
            )
            
        elif name == "copy_missing_files":
            return copy_missing_files(
                arguments.get("source_path", f"{EXPERIMENTAL_WORKSPACE}/somef/outputs"),
                arguments.get("target_path", f"{WORKSPACE_FOLDER}/outputs"),
                arguments.get("files_to_copy", ["requirements.txt", "requirements_dev.txt"])
            )
            
        else:
            console.print(f"[red]Unknown tool: {name}[/red]")
            return {
                "status": "error",
                "message": f"Unknown tool: {name}"
            }
    
    except Exception as e:
        console.print(f"[red]Error in tool execution: {str(e)}[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")
        return {
            "status": "error",
            "message": f"Error in tool execution: {str(e)}"
        }