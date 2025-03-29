#!/bin/bash

# Set error handling
set -e

# Print colored output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if Python is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        printf "${RED}Error: Python 3 is not installed${NC}\n"
        exit 1
    fi
}

# Function to check if virtual environment exists
check_venv() {
    if [ ! -d "venv" ]; then
        printf "${BLUE}Creating virtual environment...${NC}\n"
        python3 -m venv venv
    fi
}

# Function to activate virtual environment
activate_venv() {
    printf "${BLUE}Activating virtual environment...${NC}\n"
    source venv/bin/activate
}

# Function to install dependencies
install_dependencies() {
    printf "${BLUE}Installing dependencies...${NC}\n"
    pip install -r requirements.txt
}

# Function to run the AI settings preparation
run_ai_settings() {
    printf "${BLUE}Preparing AI settings...${NC}\n"
    python3 prepare_ai_settings.py
    if [ $? -eq 0 ]; then
        printf "${GREEN}AI settings prepared successfully${NC}\n"
    else
        printf "${RED}Error preparing AI settings${NC}\n"
        exit 1
    fi
}

# Function to run the main system
run_main_system() {
    printf "${BLUE}Starting the AI Assistant...${NC}\n"
    python3 simple.py
}

# Main execution
main() {
    printf "${GREEN}Starting system initialization...${NC}\n"
    
    # Check requirements
    check_python
    check_venv
    activate_venv
    install_dependencies
    
    # Run the system
    run_ai_settings
    run_main_system
}

# Run main function
main