# AutoINSTALL: Automatize Install Software

## Idea
- Equip our Assistant with tools to extract this information from the project directly.
- Instead of asking the user, an assistant can ask for a tool instead.

## Workflow

Interplay between the *Assistants* and the *Tool* agents.

### Assistants (Personas)
In this workflow, we are giving 4 different personas (and prompt templates) to the AI model:
- An **AI Planner**: Responsible for creating structured installation plans.
- An **AI Researcher**: Performs web searches and gathers relevant information.
- An **AI Writer**: Generates installation scripts and container files.
- An **AI Validator**: Validates the installation process and ensures correctness.

The workflow starts by cloning the given project and generating a list of all files (except the ones inside the `.git` folder).

### Tools
In addition to these new prompts, we will also supply the LLM with several tool definitions. There are 4 tool usages in this project:
- `analyse_project_tool`: Analyzes the project structure and dependencies.
- `write_files_tool`: Writes generated files like `install.sh` and `Dockerfile`.
- `search_tool`: Searches a given query on Google to gather relevant information.
- `execute_tool_in_terminal`: Executes installation steps in a controlled terminal environment.

### ETE Agent Version
This project implements the **ETE (Extract-Transform-Execute) Agent** version, which follows a modular pipeline:
1. **Extract**: The `extract_agt.py` agent clones the repository and gathers metadata.
2. **Transform**: The `interpret_agt.py` and `analyse_agt.py` agents analyze the repository and generate structured installation plans.
3. **Validate**: The `validation_agt.py` agent validates the installation requirements and generates container recommendations.
4. **Execute**: The `generate_agt.py` agent generates executable files (`install.sh` and `Dockerfile`), and the `super_executor.py` agent executes the installation process.

### Features
- No-cost API usage.
- Leverages Meta's Llama 3.3 70B model for intelligent decision-making.
- Fully automated installation process.
- Modular design for extensibility.
- Integration of web search capabilities for error handling and recommendations.

### Directory Structure


### Future Work
- Extend support for additional containerization tools (e.g., Singularity, Guix).
- Enhance security measures for generated scripts.
- Improve adaptability to heterogeneous environments.
