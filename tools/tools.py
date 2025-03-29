from termcolor import colored
from dotenv import dotenv_values
from groq import Groq
import os
from tools.tool_models import DockerfileRequest, DockerfileContent, DockerfileResponse



def get_bakery_prices(bakery_item: str):
    if bakery_item == "croissant":
        return 4.25
    elif bakery_item == "brownie":
        return 2.50
    elif bakery_item == "cappuccino":
        return 4.75
    else:
        return "We're currently sold out!"


def expert_coder(prompt: str) -> str:
    """
    Generates an expert-level Python code snippet based on the given prompt using the Groq LLM model.
    """
    # Load the Groq API key from the environment configuration
    CONFIG = dotenv_values("config/.env")
    api_key = CONFIG.get("GROQ_API_KEY")

    if not api_key:
        print(colored("Error: GROQ_API_KEY is not set in the environment configuration.", "red"))
        return "An error occurred: Missing API key."

    # Initialize the Groq client
    client = Groq(api_key=api_key)

    # Debug: Print the prompt and model
    print(colored(f"Debug: Prompt -> {prompt}", "yellow"))

    # Define the system message to guide the model
    system_message = {
        "role": "system",
        "content": "You are an expert Python programmer. Generate high-quality, expert-level Python code based on the user's prompt."
    }

    # Define the user message with the provided prompt
    user_message = {
        "role": "user",
        "content": prompt
    }

    # Combine messages
    messages = [system_message, user_message]

    # Call the Groq LLM model
    try:
        response = client.chat.completions.create(
            model="gemma2-9b-it",
            messages=messages,
            max_tokens=1024,  # Adjust token limit as needed
            temperature=0.7,  # Adjust creativity level
        )

        # Debug: Print the raw response
        print(colored(f"Debug: Response -> {response}", "yellow"))

        # Extract the generated code from the response
        generated_code = response.choices[0].message.content
        return generated_code

    except Exception as e:
        print(colored(f"Error generating code: {e}", "red"))
        return "An error occurred while generating the code."
    


def generate_dockerfile(prompt: str, model: str = "gemma2-9b-it") -> DockerfileResponse:
    """
    Generates a Dockerfile based on the given prompt using the Groq API.
    
    Args:
        prompt (str): The prompt describing the desired Dockerfile content.
        model (str): The name of the Groq LLM model to use.
    
    Returns:
        DockerfileResponse: The response containing the Dockerfile content and metadata.
    """
    try:
        # Validate input
        request = DockerfileRequest(prompt=prompt, model=model)
        
        # Load the Groq API key from the environment configuration
        CONFIG = dotenv_values("config/.env")
        api_key = CONFIG.get("GROQ_API_KEY")

        if not api_key:
            print(colored("Error: GROQ_API_KEY is not set in the environment configuration.", "red"))
            return DockerfileResponse(
                content="",
                filepath="",
                status="error",
                error="Missing API key"
            )

        # Initialize the Groq client
        client = Groq(api_key=api_key)

        # Define the system message to guide the model
        system_message = {
            "role": "system",
            "content": "You are an expert in creating Dockerfiles. Generate a high-quality Dockerfile based on the user's prompt."
        }

        # Define the user message with the provided prompt
        user_message = {
            "role": "user",
            "content": request.prompt
        }

        # Combine messages
        messages = [system_message, user_message]

        response = client.chat.completions.create(
            model=request.model,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )
        
        # Parse and extract Dockerfile content
        content = DockerfileContent(raw_content=response.choices[0].message.content)
        dockerfile_code = content.dockerfile_code

        # Create output directory and save file
        output_dir = os.path.join(os.getcwd(), "experimental_workplace")
        os.makedirs(output_dir, exist_ok=True)
        dockerfile_path = os.path.join(output_dir, "Dockerfile")
        
        with open(dockerfile_path, "w") as dockerfile:
            dockerfile.write(dockerfile_code)

        return DockerfileResponse(
            content=dockerfile_code,
            filepath=dockerfile_path,
            status="success"
        )

    except Exception as e:
        return DockerfileResponse(
            content="",
            filepath="",
            status="error",
            error=str(e)
        )