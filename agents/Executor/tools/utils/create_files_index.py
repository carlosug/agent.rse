from pathlib import Path
from typing import Dict, Any
from rich.console import Console

console = Console()

def create_files_index(workspace_path: Path) -> Dict[str, Any]:
    """
    Create an index of files in the workspace.
    
    Args:
        workspace_path (Path): Path to the workspace directory
        
    Returns:
        Dict[str, Any]: Index of files and their metadata
    """
    try:
        index = {
            "files": [],
            "directories": [],
            "metadata": {}
        }
        
        for item in workspace_path.rglob("*"):
            if item.name.startswith('.'):  # Skip hidden files
                continue
                
            rel_path = str(item.relative_to(workspace_path))
            
            if item.is_file():
                index["files"].append(rel_path)
                index["metadata"][rel_path] = {
                    "size": item.stat().st_size,
                    "modified": item.stat().st_mtime,
                    "extension": item.suffix
                }
            elif item.is_dir():
                index["directories"].append(rel_path)
        
        return {
            "status": "success",
            "index": index
        }
        
    except Exception as e:
        error_msg = f"Error creating file index: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        return {
            "status": "error",
            "error": error_msg
        }