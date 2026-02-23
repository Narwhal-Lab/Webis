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
# Use Python 3.9+ (default to 3.10 if available, fallback to 3.9)
if conda search python=3.10 &> /dev/null; then
    PYTHON_VERSION="3.10"
else
    PYTHON_VERSION="3.9"
fi
echo "Using Python $PYTHON_VERSION"
conda create -n webis python=$PYTHON_VERSION -y

# Initialize conda for bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate webis

# Install dependencies from requirements.txt
echo ""
echo "Installing dependencies from requirements.txt (includes visualizer + brightdata-sdk)..."
cd "$PROJECT_ROOT"
pip install --upgrade pip
pip install -r setup/requirements.txt

# Install the local package so the `webis` CLI entry point is available.
echo ""
echo "Installing webis package in editable mode..."
pip install -e . --no-deps

echo ""
echo "Setup completed successfully!"
echo ""
echo "To use the environment:"
echo "  conda activate webis"
echo ""
echo "To verify the installation:"
echo "  webis --help"
echo ""
echo "To run the visualizer:"
echo "  webis visualizer"
