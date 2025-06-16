#!/bin/bash
set -e

echo "Cloning the SOMEF repository..."
git clone https://github.com/KnowledgeCaptureAndDiscovery/somef.git

echo "Installing Poetry..."
curl -sSL https://install.python-poetry.org | python3 -

echo "Installing SOMEF and its dependencies..."
cd somef
poetry install

echo "Installing the poetry plugin shell..."
pip install poetry-plugin-shell

echo "Accessing the virtual environment..."
poetry shell