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
    source webis/bin/activate
else
    echo "Using existing virtual environment: $VIRTUAL_ENV"
fi

# Install dependencies from requirements.txt
echo ""
echo "Installing dependencies from requirements.txt..."
cd "$PROJECT_ROOT"
uv pip install --upgrade pip
uv pip install -r setup/requirements.txt

echo ""
echo "Setup completed successfully!"
echo ""
echo "To use the environment:"
echo "  source webis/bin/activate"
echo ""
echo "To test the installation:"
echo "  python examples/demo.py"
