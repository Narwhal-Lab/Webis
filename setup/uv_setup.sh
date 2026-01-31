#!/usr/bin/env bash
# uv_setup.sh - Webis uv Environment Setup Script
# Simple one-command setup for Webis project using uv

set -e

echo "=== Webis uv Environment Setup ==="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv not found. Please install first: https://docs.astral.sh/uv/"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Creating virtual environment..."
    cd "$PROJECT_ROOT"
    uv venv webis
    echo "Virtual environment created at: $PROJECT_ROOT/webis"
    echo "Please activate it manually: source webis/bin/activate"
else
    echo "Using existing virtual environment: $VIRTUAL_ENV"
fi

# Install dependencies from requirements.txt
echo ""
echo "Installing dependencies from requirements.txt (includes brightdata-sdk)..."
cd "$PROJECT_ROOT"
if [ -n "$VIRTUAL_ENV" ]; then
    # If venv is activated, use regular pip
    pip install --upgrade pip
    pip install -r setup/requirements.txt
else
    # If venv is not activated, activate it first or use uv pip with venv path
    VENV_PYTHON="$PROJECT_ROOT/webis/bin/python"
    if [ -f "$VENV_PYTHON" ]; then
        echo "Installing to virtual environment: $PROJECT_ROOT/webis"
        "$VENV_PYTHON" -m pip install --upgrade pip
        "$VENV_PYTHON" -m pip install -r setup/requirements.txt
    else
        echo "Error: Virtual environment not found. Please run this script again after creating the venv."
        exit 1
    fi
fi

echo ""
echo "Setup completed successfully!"
echo ""
if [ -z "$VIRTUAL_ENV" ]; then
    echo "To use the environment:"
    echo "  source webis/bin/activate"
    echo ""
fi
echo "To test the installation:"
echo "  python tools/examples/demo.py"
