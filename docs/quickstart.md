# Quick Start Guide

Welcome to Webis! This guide will help you get started in just 5 minutes.

## 🎯 What You'll Learn

- Installing Webis
- Running your first pipeline
- Using the web interface
- Your first results

## 🚀 Installation

### Option 1: One-Command Setup (Recommended)

```bash
# Run the setup script
bash setup/conda_setup.sh
```

This script will:
- Create a new conda environment
- Install Webis
- Download necessary models
- Set up configuration

### Option 2: Manual Installation

```bash
# Clone and install
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis
pip install -e .
```

## ⚡ First Pipeline

### 1. Simple Web Data Collection

Let's get the latest AI news:

```bash
webis run "Latest artificial intelligence news" --limit 5
```

This command will:
- Search the web for AI news
- Extract and clean content
- Save results to `./output/timestamp/result.json`

### 2. Check Your Results

```bash
# View the structured results
cat ./output/timestamp/result.json | head -50
```

```json
[
  {
    "title": "OpenAI Announces New GPT-5 Model",
    "url": "https://example.com/openai-gpt5",
    "content": "OpenAI announced their latest model...",
    "published_at": "2024-01-15",
    "source": "TechCrunch"
  }
]
```

## 🖥️ Web Interface

Launch the visualizer:

```bash
webis visualizer
```

Open your browser to `http://localhost:8501`

### Basic Workflow:

1. **Add Data Sources**
   - Click "Add Data Source" in the sidebar
   - Choose web crawling or file upload
   - Enter your query (e.g., "AI news")

2. **Run Pipeline**
   - Click "Run Pipeline"
   - Watch the progress
   - See real-time updates

3. **Review Results**
   - Switch between tabs for different views
   - Export data in various formats
   - Use the AI Assistant for analysis

## 📄 Process Local Files

Extract information from a PDF:

```bash
# Download a sample PDF (or use your own)
curl -o sample.pdf https://example.com/sample.pdf

# Extract information
webis extract sample.pdf --task "Extract key findings and main conclusions"
```

## 🔧 Configuration

Create a `.env` file for API keys:

```bash
# Copy the template
cp .env.example .env
```

Edit `.env` and add your keys:

```env
# LLM Provider
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Search APIs
SERPAPI_API_KEY=your_serpapi_key
TAVILY_API_KEY=your_tavily_key
```

## 🎯 Next Steps

1. **Try different data sources**
   ```bash
   webis run "Python tutorials" --sources github,stackoverflow
   ```

2. **Build a knowledge base**
   ```bash
   webis run "Recent ML papers" --rag-mode --limit 10
   ```

3. **Explore the examples**
   ```bash
   ls examples/
   ```

## 📚 Need Help?

- [User Guide](user-guide.md) - Complete feature walkthrough
- [API Reference](api.md) - Full API documentation
- [Plugin Development](plugins.md) - Create custom plugins
- [Community](https://github.com/Narwhal-Lab/Webis/discussions) - Get help from the community

---

You're ready to explore Webis! Check out the [User Guide](user-guide.md) for a complete walkthrough of all features.