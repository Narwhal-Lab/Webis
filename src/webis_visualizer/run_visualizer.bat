@echo off
REM Webis Visualizer Launcher for Windows
REM Usage: run_visualizer.bat

cd /d "%~dp0\..\.."

REM Install dependencies if needed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo 📦 Installing dependencies...
    pip install -r src/webis_visualizer/requirements.txt
)

echo 🚀 Starting Webis Visualizer...
echo 📊 Please open http://localhost:8501 in your browser
echo.

streamlit run src/webis_visualizer/app.py