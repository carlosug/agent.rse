#!/bin/bash
set -e

echo "Cloning the repository..."
git clone https://github.com/bytedance/repo2run.git
echo "Cloning completed successfully."

echo "Changing directory to repo2run..."
cd repo2run
echo "Directory changed to repo2run."

echo "Installing dependencies..."
pip install -r requirements.txt
echo "Dependencies installed successfully."

echo "Installation and setup completed."
