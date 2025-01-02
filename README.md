# agent.rse

The agent attempts to autonomously install a given open source research software repository. Agent.rse performs its tasks in two stages: i) it gathers text related to the installation from README and ii) it tries to build, generate ,and if necessary, repair, a instruction to install and test the target repository. We will explore how different LLMs can cooperate to enhance Agent.rese ability to transform a unstructured README into clear, concise and informative instructions.

**Agent.rse** autonomously explore multiple tools to:

- search intallation-related section,
- detect installation methods (plans and steps), 
- repair installation methods,
- generate installation methods.

**Agent.rse** is built and maintained by researchers from OEG group. It's an academic research project started at UPM University as part of my PhD thesis. We envisioned a system capable of tasks aiding researchers (ranging from ideation, writing code, running experiments and summarizing results, to writing entire papers and conducting peer-review). We believe this work opens up a new era of AI-driven scientific research and accelerated discovery
