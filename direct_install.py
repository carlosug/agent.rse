#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from pathlib import Path
from rich.console import Console
import traceback

console = Console()

# Define paths
EXPERIMENTAL_WORKSPACE = Path("experimental_workspace") 
DGM_PATH = EXPERIMENTAL_WORKSPACE / "dgm"
EXPERIMENTAL_OUTPUT_PATH = DGM_PATH / "outputs"

WORKSPACE_PATH = Path("execution_agent_workspace")
OUTPUT_PATH = WORKSPACE_PATH / "outputs"

def setup_workspace():
    """Set up the workspace directory structure."""
    try:
        console.print("[blue]Setting up workspace...[/blue]")
        
        # Create directories
        WORKSPACE_PATH.mkdir(exist_ok=True)
        OUTPUT_PATH.mkdir(exist_ok=True)
        
        # Copy install.sh and Dockerfile from experimental workspace
        if (EXPERIMENTAL_OUTPUT_PATH / "install.sh").exists():
            shutil.copy2(EXPERIMENTAL_OUTPUT_PATH / "install.sh", OUTPUT_PATH / "install.sh")
            os.chmod(OUTPUT_PATH / "install.sh", 0o755)
            console.print("[green]✓ Copied install.sh[/green]")
        else:
            console.print("[red]✗ install.sh not found in experimental workspace[/red]")
            return False
            
        if (EXPERIMENTAL_OUTPUT_PATH / "Dockerfile").exists():
            shutil.copy2(EXPERIMENTAL_OUTPUT_PATH / "Dockerfile", OUTPUT_PATH / "Dockerfile")
            console.print("[green]✓ Copied Dockerfile[/green]")
            
        return True
    except Exception as e:
        console.print(f"[red]Error setting up workspace: {str(e)}[/red]")
        console.print(traceback.format_exc())
        return False

def run_install_script():
    """Run the installation script."""
    try:
        console.print("[blue]Running installation script...[/blue]")
        
        script_path = OUTPUT_PATH / "install.sh"
        if not script_path.exists():
            console.print(f"[red]✗ Script not found: {script_path}[/red]")
            return False
            
        # Show script content before running
        console.print("[cyan]Script content:[/cyan]")
        with open(script_path, 'r') as f:
            script_content = f.read()
            console.print(script_content)
        
        # Make sure script is executable
        os.chmod(script_path, 0o755)
        
        # Setup log files
        log_file = OUTPUT_PATH / "installation.log"
        error_file = OUTPUT_PATH / "installation_errors.log"
        
        # Run the script with output redirection
        console.print(f"[yellow]Running script: {script_path}[/yellow]")
        process = subprocess.run(
            f"cd {OUTPUT_PATH} && ./install.sh > {log_file} 2> {error_file}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        # Show tail of logs
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
                console.print("[green]Installation log (last 20 lines):[/green]")
                for line in lines[-20:]:
                    console.print(line.strip())
        
        if error_file.exists() and error_file.stat().st_size > 0:
            with open(error_file, 'r') as f:
                lines = f.readlines()
                console.print("[red]Installation errors:[/red]")
                for line in lines:
                    console.print(line.strip())
            
        if process.returncode == 0:
            console.print("[green]✓ Installation completed successfully[/green]")
            return True
        else:
            console.print(f"[red]✗ Installation failed with code {process.returncode}[/red]")
            console.print(process.stderr)
            return False
            
    except Exception as e:
        console.print(f"[red]Error running install script: {str(e)}[/red]")
        console.print(traceback.format_exc())
        return False

def main():
    """Main function to run the installation process."""
    console.print("\n[bold cyan]====== Direct Installation Script ======[/bold cyan]\n")
    
    # Step 1: Setup workspace
    if not setup_workspace():
        console.print("[red]Workspace setup failed[/red]")
        return 1
        
    # Step 2: Run installation script
    if not run_install_script():
        console.print("[red]Installation failed[/red]")
        return 1
        
    console.print("\n[green]Installation process completed![/green]")
    console.print("\n[blue]Next steps:[/blue]")
    console.print("[yellow]1. Navigate to the outputs directory:[/yellow]")
    console.print(f"   cd {OUTPUT_PATH}")
    console.print("[yellow]2. Build the Docker container:[/yellow]")
    console.print(f"   docker build -t project_container .")
    console.print("[yellow]3. Run the container:[/yellow]")
    console.print(f"   docker run project_container")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
