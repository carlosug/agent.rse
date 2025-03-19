# agent-based-prototype

This project is an agent-based prototype system designed to convert human-generated installation instructions from README files into executable files ready for installation on any computer. The system leverages large language models (LLMs) for extracting and interpreting instructions, employs a reasoning model based on ontology or similar frameworks, and provides a user-friendly interface using Gradio.

## Components

### 1. LLM Extractor
The `LLMExtractor` class, located in `src/models/llm_extractor.py`, utilizes one or multiple large language models to extract and interpret installation instructions from README files. Key methods include:
- `extract_instructions`: Extracts relevant installation instructions from the provided README content.
- `interpret_instructions`: Interprets the extracted instructions to generate a structured format suitable for further processing.

### 2. Reasoning Model
The `ReasoningModel` class, found in `src/models/reasoning_model.py`, implements an ontology-based reasoning framework or utilizes frameworks like SmolAgents or LlamaIndex. Important methods include:
- `reason_about_instructions`: Analyzes the extracted instructions to ensure logical coherence and completeness.
- `validate_instructions`: Validates the instructions against known installation patterns and best practices.

### 3. User Interface
The user interface is built using Gradio and is defined in `src/ui/gradio_interface.py`. The `GradioInterface` class includes:
- `launch_interface`: Launches the Gradio interface for user interaction.
- `handle_user_input`: Processes user-submitted README files and triggers the extraction and reasoning processes.

### 4. Utility Functions
Utility functions for handling file operations are implemented in `src/utils/file_handler.py`. Key functions include:
- `read_readme`: Reads the content of a README file.
- `save_executable`: Saves the generated executable installation scripts to the specified location.

## Usage Instructions
1. Install the required dependencies listed in `requirements.txt`.
2. Run the main application using `src/main.py`.
3. Use the Gradio interface to upload README files and receive executable installation scripts.

## Future Work
This project aims to enhance the capabilities of the agent-based system by integrating more advanced reasoning models and improving the user interface for better usability. Contributions and feedback are welcome as we strive to create a robust tool for researchers and developers alike.