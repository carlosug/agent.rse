import os
import gradio as gr
from models.llm_extractor import LLMExtractor
from models.reasoning_model import ReasoningModel
from models.agent_based import TaskRunAgent
from ui.gradio_interface import GradioInterface

def main():
    # Initialize the LLM extractor with a model
    model_name = "gpt2"
    llm_extractor = LLMExtractor(model_name)

    # Initialize the reasoning model with an ontology
    ontology = "path/to/ontology"
    reasoning_model = ReasoningModel(ontology)

    # Retrieve the Anthropic API key from environment variables
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("The ANTHROPIC_API_KEY environment variable is not set.")
    
    # Initialize the agent-based model with Anthropic API key
    agent_based_model = TaskRunAgent(api_key)

    # Set up the Gradio interface
    interface = GradioInterface(llm_extractor, reasoning_model, agent_based_model)
    
    # Launch the user interface
    interface.launch_interface()

if __name__ == "__main__":
    main()