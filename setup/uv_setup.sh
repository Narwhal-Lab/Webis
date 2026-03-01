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
echo "Installing dependencies from requirements.txt (includes visualizer + brightdata-sdk)..."
cd "$PROJECT_ROOT"
if [ -n "$VIRTUAL_ENV" ]; then
    # If venv is activated, use uv pip
    uv pip install --upgrade pip
    uv pip install -r setup/requirements.txt
else
    # If venv is not activated, use uv pip with venv path
    VENV_PATH="$PROJECT_ROOT/webis"
    if [ -d "$VENV_PATH" ]; then
        echo "Installing to virtual environment: $VENV_PATH"
        uv pip install --upgrade pip --python "$VENV_PATH/bin/python"
        uv pip install -r setup/requirements.txt --python "$VENV_PATH/bin/python"
    else
        echo "Error: Virtual environment not found. Please run this script again after creating the venv."
        exit 1
    fi
fi

# Install the local package so the `webis` CLI entry point is available.
echo ""
echo "Installing webis package in editable mode..."
if [ -n "$VIRTUAL_ENV" ]; then
    uv pip install -e "$PROJECT_ROOT"
else
    uv pip install -e "$PROJECT_ROOT" --python "$PROJECT_ROOT/webis/bin/python"
fi

echo ""
echo "Setup completed successfully!"
echo ""
if [ -z "$VIRTUAL_ENV" ]; then
    echo "To use the environment:"
    echo "  source webis/bin/activate"
    echo ""
fi
echo "To verify the installation:"
echo "  webis --help"
echo ""
echo "To run the visualizer:"
echo "  webis visualizer"
