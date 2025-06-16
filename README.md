# ETE Agent: Extract, Transform and Execute Install Instructions From README files automatically

<img src="/media/ete.png" width="500" alt="ETE Diagram">

## Idea
- Equip our ETE Assistant with tools to extract this information from the project directly.
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


## Installation

### Prerequisites
- Python 3.8+
- Git
- Access to Groq API (requires API key)

### Step 1: Clone the Repository
```bash
git clone https://github.com/[username]/agent.rse.git
cd agent.rse
```

### Step 2: Create and Activate Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# Or on Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
```bash
# Create config/.env file with your API keys
mkdir -p config
touch config/.env

# Add the following to config/.env:
GROQ_API_KEY=your_groq_api_key_here
# Add any other required API keys
```

### Step 5: Run the ETE Pipeline
Execute the agents in sequence:

```bash
# 1. Extract repository metadata
python agents/extract_agt.py --repo [target_repository_url]

# 2. Transform and analyze repository
python agents/interpret_agt.py
python agents/analyse_agt.py

# 3. Validate installation requirements
python agents/validation_agt.py

# 4. Generate installation files and execute
python agents/generate_agt.py
python agents/super_executor.py
```

### Step 6: View Results
The installation artifacts will be available in the `outputs` directory:
- `installation_analysis.json`: Analysis of repository installation requirements
- `installation_plan.json`: Structured installation plan
- `install.sh`: Generated installation script
- `Dockerfile`: Generated container definition
- `execution_log.json`: Log of the execution process

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
