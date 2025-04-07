import os
import json
import sys
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

def extract_github_repo(url: str, create_metadata: bool = True) -> Dict[str, Any]:
    """
    Clones a GitHub repository and lists all files in experimental_workspace.
    Optionally creates metadata files for execution agent.
    
    Args:
        url (str): GitHub repository URL
        create_metadata (bool): Whether to create metadata files
        
    Returns:
        Dict[str, Any]: Dictionary containing status and repository info
    """
    result = {
        "status": "success",
        "error": None,
        "files": [],
        "local_path": None,
        "metadata_path": None
    }
    
    try:
        # Clean URL and get repo info
        cleaned_url = url.rstrip("/")
        repo_name = cleaned_url.split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
            
        # Create experimental_workspace if it doesn't exist
        workspace_path = os.path.join(os.getcwd(), "experimental_workspace")
        os.makedirs(workspace_path, exist_ok=True)
        
        # Set repository path
        repo_path = os.path.join(workspace_path, repo_name)
        
        # Remove existing repository if it exists
        if os.path.exists(repo_path):
            console.print(f"[yellow]Removing existing repository: {repo_path}[/yellow]")
            subprocess.run(["rm", "-rf", repo_path], check=True)
        
        # Clone repository
        console.print(f"[blue]Cloning repository: {url}[/blue]")
        clone_process = subprocess.run(
            ["git", "clone", url, repo_path],
            capture_output=True,
            text=True
        )
        
        if clone_process.returncode != 0:
            raise Exception(f"Failed to clone repository: {clone_process.stderr}")
        
        # Collect files without creating tree structure
        file_list = []
        
        # Walk through repository
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in root:
                continue
            
            # Add files to list
            for file in files:
                file_path = os.path.relpath(os.path.join(root, file), repo_path)
                file_list.append(file_path)
        
        # Always auto-detect language
        language = detect_repository_language(repo_path, file_list)
        
        # Print repository info with project name and language
        console.print(Panel(
            f"Repository: {repo_name}\n"
            f"URL: {url}\n"
            f"Language: {language}\n"
            f"Files: {len(file_list)}",
            title="Repository Information"
        ))
        
        # Create metadata if requested
        if create_metadata:
            metadata_path = create_metadata_file(repo_name, url, language)
            result["metadata_path"] = metadata_path
            console.print(f"[green]Created metadata file: {metadata_path}[/green]")
        
        # Update result
        result["files"] = file_list
        result["local_path"] = repo_path
        result["language"] = language
        
        return result
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        console.print(f"[red]Error: {str(e)}[/red]")
        return result

def detect_repository_language(repo_path: str, file_list: List[str]) -> str:
    """
    Auto-detect the primary programming language of a repository.
    
    Args:
        repo_path (str): Path to the repository
        file_list (List[str]): List of files in the repository
        
    Returns:
        str: Detected language (default: "python")
    """
    # Count files by extension
    extensions = {}
    for file_path in file_list:
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if ext:
            extensions[ext] = extensions.get(ext, 0) + 1
    
    # Define extension to language mapping
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'cpp',
        '.rb': 'ruby',
        '.php': 'php',
        '.go': 'go',
        '.rs': 'rust',
        '.cs': 'csharp',
        '.sh': 'bash',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.r': 'r'
    }
    
    # Find the most common programming language extension
    top_extension = None
    top_count = 0
    
    for ext, count in extensions.items():
        if ext in extension_map and count > top_count:
            top_extension = ext
            top_count = count
    
    # Return the detected language or default to python
    return extension_map.get(top_extension, "python") if top_extension else "python"

def create_metadata_file(project_name: str, github_url: str, language: str) -> str:
    """
    Creates a metadata file for the execution agent.
    
    Args:
        project_name (str): The name of the project/repository
        github_url (str): The GitHub URL of the repository
        language (str): The programming language of the repository
        
    Returns:
        str: Path to the created metadata file
    """
    # Generate image name from project name
    image = f"{project_name}_image:ExecutionAgent"
    
    # Check for customize.json, create if not exists
    customize_path = "customize.json"
    if not os.path.exists(customize_path):
        customize = {"KEEP_CONTAINER": True}
        with open(customize_path, 'w') as f:
            json.dump(customize, f, indent=4)
        console.print(f"[yellow]Created default customize.json[/yellow]")
    else:
        try:
            with open(customize_path) as ctz:
                customize = json.load(ctz)
        except json.JSONDecodeError:
            customize = {"KEEP_CONTAINER": True}
            console.print(f"[yellow]Error reading customize.json, using defaults[/yellow]")
    
    # Define metadata
    metadata = {
        "repetition_handling": "RESTRICT",
        "project_path": project_name,
        "project_url": github_url,
        "budget_control": {
            "name": "NO-TRACK"
        },
        "language": language,
        "image": image,
        "keep_container": customize.get("KEEP_CONTAINER", True)
    }
    
    # Define metadata file paths
    
    # Root metadata file (kept for backward compatibility)
    root_metadata_file = "project_meta_data.json"
    with open(root_metadata_file, 'w') as f:
        json.dump(metadata, f, indent=4)
    
    # Create output directory in experimental_workspace/project_name
    output_dir = os.path.join("experimental_workspace", project_name, "outputs")
    os.makedirs(output_dir, exist_ok=True)
    
    # Write metadata to the output directory
    output_metadata_path = os.path.join(output_dir, "project_meta_data.json")
    with open(output_metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)
    
    # Also create a copy in the project root for compatibility
    workspace_metadata_path = os.path.join("experimental_workspace", project_name, "project_meta_data.json")
    with open(workspace_metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)
    
    console.print(f"[green]Metadata saved to outputs directory: {output_metadata_path}[/green]")
    
    return output_metadata_path

def clone_execution_workspace(github_url: str) -> str:
    """
    Clone repository to execution_agent_workspace.
    This replicates the standalone clone_repository function.
    
    Args:
        github_url (str): GitHub repository URL
        
    Returns:
        str: Path to the cloned repository
    """
    # Clean URL and get repo info
    cleaned_url = github_url.rstrip("/")
    project_name = cleaned_url.split("/")[-1]
    if project_name.endswith(".git"):
        project_name = project_name[:-4]
    
    cwd = os.getcwd()
    
    # Create execution_agent_workspace if it doesn't exist
    os.makedirs("execution_agent_workspace", exist_ok=True)
    
    # Clone the repository
    os.chdir("execution_agent_workspace/")
    subprocess.run(["git", "clone", github_url])
    
    # Define project directory
    project_directory = os.path.join(os.getcwd(), project_name)
    
    os.chdir(cwd)
    return project_directory

if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        repo_url = sys.argv[1]
    else:
        # Interactive mode
        repo_url = input("Enter GitHub repository URL: ")
    
    # Execute extraction with auto-detection of language
    result = extract_github_repo(repo_url, create_metadata=True)
    
    if result["status"] == "success":
        console.print(f"[green]Repository cloned successfully to: {result['local_path']}[/green]")
        if result["metadata_path"]:
            console.print(f"[green]Metadata file created: {result['metadata_path']}[/green]")
        
        # Show number of files
        console.print(f"[blue]Total files found: {len(result['files'])}[/blue]")