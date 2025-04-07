import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.syntax import Syntax
import json
import os
import sys
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

WORKSPACE_FOLDER = "execution_agent_workspace"
OUTPUT_DIR = "outputs"  # This matches the actual directory name


def ensure_workspace_exists(base_path: str) -> Dict[str, str]:
    """Verify workspace directory structure exists without creating it."""
    try:
        # Use WORKSPACE_FOLDER as base and append the relative path
        root_workspace = Path(WORKSPACE_FOLDER).resolve()  # Get absolute path
        workspace_path = root_workspace / Path(base_path).relative_to(WORKSPACE_FOLDER)
        output_path = workspace_path / OUTPUT_DIR
        
        # Only verify directories exist
        if not workspace_path.exists():
            return {
                "status": "error",
                "message": f"Workspace directory not found: {workspace_path}"
            }
            
        if not output_path.exists():
            return {
                "status": "error",
                "message": f"Outputs directory not found: {output_path}"
            }
            
        # All directories exist
        return {
            "status": "success",
            "workspace_path": str(workspace_path),
            "output_path": str(output_path),
            "message": "Workspace structure verified successfully"
        }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error verifying workspace: {str(e)}"
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
        script_path = Path(script_path)
        if not script_path.is_file():
            return {
                "status": "error",
                "message": f"Script not found: {script_path}"
            }
        
        # Setup log files
        log_file = script_path.parent / "installation.log"
        error_file = script_path.parent / "installation_errors.log"
        
        # Make executable and run
        os.chmod(script_path, 0o755)
        process = subprocess.run(
            f"cd {script_path.parent} && ./install.sh",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Save outputs
        log_file.write_text(process.stdout)
        error_file.write_text(process.stderr)
        
        return {
            "status": "success" if process.returncode == 0 else "error",
            "returncode": process.returncode,
            "output_log": str(log_file),
            "error_log": str(error_file),
            "message": "Installation completed" if process.returncode == 0 else f"Failed with code {process.returncode}"
        }
            
    except Exception as e:
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
            model="qwen-2.5-32b",
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

def execute_tool_in_terminal(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute terminal commands for each step, using LLM to generate secure commands."""
    try:
        console.print(f"\n[cyan]🔧 Executing: {name}[/cyan]")
        
        # Ask LLM for secure commands
        client = init_groq_client()
        prompt = f"""Generate secure shell commands for the tool '{name}' with these arguments:
        {json.dumps(arguments, indent=2)}
        
        Requirements:
        1. Include safety checks (file existence, permissions)
        2. Use absolute paths when possible
        3. Add error handling
        4. Validate inputs
        5. Save outputs to logs
        
        Return only the commands as a JSON array, e.g.:
        ["command1", "command2"]
        """
        
        response = client.chat.completions.create(
            model="qwen-2.5-32b",
            messages=[
                {"role": "system", "content": "You are a secure shell command generator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        try:
            commands = json.loads(response.choices[0].message.content)
            if not isinstance(commands, list):
                raise ValueError("Commands must be a list")
        except (json.JSONDecodeError, ValueError) as e:
            return {
                "status": "error",
                "message": f"Invalid commands from LLM: {str(e)}"
            }
        
        # Execute generated commands
        results = []
        for cmd in commands:
            console.print(f"\n[yellow]$ {cmd}[/yellow]")
            
            # Basic security checks
            if any(unsafe in cmd.lower() for unsafe in ['rm -rf', 'wget', 'curl', '>', '|', '&', ';']):
                console.print(f"[red]⚠️ Unsafe command detected: {cmd}[/red]")
                continue
                
            process = subprocess.run(
                cmd,
                shell=True,
                text=True,
                capture_output=True,
                cwd=str(Path(WORKSPACE_FOLDER).resolve())  # Use absolute path
            )
            
            if process.stdout: console.print(process.stdout)
            if process.stderr: console.print(f"[red]{process.stderr}[/red]")
            
            results.append({
                "command": cmd,
                "output": process.stdout,
                "error": process.stderr,
                "status": process.returncode,
                "cwd": str(Path(WORKSPACE_FOLDER).resolve())
            })
        
        return {
            "status": "success",
            "results": results,
            "generated_commands": commands
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error in command execution: {str(e)}"
        }