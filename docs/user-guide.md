# User Guide

Complete guide for using Webis v2.

## Table of Contents

1. [Installation](#installation)
2. [CLI Commands](#cli-commands)
3. [Intelligent Pipeline](#intelligent-pipeline)
4. [HTML Report Generation](#html-report-generation)
5. [Document Extraction](#document-extraction)
6. [RAG Knowledge Base](#rag-knowledge-base)
7. [Web Interface (Visualizer)](#web-interface-visualizer)
8. [LLM Configuration](#llm-configuration)
9. [Search Source Plugins](#search-source-plugins)
10. [Troubleshooting](#troubleshooting)

## Installation

### Conda (Recommended)

```bash
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis
bash setup/conda_setup.sh
conda activate webis
```

### Docker

```bash
docker-compose up -d
```

See [Docker Usage](docker-usage.md) for details.

### Manual

```bash
pip install -e .
```

## CLI Commands

Webis provides five main CLI commands:

### `webis run` — Intelligent Crawl Pipeline

```bash
webis run <TASK> [--limit N] [--output DIR]
```

| Argument | Description |
|----------|-------------|
| `TASK` | Natural language task description (positional, required) |
| `--limit N` | Maximum number of documents to collect (default: 5) |
| `--output DIR` / `-o DIR` | Output directory (default: `./output/<timestamp>/`) |

**Example:**

```bash
webis run "Recent developments in quantum computing" --limit 10
```

**Pipeline Phases:**

| Phase | What Happens |
|-------|-------------|
| Phase 1 | Intelligent crawl — CrawlerAgent + ValidationAgent loop |
| Phase 2 | Document processing — PDF parsing, document parsing |
| Phase 3 | LLM extraction — Structured data extraction via LLM |
| Phase 4 | RAG knowledge base — Embeddings + vector store |

### `webis html-report` — Generate HTML Report

```bash
webis html-report <RAG_STORE> [--output DIR] [--query TEXT]
```

| Argument | Description |
|----------|-------------|
| `RAG_STORE` | Path to `rag_store.json` (positional, required) |
| `--output DIR` / `-o DIR` | Output directory |
| `--query TEXT` | Report focus query |

**Example:**

```bash
webis html-report ./output/20260226_030717/rag_store.json \
  --query "AI breakthroughs in 2026"
```

### `webis markdown-report` — Generate Markdown Report

```bash
webis markdown-report <RAG_STORE> [--query TEXT]
```

Uses a two-stage LLM synthesis to produce a Markdown report.

### `webis extract` — Extract from Local Files

```bash
webis extract <FILES...> [--task TEXT] [--schema PATH] [--output DIR]
```

| Argument | Description |
|----------|-------------|
| `FILES` | One or more file paths (positional) |
| `--task TEXT` | Extraction goal (default: "Extract main information") |
| `--schema PATH` | JSON schema file for structured output |
| `--output DIR` / `-o DIR` | Output directory |

**Example:**

```bash
webis extract report.pdf paper.pdf \
  --task "Extract key findings and conclusions" \
  --schema schema.json
```

### `webis visualizer` — Launch Web UI

```bash
webis visualizer
```

Opens the Streamlit-based dashboard at `http://localhost:8501`.

## Intelligent Pipeline

The core of Webis v2 is the **Intelligent Pipeline** — an agent-driven
crawl-clean-validate loop.

### Architecture

```
┌─────────────────────────────────────────┐
│           IntelligentPipeline           │
│                                         │
│   ┌──────────┐     ┌───────────────┐   │
│   │ Crawler   │────▶│ HTML Cleaner  │   │
│   │ Agent     │     │ + Fetcher     │   │
│   └──────────┘     └──────┬────────┘   │
│        ▲                   │            │
│        │           ┌───────▼────────┐   │
│        │           │ Validation     │   │
│        └───────────│ Agent          │   │
│    (next iteration)└────────────────┘   │
│                                         │
│   Parameters:                           │
│   • min_count (target doc count)        │
│   • relevance_threshold (default: 0.7)  │
│   • max_iterations (default: 3)         │
└─────────────────────────────────────────┘
```

### CrawlerAgent

- Uses the LLM to select optimal search plugins for the task
- Supports 11 registered search sources (see [Search Source Plugins](#search-source-plugins))
- Automatic **query variation** across iterations to broaden coverage
- URL-based deduplication via `exclude_urls`

### ValidationAgent

- LLM-scored relevance per document (0.0–1.0)
- Documents scoring ≥ `relevance_threshold` are accepted
- Tracks `AgentState` with `seen_urls` to prevent re-processing

### Auto-Fetch for Snippets

If a search result only returns a snippet (< 500 characters), the pipeline
automatically fetches the full page via `HtmlFetcherPlugin` before cleaning.

## HTML Report Generation

The `webis html-report` command runs a **3-Agent Pipeline**:

### Agent 1: RAG Retrieval Agent

- Loads documents from `rag_store.json`
- Ranks by keyword overlap relevance
- Calls LLM to generate a structured **analysis pack**:
  - `report_title` — topic-specific, engaging
  - `executive_summary` — 2–3 sentence narrative
  - `kpis` — domain-specific KPIs (not generic)
  - `insights` — ≥ 4 findings with varying confidence levels
  - `patterns`, `actions`, `risks`
  - `evidence_matrix` with source references
  - `methodology`

### Agent 2: Template Design Agent

- Receives the analysis pack
- Calls LLM to design a **topic-adaptive CSS theme**:
  - Tech topics → dark glassmorphism
  - Business topics → corporate navy + gold
  - Science topics → clean teal/academic
  - News topics → newspaper-style serif
  - Health topics → calming blue/green
- Generates a **presentation pack** (layout cards, KPI cards, insight cards)

### Agent 3: Report Assembly Agent

- **Hybrid approach**: LLM generates creative `<body>` section HTML
  (`max_tokens=8000`, `temperature=0.7`), wrapped in a deterministic
  HTML5 skeleton for reliability
- If LLM generation fails, a guaranteed deterministic renderer kicks in
- Post-processing: HTML sanitization, validation, and auto-repair

### Output

A single standalone HTML5 file with:
- Embedded CSS (no external dependencies)
- Responsive layout
- Topic-adapted visual design
- All data from the RAG knowledge base

## Document Extraction

```bash
webis extract document.pdf --task "Extract financial metrics"
```

**Supported formats:** PDF, DOCX, HTML, Markdown, plain text.

**Pipeline:**
1. `PDFPlugin` / `DocumentParsePlugin` — parse the file
2. `LLMExtractorPlugin` — LLM-based structured extraction
3. Output to JSON with optional schema validation

**Custom schema example** (`schema.json`):

```json
{
  "type": "object",
  "properties": {
    "title": { "type": "string" },
    "author": { "type": "string" },
    "key_findings": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

## RAG Knowledge Base

Every `webis run` with sufficient documents builds a RAG knowledge base:

- **Embedding model**: `sentence-transformers/all-MiniLM-L6-v2` (cached locally, works offline)
- **Storage**: `rag_store.json` — contains document content + metadata keyed by URL
- **Usage**: Feeds into `html-report` and `markdown-report` commands

Environment variables for offline mode (auto-set by the pipeline):

```env
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

## Web Interface (Visualizer)

```bash
webis visualizer
```

The Streamlit-based dashboard provides:

| Panel | Features |
|-------|----------|
| **Task Input** | Natural language query, parameter configuration |
| **Pipeline Dashboard** | Real-time progress, iteration tracking |
| **Results** | Document browser, export (JSON, CSV, Markdown) |
| **AI Assistant** | RAG-powered Q&A over collected documents |
| **Report Generator** | One-click HTML report generation |

## LLM Configuration

### Supported Models

| Key | Model | Provider | Context | Notes |
|-----|-------|----------|---------|-------|
| `deepseek-v3.2` | `deepseek-chat` | DeepSeek | 64K | JSON mode, default primary |
| `deepseek-r1` | `deepseek-reasoner` | DeepSeek | 64K | Reasoning model |
| `qwen-coder-32b` | `Qwen/Qwen2.5-Coder-32B-Instruct` | SiliconFlow | 32K | JSON mode |
| `gpt-4o` | `gpt-4o` | OpenAI | 128K | JSON mode + Vision |
| `gpt-4o-mini` | `gpt-4o-mini` | OpenAI | 128K | JSON mode |
| `claude-sonnet` | `claude-sonnet-4-20250514` | Anthropic | 200K | Vision |

### Model Selection

1. Set `WEBIS_LLM_MODEL` in `.env` to choose a specific primary model
2. Or let Webis auto-select based on available API keys and model capabilities
3. Free fallback: `Qwen/Qwen2.5-7B-Instruct` via SiliconFlow

### Fallback Chain

The `LLMRouter` automatically retries with fallback models if the primary fails:

```
Primary Model → Fallback 1 → Fallback 2 → Free Tier (Qwen 7B)
```

Built-in response caching (SHA256-keyed, up to 1000 entries) avoids redundant calls.

### Custom Model Endpoint

```env
CUSTOM_API_KEY=your_key
CUSTOM_MODEL_NAME=your-model
CUSTOM_BASE_URL=https://your-endpoint/v1
```

## Search Source Plugins

### Auto-Registered Sources (10)

| Plugin Name | API Key Env Var | Description |
|-------------|----------------|-------------|
| `tavily_search` | `TAVILY_API_KEY` | Tavily AI-optimized search |
| `bocha_search` | `BOCHA_API_KEY` | Bocha search API |
| `exa_firecrawl_crawler` | `EXA_API_KEY` | Exa + Firecrawl search/crawl |
| `serper_search` | `SERPER_API_KEY` | Serper Google search |
| `serpapi` | `SERPAPI_API_KEY` | SerpAPI Google search |
| `bright_data` | `BRIGHTDATA_API_TOKEN` | Bright Data scraping |
| `github` | `GITHUB_TOKEN` | GitHub repositories |
| `gnews` | `GNEWS_API_KEY` | Google News |
| `hackernews` | *(none needed)* | Hacker News stories |
| `semantic_scholar` | *(none needed)* | Academic papers |

### How Source Selection Works

The **CrawlerAgent** uses the LLM to pick the best sources for each task:

1. Evaluates which plugins have valid API keys
2. LLM ranks sources by relevance to the query
3. Falls back to other enabled search providers if one source fails
4. Query is automatically varied across iterations

## Troubleshooting

### SSL / Network Errors

Webis includes resilient TLS handling with automatic retries:

```bash
# If you see SSL certificate errors, they are auto-handled.
# For HuggingFace model downloads behind a firewall:
export HF_ENDPOINT=https://hf-mirror.com
```

### Embedding Model Download Issues

The pipeline auto-sets `HF_HUB_OFFLINE=1` and retries with cached models.
Pre-download the model:

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Pipeline Returns 0 Documents

- Check that at least one search API key is configured
- Lower `--limit` to start with fewer documents

### HTML Report Hangs

- The 3-agent pipeline makes 3–4 LLM calls; allow 1–2 minutes
- Check LLM API key validity
- If the primary model is down, the fallback chain will be tried

### Common Environment Variables

```env
# Force a specific LLM
WEBIS_LLM_MODEL=deepseek-v3.2

# Debug logging
LOG_LEVEL=DEBUG
DEBUG=true

# Offline mode for embeddings
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

---

## Next Steps

- [API Reference](api.md) — Core classes and CLI reference
- [Plugin Development](plugins.md) — Create custom plugins
- [Deployment Guide](deployment.md) — Production setup
- [Docker Usage](docker-usage.md) — Container-based deployment
