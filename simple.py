from tools.tools import get_bakery_prices, expert_coder, generate_dockerfile
from tools.tool_schema import tools
from models.groq_model import groq_model
from termcolor import colored
import re
import os
import shutil
import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from groq import Groq
from dotenv import dotenv_values

CONFIG = dotenv_values("config/.env")

client = Groq(api_key=CONFIG["GROQ_API_KEY"])
model = "llama-3.3-70b-versatile"  # Updated to a more capable model
console = Console()
conversation_history = []

def process_message(user_message: str) -> None:
    """
    Processes the user message and prints the response from the model.
    """
    global conversation_history

    conversation_history.append({"role": "user", "content": user_message})
    conversation_history = conversation_history[-4:]

    system_prompt = """You are a helpful AI assistant that can:
    1. Generate Python code snippets
    2. Look up bakery prices
    3. Create Dockerfile scripts

    To use these capabilities, use the appropriate function call:
    - For Python code: expert_coder
    - For bakery prices: get_bakery_prices
    - For Dockerfiles: generate_dockerfile

    When you want to use a tool, respond using this exact format:
    {"function": "tool_name", "arguments": {"param1": "value1", ...}}

    Always try to understand the user's intent and use the appropriate tool.
    If unsure, ask for clarification."""

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    messages.extend([msg for msg in conversation_history if msg['content'] is not None])
    
    try:
        # Make the API call
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=4096,
            temperature=0.7
        )

        assistant_message = response.choices[0].message
        
        # Debug logging
        console.print(f"[dim]Debug: Message received: {assistant_message}[/dim]")

        # Check for tool calls
        if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    console.print(f"[yellow]Using tool: {function_name}[/yellow]")

                    if function_name == "expert_coder":
                        prompt = function_args.get("prompt")
                        if prompt:
                            code = expert_coder(prompt)
                            if code and "error" not in code.lower():
                                console.print(Panel(
                                    Syntax(code, "python", theme="monokai", line_numbers=True),
                                    title="Generated Python Code"
                                ))
                            else:
                                console.print(Panel(code, title="Error", style="red"))
                        else:
                            console.print("[red]Error: No prompt provided for expert_coder[/red]")

                    elif function_name == "get_bakery_prices":
                        bakery_item = function_args.get("bakery_item")
                        if bakery_item:
                            price = get_bakery_prices(bakery_item)
                            console.print(Panel(f"Price for {bakery_item}: ${price}", title="Bakery Price"))
                        else:
                            console.print("[red]Error: No bakery item provided[/red]")

                    elif function_name == "generate_dockerfile":
                        prompt = function_args.get("prompt")
                        if prompt:
                            result = generate_dockerfile(prompt, model)
                            
                            if result.status == "success":
                                console.print(Panel(
                                    Syntax(result.content, "dockerfile", theme="monokai", line_numbers=True),
                                    title="Generated Dockerfile",
                                    expand=False
                                ))
                                console.print(f"[green]Dockerfile saved to: {result.filepath}[/green]")
                            else:
                                console.print(f"[red]Error: {result.error}[/red]")
                        else:
                            console.print("[red]Error: No prompt provided for generate_dockerfile[/red]")

                except json.JSONDecodeError:
                    console.print("[red]Error: Invalid function arguments format[/red]")
                except Exception as e:
                    console.print(f"[red]Error executing {function_name}: {str(e)}[/red]")

        # Handle regular responses
        elif assistant_message.content:
            console.print(Panel(assistant_message.content, title="Assistant Response"))
            conversation_history.append({"role": "assistant", "content": assistant_message.content})

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")


if __name__ == "__main__":
    console.print("[bold green]Welcome to the AI Assistant![/bold green]")
    console.print("[dim]Type 'exit' to quit[/dim]")
    
    while True:
        try:
            user_input = console.input("\n[bold blue]You:[/bold blue] ")
            if user_input.lower() in ['exit', 'quit', 'q']:
                console.print("[bold red]Goodbye![/bold red]")
                break
                
            console.print("[bold cyan]Assistant is thinking...[/bold cyan]")
            process_message(user_input)
            
        except KeyboardInterrupt:
            console.print("\n[bold red]Exiting...[/bold red]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {str(e)}[/red]")



