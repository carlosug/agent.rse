import os
import gradio as gr
from models.llm_extractor import LLMExtractor
from models.reasoning_model import ReasoningModel
from models.agent_based import TaskRunAgent

class GradioInterface:
    def __init__(self, llm_extractor, reasoning_model, agent_based_model):
        self.llm_extractor = llm_extractor
        self.reasoning_model = reasoning_model
        self.agent_based_model = agent_based_model

    def handle_user_input(self, readme_text, approach):
        if approach == "Rule-based":
            extracted_instructions = self.llm_extractor.extract_instructions(readme_text)
        elif approach == "Agent-based":
            actions = self.agent_based_model.generate_action_list(readme_text)
            extracted_instructions = self.agent_based_model.format_actions(actions)
        
        validated_instructions = self.reasoning_model.validate_instructions(extracted_instructions)
        
        # Generate the output file
        output_file_path = self.generate_output_file(validated_instructions)
        return output_file_path

    def generate_output_file(self, instructions):
        # Ensure instructions is a string
        instructions_str = "\n".join(instructions) if isinstance(instructions, list) else str(instructions)

        # Determine the type of output file to generate (e.g., executable, YAML, Dockerfile)
        output_type = "sh"  # This can be changed based on user preference or input

        if output_type == "yml":
            file_path = "install_instructions.yml"
            with open(file_path, 'w') as file:
                file.write(instructions_str)
        elif output_type == "sh":
            file_path = "install_instructions.sh"
            with open(file_path, 'w') as file:
                file.write("#!/bin/bash\n")
                file.write("# installer.sh - Automatically sets up the project environment\n\n")
                file.write("# Check if conda is available\n")
                file.write("if ! command -v conda &> /dev/null; then\n")
                file.write("    echo \"Error: Conda is not installed. Please install Miniconda first.\"\n")
                file.write("    exit 1\n")
                file.write("fi\n\n")
                file.write("# Clone the repository if it doesn't exist\n")
                file.write("if [ ! -d \"autoMate\" ]; then\n")
                file.write("    echo \"Cloning the autoMate repository...\"\n")
                file.write("    git clone https://github.com/yuruotong1/autoMate.git\n")
                file.write("fi\n\n")
                file.write("cd autoMate || { echo \"Failed to enter the autoMate directory\"; exit 1; }\n\n")
                file.write("# Create the Conda environment named \"automate\" with Python 3.12\n")
                file.write("echo \"Creating Conda environment 'automate' with Python 3.12...\"\n")
                file.write("conda create -n automate python=3.12 -y\n\n")
                file.write("# Activate the environment\n")
                file.write("echo \"Activating the environment...\"\n")
                file.write("source \"$(conda info --base)/etc/profile.d/conda.sh\"\n")
                file.write("conda activate automate\n\n")
                file.write("# Install project dependencies by running the install script\n")
                file.write("echo \"Running installation script...\"\n")
                file.write("python install.py\n\n")
                file.write("echo \"Installation complete. To re-activate the environment later, run: conda activate automate\"\n")
            os.chmod(file_path, 0o755)  # Make the script executable
        elif output_type == "dockerfile":
            file_path = "Dockerfile"
            with open(file_path, 'w') as file:
                file.write("FROM ubuntu:latest\n")
                file.write("RUN " + instructions_str.replace("\n", " && \\\nRUN "))
        
        return file_path

    def launch_interface(self):
        interface = gr.Interface(
            fn=self.handle_user_input,
            inputs=[gr.Textbox(lines=20, label="README Text"), gr.Radio(["Rule-based", "Agent-based"], label="Approach")],
            outputs="file",
            title="Installation Instructions Converter",
            description="Submit README text to convert installation instructions into executable files."
        )
        interface.launch(share=True)