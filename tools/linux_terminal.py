import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
from rich.console import Console
from rich.panel import Panel

console = Console()

class LinuxTerminal:
    """Simplified Linux terminal for installation analysis."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.current_dir = self.workspace_path
        
    def execute(self, command: str) -> Dict[str, str]:
        """Execute a Linux terminal command."""
        try:
            console.print(f"[blue]Executing:[/blue] {command}")
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.current_dir
            )
            
            return {
                "status": "success" if process.returncode == 0 else "error",
                "output": process.stdout.strip(),
                "error": process.stderr.strip()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "output": "",
                "error": str(e)
            }
    
    def analyze_dependencies(self) -> List[str]:
        """Find dependency files in the project."""
        dependency_files = []
        patterns = ['requirements.txt', 'setup.py', 'package.json', 'Gemfile']
        
        for pattern in patterns:
            result = self.execute(f"find . -name {pattern}")
            if result["status"] == "success" and result["output"]:
                dependency_files.extend(result["output"].split('\n'))
                
        return dependency_files
    
    def read_file(self, filepath: str) -> str:
        """Read contents of a file."""
        try:
            with open(self.current_dir / filepath) as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def list_installation_files(self) -> List[str]:
        """Find installation-related files."""
        result = self.execute("find . -type f -name 'install*' -o -name 'setup*' -o -name 'README*'")
        if result["status"] == "success":
            return result["output"].split('\n')
        return []
    
    def check_environment(self) -> Dict[str, str]:
        """Check system environment."""
        env_info = {}
        
        # Check Python
        python_version = self.execute("python3 --version")
        env_info["python"] = python_version["output"]
        
        # Check package managers
        for cmd in ["pip --version", "npm --version", "gem --version"]:
            result = self.execute(cmd)
            if result["status"] == "success":
                env_info[cmd.split()[0]] = result["output"]
                
        return env_info

def get_terminal(workspace_path: Optional[str] = None) -> LinuxTerminal:
    """Get a Linux terminal instance."""
    if workspace_path is None:
        workspace_path = os.path.join(
            Path(__file__).parent.parent,
            "experimental_workspace"
        )
    return LinuxTerminal(workspace_path)

# Example usage
if __name__ == "__main__":
    terminal = get_terminal()
    
    # Example analysis
    console.print("\n[yellow]Analyzing project structure...[/yellow]")
    console.print(Panel(
        "\n".join(terminal.list_installation_files()),
        title="Installation Files Found"
    ))
    
    console.print("\n[yellow]Checking dependencies...[/yellow]")
    console.print(Panel(
        "\n".join(terminal.analyze_dependencies()),
        title="Dependency Files"
    ))
    
    console.print("\n[yellow]Checking environment...[/yellow]")
    console.print(Panel(
        "\n".join(f"{k}: {v}" for k, v in terminal.check_environment().items()),
        title="Environment Info"
    ))
    console.print("\n[yellow]Reading README file...[/yellow]")
    readme_content = terminal.read_file("README.md")
    console.print(Panel(
        readme_content,
        title="README Content"
    ))
    console.print("\n[yellow]Project analysis complete![/yellow]")
#         if "suggested_output" in known_info:
#             suggested_output = known_info["suggested_output"]
#         else:
#             suggested_output = "README"
#         if suggested_output == "README":
#             print(colored("\nStarting AI Writer...", "green"))
#             answer_writer = writer(model=model, known_info=known_info,
#                                    system_prompt_writer=system_prompt_writer)
#             print(colored("Writer finished!", "green"))
#             skip_writer = False
#         else:
#             print(colored("\nStarting AI Validator...", "green"))
#             answer_validator = validator(model=model, known_info=known_info,
#                                          system_prompt_validator=system_prompt_validator)
#             print(colored("Validator finished!", "green"))
#             skip_writer = True
#             skip_validator = False
