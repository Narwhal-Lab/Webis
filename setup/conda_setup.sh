#!/usr/bin/env bash
# conda_setup.sh - Webis Conda Environment Setup Script
# Simple one-command setup for Webis project

set -e

echo "=== Webis Conda Environment Setup ==="

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Error: Conda not found. Please install Miniconda or Anaconda first."
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create and activate Conda environment
echo ""
echo "Creating Conda environment 'webis'..."
conda create -n webis python=3.9 -y

# Initialize conda for bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate webis

# Install dependencies from requirements.txt
echo ""
echo "Installing dependencies from requirements.txt..."
cd "$PROJECT_ROOT"
pip install --upgrade pip
pip install -r setup/requirements.txt

echo ""
echo "Setup completed successfully!"
echo ""
echo "To use the environment:"
echo "  conda activate webis"
echo ""
echo "To test the installation:"
echo "  python examples/demo.py"
