# Output: install.sh (Stored at output/install.sh)

#!/bin/bash

set -e

echo "Starting Deepseek-R1 setup (via Ollama)..."
echo "------------------------------"

# Check for Docker (required by Ollama)
echo "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "Docker detected. Proceeding..."

# Install Ollama CLI
echo "Installing Ollama CLI..."
curl -fsSL https://ollama.ai/install.sh | sudo bash

# Install Python library
echo "Installing Ollama Python package..."
pip install ollama

# Pull the Deepseek-R1 model
echo "Downloading the Deepseek-R1 model..."
ollama pull deepseek-r1:14b

echo ""
echo "Setup complete! To run the script:"
echo "------------------------------"
echo "Run: python deepseek_r1.py"
echo "------------------------------"
echo "Note: Ensure you're in the script's directory and Docker service is active."

chmod +x install.sh