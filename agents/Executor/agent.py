import os
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from rich.console import Console
from groq import Groq
from dotenv import dotenv_values
import instructor
from .models import LLMResponse

console = Console()

# Import tools
from agents.Executor.tools.tools import (
    ensure_workspace_exists,
    find_install_script,
    run_install_script,
    formulate_error_search_prompt,
    execute_tool_in_terminal
)
from agents.Executor.tools.tool_schema import tools


MODEL = "qwen-2.5-32b"

WORKSPACE_PATH = Path(__file__).parent.parent.parent / "execution_agent_workspace"
# REPO_PATH = WORKSPACE_PATH / "Repo2Run"
OUTPUT_PATH = WORKSPACE_PATH / "outputs"  # This is where install.sh should be found

# Create necessary directories with proper structure
WORKSPACE_PATH.mkdir(exist_ok=True)
# REPO_PATH.mkdir(exist_ok=True)
OUTPUT_PATH.mkdir(exist_ok=True)

# Define system prompt explicitly
SYSTEM_PROMPT = """You are an installation assistant. Follow these exact steps:

STEP 1. Find Install Script: Install.sh
{
    "name": "execute_tool_in_terminal",
    "arguments": {
        "name": "find_install_script",
        "arguments": {
            "path": "execution_agent_workspace/outputs"
        }
    }
}

STEP 2. Run Installation: Install.sh
{
    "name": "execute_tool_in_terminal",
    "arguments": {
        "name": "run_install_script",
        "arguments": {
            "script_path": "execution_agent_workspace/outputs/install.sh"
        }
    }
}

STEP 3. If Error Occurs:
{
    "name": "execute_tool_in_terminal",
    "arguments": {
        "name": "formulate_error_search_prompt",
        "arguments": {
            "error_file": "execution_agent_workspace/outputs/installation_errors.log"
        }
    }
}

IMPORTANT:
1. The install.sh script already exists, just find, locate and run it
2. Save all outputs to log files
3. Create search query if errors occur
"""

available_tools = {
    "ensure_workspace_exists": ensure_workspace_exists,
    "find_install_script": find_install_script,
    "run_install_script": run_install_script,
    "formulate_error_search_prompt": formulate_error_search_prompt,
    "execute_tool_in_terminal": execute_tool_in_terminal
}

def init_groq_client() -> Groq:
    """Initialize Groq client with instructor patch."""
    config = dotenv_values("config/.env")
    api_key = config.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in config/.env or environment")
        
    client = Groq(api_key=api_key.strip())
    return instructor.patch(client, mode=instructor.Mode.JSON)

def format_assistant_response(content: str) -> None:
    """Format assistant's response in a clean, professional way."""
    # Clean up unwanted tokens and HTML
    content = content.replace("<|assistant", "")
    content = content.replace("<|end_header_id|>", "")
    content = content.replace("<i>", "")
    content = content.replace("</i>", "")
    
    if "<think>" in content:
        # Extract thinking and action parts
        think_part = content.split("<think>")[1].split("</think>")[0].strip()
        action_part = content.split("</think>")[1].strip() if "</think>" in content else ""
        
        # Display thinking process cleanly
        console.print("\n[bold blue]Thinking[/bold blue]")
        console.print("─" * 40)
        console.print(think_part.strip())
        
        if action_part:
            console.print("\n[bold yellow]Action[/bold yellow]")
            console.print("─" * 40)
            console.print(action_part.strip())
    else:
        console.print("\n[bold green]Response[/bold green]")
        console.print("─" * 40)
        console.print(content.strip())

def interact_with_llm(user_prompt: str) -> LLMResponse:
    """Interact with the GROQ API LLM model."""
    try:
        client = init_groq_client()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        # Clean section header
        console.print("\n[bold]Starting Installation Process[/bold]")
        console.print("─" * 40)

        # Make initial request
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=4096
        )

        assistant_message = response.choices[0].message
        tool_usage = []
        
        # Process tool calls with minimal formatting
        if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                try:
                    # Clean tool execution display
                    function_args = json.loads(tool_call.function.arguments)
                    console.print(f"\n[bold]Executing: {function_name}[/bold]")
                    console.print(json.dumps(function_args, indent=2))
                    
                    # Execute function
                    function_to_call = available_tools.get(function_name)
                    if not function_to_call:
                        raise ValueError(f"Unknown tool: {function_name}")
                    
                    # Execute and show results
                    function_response = function_to_call(**function_args)
                    
                    # Format response cleanly
                    if isinstance(function_response, dict):
                        if function_response.get("status") == "success":
                            console.print("\n[green]✓ Success[/green]")
                        else:
                            console.print("\n[red]✗ Error[/red]")
                        console.print(json.dumps(function_response, indent=2))
                    
                    # Track usage and update conversation
                    tool_usage.append({
                        "name": function_name,
                        "arguments": function_args,
                        "result": function_response,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(function_response),
                        "tool_call_id": tool_call.id,
                        "name": function_name
                    })
                    
                except Exception as e:
                    console.print(f"\n[red]Error: {str(e)}[/red]")
                    messages.append({
                        "role": "tool",
                        "content": json.dumps({"error": str(e)}),
                        "tool_call_id": tool_call.id,
                        "name": function_name
                    })

            # Get and format final response
            final_response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=4096
            )
            
            # Format assistant's final response
            format_assistant_response(final_response.choices[0].message.content)
            
            return LLMResponse(
                status="success",
                content=final_response.choices[0].message.content,
                tool_calls=tool_usage
            )
        
        return LLMResponse(
            status="success",
            content=assistant_message.content,
            tool_calls=[]
        )

    except Exception as e:
        console.print("\n[bold red]❌ LLM Interaction Error:[/]")
        console.print(f"[red]{str(e)}[/]")
        return LLMResponse(
            status="error",
            content=str(e),
            tool_calls=[]
        )

