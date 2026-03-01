# Quick Start Guide

Welcome to Webis v2! This guide will get you running in 5 minutes.

## 🎯 What You'll Learn

- Installing Webis via conda
- Running an intelligent crawl pipeline
- Generating HTML / Markdown reports from RAG knowledge bases
- Launching the Streamlit visualizer

## 🚀 Installation

### Option 1: Conda Setup (Recommended)

```bash
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis
bash setup/conda_setup.sh
```

The script creates a `webis` conda environment (Python 3.10), installs all
dependencies from `setup/requirements.txt`, and registers the `webis` CLI via
`pip install -e .`.

### Option 2: uv Setup

```bash
bash setup/uv_setup.sh
```

### Option 3: Manual Installation

```bash
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis
pip install -e .
```

## ⚙️ Configuration

Copy the environment template and fill in your API keys:

```bash
cp .env.example .env
```

**Minimum required keys** (at least one LLM + one search):

```env
# LLM Provider (pick one or more)
DEEPSEEK_API_KEY=your_deepseek_key
SILICONFLOW_API_KEY=your_siliconflow_key
# OPENAI_API_KEY=your_openai_key

# Search API (pick one or more)
TAVILY_API_KEY=your_tavily_key
BOCHA_API_KEY=your_bocha_key
# EXA_API_KEY=your_exa_key
```

You can override the default LLM with:

```env
WEBIS_LLM_MODEL=deepseek-v3.2   # or gpt-4o, claude-sonnet, qwen-coder-32b, etc.
```

## ⚡ First Pipeline

### 1. Run an Intelligent Crawl

```bash
webis run "Latest artificial intelligence news" --limit 5
```

This triggers the **Intelligent Pipeline**:

1. **CrawlerAgent** — LLM selects the best search plugins (Tavily, Bocha,
   Exa, Serper, BrightData, …), executes queries with automatic variation per
   iteration.
2. **HTML Clean** — Raw pages are cleaned via `HTMLCleanerPlugin`; snippet-only
   results are auto-fetched for full content.
3. **ValidationAgent** — Each document is scored by the LLM for relevance;
   duplicates are filtered by URL.
4. **Loop** — Steps 1–3 repeat (up to 3 iterations) until enough quality
   documents are collected.
5. **LLM Extraction** — Structured data is extracted via `LLMExtractorPlugin`.
6. **RAG Knowledge Base** — Documents are embedded
   (`sentence-transformers/all-MiniLM-L6-v2`) and stored as
   `rag_store.json`.

Results are saved to `./output/<timestamp>/`.

### 2. Check Your Results

```bash
ls ./output/<timestamp>/
# result.json        — structured extraction results
# rag_store.json     — RAG knowledge base (embeddings + documents)
# documents.json     — raw collected documents
```

### 3. Generate an HTML Report

```bash
webis html-report ./output/<timestamp>/rag_store.json \
  --query "Latest artificial intelligence news"
```

This runs the **3-Agent Report Pipeline**:

| Agent | Role |
|-------|------|
| **RAGRetrievalAgent** | Ranks documents, generates an analysis pack (KPIs, insights, patterns, risks) |
| **TemplateDesignAgent** | Designs a topic-adaptive CSS theme and presentation layout |
| **ReportAssemblyAgent** | Assembles a standalone HTML5 report via hybrid LLM + deterministic rendering |

Output: `./output/<timestamp>/report.html`

### 4. Generate a Markdown Report

```bash
webis markdown-report ./output/<timestamp>/rag_store.json \
  --query "Latest artificial intelligence news"
```

## 🖥️ Web Interface

Launch the Streamlit visualizer:

```bash
webis visualizer
```

Open `http://localhost:8501` in your browser.

### Basic Workflow

1. **Enter a task** — natural language description of what you want to research
2. **Run Pipeline** — watch real-time progress as agents crawl, clean, and validate
3. **Review Results** — browse collected documents, view KPIs, export data
4. **Generate Report** — click to generate an HTML intelligence report

## 📄 Extract from Local Files

```bash
webis extract report.pdf \
  --task "Extract key findings and conclusions" \
  --schema schema.json
```

Supports PDF, DOCX, HTML, Markdown, and plain text.

## 🎯 Next Steps

- [User Guide](user-guide.md) — Complete feature walkthrough
- [API Reference](api.md) — Core classes and CLI reference
- [Plugin Development](plugins.md) — Create custom source / processor / extractor plugins
- [Deployment Guide](deployment.md) — Production setup
- [Docker Usage](docker-usage.md) — Container-based deployment
