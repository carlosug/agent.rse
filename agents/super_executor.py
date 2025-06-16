import os
import sys
import json
import time
import logging
import threading
import traceback
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Rich imports
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

# Project imports
sys.path.append(str(Path(__file__).parent.parent))
from agents.Executor.agent import interact_with_llm, WORKSPACE_PATH, OUTPUT_PATH
from agents.Executor.models import LLMResponse, ToolCall
from agents.Executor.tools.tools import execute_tool_in_terminal

console = Console()

def get_installation_prompt() -> str:
    """Get the installation process prompt."""
    return """You are an AI installation assistant. Your task is to install a project by following these steps sequentially:

Follow these steps carefully, always THINK before you ACT:

1. Workspace:
   THINK: Verify if workspace exists and copy files from experimental_workspace
   ACT: Execute command to locate workspace and copy necessary files
   {
     "tool_name": "ensure_workspace_exists",
     "arguments": {
       "base_path": "execution_agent_workspace"
     }
   }

2. Locate Script Installation:
   THINK: After workspace is verified and files copied, locate install.sh
   ACT: Search for installation script
   {
     "tool_name": "find_install_script",
     "arguments": {
       "path": "execution_agent_workspace"
     }
   }

3. Installation Execution:
   THINK: Once script is found, run the script and save errors
   ACT: Run the installation script
   {
     "tool_name": "run_install_script",
     "arguments": {
       "script_path": "execution_agent_workspace/outputs/install.sh"
     }
   }

4. Error Prompting:
   THINK: If installation fails, analyze errors and create a search prompt for troubleshooting search
   ACT: Process error logs
   {
     "tool_name": "formulate_error_search_prompt",
     "arguments": {
       "error_file": "execution_agent_workspace/outputs/installation_errors.log"
     }
   }

5. Missing Files Fix:
   THINK: Check error logs for missing files, especially requirements.txt
   ACT: Copy missing files from experimental workspace
   {
     "tool_name": "copy_missing_files",
     "arguments": {
       "source_path": "experimental_workspace/dgm/outputs",
       "target_path": "execution_agent_workspace/outputs",
       "files_to_copy": ["requirements.txt", "requirements_dev.txt"]
     }
   }

6. Retry Installation:
   THINK: After fixing missing files, retry the installation
   ACT: Run the installation script again
   {
     "tool_name": "run_install_script",
     "arguments": {
       "script_path": "execution_agent_workspace/outputs/install.sh"
     }
   }

7. Final Error Analysis:
   THINK: If installation still fails, provide a comprehensive error analysis
   ACT: Reformulate error prompt with more detailed context
   {
     "tool_name": "formulate_error_search_prompt",
     "arguments": {
       "error_file": "execution_agent_workspace/outputs/installation_errors.log"
     }
   }

For each step:
1. Always wrap your analysis in <think>your reasoning here</think>
2. Wait for each command to complete before proceeding
3. Analyze the result and adjust if needed
4. Only move to next step when current step is successful

Remember:
- Directory structure will be created as follows:
  execution_agent_workspace/
  └── outputs/
      └── install.sh  (copied from experimental_workspace)
      
- Step 1 creates the directory and copies the needed files
- Step 5 is used if installation fails due to missing files like requirements.txt
- Step 7 is used if installation still fails after fixing missing files
- Each step must complete successfully before moving to next
- Always show your thinking process
- Use exact paths as shown above"""

def format_conversation_output(messages: List[Dict]) -> None:
    """Format and display the conversation in organized sections with typing effect."""
    for message in messages:
        if message["role"] == "assistant":
            content = message["content"]
            if "<think>" in content:
                # Split thinking and action parts
                think_part = content.split("<think>")[1].split("</think>")[0].strip()
                action_part = content.split("</think>")[1].strip()
                
                # Display thinking process
                console.print("\n[cyan]🤔 Thinking Process:[/cyan]")
                console.print(think_part, style="cyan")
                
                # Display action plan with proper formatting
                console.print("\n[green]🔧 Action Plan:[/green]")
                for line in action_part.split('\n'):
                    if line.strip():
                        # Format based on line content
                        style = "yellow" if line.startswith(('$', '>')) else "blue" if line.startswith('#') else "white"
                        console.print(line, style=style)
            else:
                console.print("\n[yellow]Response:[/yellow]")
                console.print(content)
                
        elif message["role"] == "tool":
            # Display tool execution results
            tool_id = message.get("tool_call_id", "unknown")
            console.print(f"\n[blue]🛠 Tool Execution ({tool_id}):[/blue]")
            try:
                result = json.loads(message["content"])
                style = "green" if isinstance(result, dict) and result.get("status") == "success" else "red"
                console.print(json.dumps(result, indent=2), style=style)
            except json.JSONDecodeError:
                console.print(message["content"])

def save_results(result: LLMResponse) -> None:
    """Save execution results to a file."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    results_file = OUTPUT_PATH / f"installation_results_{timestamp}.json"
    
    # Convert result to dict and handle Path objects
    def convert_paths(obj):
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: convert_paths(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_paths(i) for i in obj]
        return obj

    # Convert to dict and save
    result_dict = convert_paths(result.model_dump())
    
    with open(results_file, "w") as f:
        json.dump(result_dict, f, indent=2)
    
    console.print(f"[green]Results saved to: {results_file}[/green]")

def execute_tool(tool: ToolCall, timeout: int = 300) -> Dict[str, Any]:
    """Execute a tool call with timeout and return its result."""
    try:
        def timeout_handler(func, args=(), kwargs=None, timeout_duration=300):
            """Handle function timeout."""
            if kwargs is None:
                kwargs = {}
                
            result_container = {"result": None, "exception": None}
            
            def worker():
                try:
                    result_container["result"] = func(*args, **kwargs)
                except Exception as e:
                    result_container["exception"] = e
                    
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join(timeout_duration)
            
            if thread.is_alive():
                raise TimeoutError(f"Tool execution timed out after {timeout_duration} seconds")
                
            if result_container["exception"]:
                raise result_container["exception"]
                
            return result_container["result"]
        
        # Parse arguments from string to dict if needed
        tool_arguments = tool.arguments
        if isinstance(tool_arguments, str):
            try:
                # Check if it's actually JSON
                if tool_arguments.strip().startswith('{'):
                    tool_arguments = json.loads(tool_arguments)
                else:
                    # If it's not JSON, create a simple key:value dict
                    tool_arguments = {"value": tool_arguments.strip()}
            except json.JSONDecodeError as e:
                console.print(f"[yellow]Warning: JSON parsing error: {e}[/yellow]")
                console.print(f"[yellow]Raw arguments: '{tool_arguments}'[/yellow]")
                # Create a simple dict to avoid the error
                tool_arguments = {"raw_input": tool_arguments}
        
        # Handle nested execute_tool_in_terminal format
        if tool.name == "execute_tool_in_terminal" and isinstance(tool_arguments, dict):
            if "name" in tool_arguments and "arguments" in tool_arguments:
                # This is a nested tool call - extract the actual tool name
                actual_tool_name = tool_arguments["name"]
                actual_tool_args = tool_arguments["arguments"]
                console.print(f"[yellow]Unwrapping nested tool call: {actual_tool_name}[/yellow]")
                
                # Call execute_tool_in_terminal with the unwrapped arguments
                result = timeout_handler(
                    execute_tool_in_terminal,
                    args=(actual_tool_name, actual_tool_args),
                    timeout_duration=timeout
                )
                return result
        
        # Print debug information
        console.print(f"[dim]Debug: Executing tool {tool.name} with arguments: {tool_arguments}[/dim]")
        
        # Direct tool call for non-nested format
        result = timeout_handler(
            execute_tool_in_terminal,
            args=(tool.name, tool_arguments),
            timeout_duration=timeout
        )
        
        return result
        
    except TimeoutError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        console.print(f"[red]Exception details: {traceback.format_exc()}[/red]")
        return {
            "status": "error",
            "message": f"Tool execution failed: {str(e)}"
        }

def get_progress_bar(current: int, total: int, width: int = 40) -> str:
    """Create a text-based progress bar."""
    filled = int(width * current / total)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    percent = int(100 * current / total)
    return f"{bar} {percent}%"

def display_progress(step: int, total: int, step_name: str) -> None:
    """Display current progress in the installation process."""
    console.print("\n")
    console.print(f"Installation Progress: {get_progress_bar(step, total)}")
    console.print(f"[bold blue]Step {step}/{total}: {step_name.upper()}[/bold blue]")
    console.print("\n")

def setup_logging() -> None:
    """Set up logging for the installation process."""
    # Create logs directory if it doesn't exist
    logs_dir = OUTPUT_PATH / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Set up file handler
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = logs_dir / f"installation_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logging.info(f"Installation session started. Log file: {log_file}")
    return log_file

def display_installation_header() -> None:
    """Display an attractive header for the installation process."""
    console.print("\n")
    console.print("[bold cyan]╔════════════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║                 INSTALLATION ASSISTANT                 ║[/bold cyan]")
    console.print("[bold cyan]╚════════════════════════════════════════════════════════╝[/bold cyan]")
    console.print("\n[yellow]This assistant will guide you through the installation process.[/yellow]")
    console.print("[yellow]Each step will be explained before execution.[/yellow]")
    console.print("\n")

def confirm_action(message: str) -> bool:
    """Ask for user confirmation before proceeding."""
    response = input(f"{message} (y/n): ").strip().lower()
    return response == "y" or response == "yes"

def main():
    """Main function to run the installation process."""
    try:
        # Display header
        display_installation_header()
        
        # Setup logging
        log_file = setup_logging()
        
        # Initialize conversation history
        messages = []
        
        # Get and display installation prompt
        prompt = get_installation_prompt()
        console.print("\n[cyan]Installation Plan:[/cyan]")
        console.print(prompt)
        
        # Track progress through all steps with retry capabilities
        steps = ["workspace", "scripts", "installation", "errors", "fix_files", "retry_installation", "final_analysis"]
        current_step = 0
        max_retries = 2
        
        while current_step < len(steps):
            retry_count = 0
            step_succeeded = False
            
            # Allow retries for failed steps
            while not step_succeeded and retry_count <= max_retries:
                if retry_count > 0:
                    console.print(f"\n[yellow]Retrying step {current_step + 1}: {steps[current_step]} (Attempt {retry_count}/{max_retries})[/yellow]")
                
                # Get LLM response for current step
                result = interact_with_llm(prompt)
                
                if result.status == "error":
                    console.print(f"[red]Error: {result.content}[/red]")
                    retry_count += 1
                    continue
                
                # Display thinking process
                console.print(f"\n[bold blue]Step {current_step + 1}: {steps[current_step]}[/bold blue]")
                console.print(result.content)
                
                # Execute tool calls if any
                if result.tool_calls:
                    all_tools_succeeded = True
                    for tool in result.tool_calls:
                        console.print(f"\n[yellow]→ Executing: {tool.name}[/yellow]")
                        
                        # Execute tool using the fixed execute_tool function
                        tool_result = execute_tool(tool)
                        
                        # Check if tool execution succeeded
                        if tool_result.get("status") != "success":
                            all_tools_succeeded = False
                            console.print(f"[red]✗ Tool failed: {tool_result.get('message', 'Unknown error')}[/red]")
                        else:
                            console.print(f"[green]✓ Tool succeeded[/green]")
                        
                        # Add results to conversation
                        messages.append({
                            "role": "tool",
                            "content": json.dumps(tool_result),
                            "name": tool.name
                        })
                    
                    step_succeeded = all_tools_succeeded
                    if not step_succeeded:
                        retry_count += 1
                    else:
                        # Update prompt with results for next step
                        prompt = f"""Previous step ({steps[current_step]}) completed successfully.
                        Tool results: {json.dumps(messages[-1], indent=2)}
                        
                        Continue with next step: {steps[min(current_step + 1, len(steps) - 1)]}
                        
                        {get_installation_prompt()}"""
                else:
                    step_succeeded = True
            
            # Check if step eventually succeeded
            if not step_succeeded:
                console.print(f"[red]Failed to complete step {current_step + 1}: {steps[current_step]} after {max_retries} retries[/red]")
                save_results(result)
                return 1
                
            current_step += 1
            display_progress(current_step, len(steps), steps[current_step - 1])  # Update progress display
            
        console.print("\n[green]✨ Installation process completed![/green]")
        save_results(result)
        return 0
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1

if __name__ == "__main__":
    sys.exit(main())