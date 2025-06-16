#!/bin/bash
# Wrapper script to capture output
cd /Users/ccugutrillague/Documents/perso/doctorado/projects/agent.rse/execution_agent_workspace/outputs
exec 1> /Users/ccugutrillague/Documents/perso/doctorado/projects/agent.rse/execution_agent_workspace/outputs/installation.log 2> /Users/ccugutrillague/Documents/perso/doctorado/projects/agent.rse/execution_agent_workspace/outputs/installation_errors.log
echo "Starting installation at $(date)"
./$(basename /Users/ccugutrillague/Documents/perso/doctorado/projects/agent.rse/execution_agent_workspace/outputs/install.sh)
exit_code=$?
echo "Installation finished at $(date) with exit code $exit_code"
exit $exit_code
