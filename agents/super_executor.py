import os
import sys
from pathlib import Path
from rich.console import Console
import json
import time
from typing import Dict, List, Any

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Use full package path for imports
from agents.Executor.agent import interact_with_llm, WORKSPACE_PATH, OUTPUT_PATH
from agents.Executor.models import LLMResponse, ToolCall
from agents.Executor.tools.tools import execute_tool_in_terminal

console = Console()

def get_installation_prompt() -> str:
    """Get the installation process prompt."""
    return """You are an AI installation assistant. Your task is to install a project by following these steps sequentially:

Follow these steps carefully, always THINK before you ACT:

1. Workspace:
   THINK: Verify if workspace exists and its structure
   ACT: Execute command to locate workspace
   {
     "tool_name": "ensure_workspace_exists",
     "arguments": {
       "base_path": "execution_agent_workspace"
     }
   }

2. Locate Script Installation:
   THINK: After workspace is verified, locate install.sh
   ACT: Search for installation script
   {
     "tool_name": "find_install_script",
     "arguments": {
       "path": "execution_agent_workspace"
     }
   }

3. Installation Execution:
   THINK: Once script is found, run the script and save errors
   ACT: Run the installation script with execute_tool_in_terminal
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

For each step:
1. Always wrap your analysis in <think>your reasoning here</think>
2. Wait for each command to complete before proceeding
3. Analyze the result and adjust if needed
4. Only move to next step when current step is successful

Remember:
- Directory structure is:
  execution_agent_workspace/
  └── outputs/
      └── install.sh
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

def execute_tool(tool: ToolCall) -> Dict[str, Any]:
    """Execute a tool call and return its result."""
    try:
        return execute_tool_in_terminal(
            name=tool.name,
            arguments=json.loads(tool.arguments)  # Parse JSON string directly
        )
    except Exception as e:
        return {
            "status": "error",
            "message": f"Tool execution failed: {str(e)}"
        }

def main():
    """Main function to run the installation process."""
    try:
        # Initialize conversation history
        messages = []
        
        # Get and display installation prompt
        prompt = get_installation_prompt()
        console.print("\n[cyan]Installation Plan:[/cyan]")
        console.print(prompt)
        
        # Track progress through all steps
        steps = ["workspace", "scripts", "installation", "errors"]
        current_step = 0
        
        while current_step < len(steps):
            # Get LLM response for current step
            result = interact_with_llm(prompt)
            
            if result.status == "error":
                console.print(f"[red]{result.content}[/red]")
                return 1
            
            # Display thinking process
            console.print(f"\n[yellow]Step {current_step + 1}: {steps[current_step]}[/yellow]")
            console.print(result.content)
            
            # Execute tool calls if any
            if result.tool_calls:
                for tool in result.tool_calls:
                    console.print(f"\n[yellow]→ Executing: {tool.name}[/yellow]")
                    
                    # Execute tool using the fixed execute_tool function
                    tool_result = execute_tool(tool)
                    
                    # Add results to conversation
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(tool_result),
                        "name": tool.name
                    })
                
                # Update prompt with results for next step
                prompt = f"""Previous step ({steps[current_step]}) completed.
                Tool results: {json.dumps(messages[-1], indent=2)}
                
                Continue with next step: {steps[min(current_step + 1, len(steps) - 1)]}
                
                {get_installation_prompt()}"""
                
            current_step += 1
            
        console.print("\n[green]✨ Installation process completed![/green]")
        save_results(result)
        return 0
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return 1

if __name__ == "__main__":
    sys.exit(main())