#!/bin/bash
# Webis Visualizer Launcher Script
# Usage: ./run_visualizer.sh

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project root
cd "$SCRIPT_DIR/../.."

# Install dependencies if needed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r src/webis_visualizer/requirements.txt
fi

# Run Streamlit
echo "🚀 Starting Webis Visualizer..."
echo "📊 Please open http://localhost:8501 in your browser"
echo ""

streamlit run src/webis_visualizer/app.py