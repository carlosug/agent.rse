# agent.rse

The agent attempts to autonomously install a given open source research software repository. Agent.rse performs its tasks in two stages: i) it gathers text related to the installation from README and ii) it tries to build, generate ,and if necessary, repair, a instruction to install and test the target repository. We will explore how different LLMs can cooperate to enhance Agent.rese ability to transform a unstructured README into clear, concise and informative instructions.

**Agent.rse** autonomously explore multiple tools to:

- Search intallation-related section,
- Detect installation methods (plans and steps), 
- Repair installation methods (RepairAgent.rse: An Autonomous, LLM-Based Agent for installation instructions Repair),
- Generate installation methods.

**Agent.rse** is built and maintained by researchers from OEG group. It's an academic research project started at UPM University as part of my PhD thesis. Agent.rse is a researcher agent that operates from a command line to help researchers making their software with higher quality and sustainable.  We envision a Agent-based system capable of tasks aiding researchers (ranging from intalling research software, repairing instructions, running tools and simplifying instruction-guide manuals, to writing entire installation procedures and conducting installation-test). We believe this work opens up a new era of AI-driven scientific research and accelerated discovery.




