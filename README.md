# Webis: AI-Driven Data Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Webis** is a modular, plugin-based framework designed to power the next generation of AI applications. Through a robust pipeline of collection, processing, and extraction, it connects diverse data sources (Web, SaaS, databases, etc.) to Large Language Models (LLMs).

## 🚀 Key Features

* **Plugin-First Architecture**: Everything is a plugin (Source, Processor, Extractor, Model).
* **Intelligent Crawler Agent**: Uses LLMs to dynamically select the best data sources and generate queries.
* **RAG-Ready**: Built-in cleaning, chunking, and RAG preparation capabilities.
* **LLM Extraction**: Turn unstructured PDFs/webpages into structured JSON (supports dynamic schemas).
* **Unified CLI**: Use a single `webis` command to complete all operations.

## 📦 Installation

```bash
cd webis
pip install -e .
```

## 🛠️ Usage

Webis primarily runs via the `webis` CLI.

### 1. End-to-End Run

Execute the full pipeline: identify data sources -> crawl -> clean -> extract -> visual report.

```bash
# Example: Find news about Peking University in the last three months and generate a report
webis run "Find news about Peking University in the last three months and generate a report" --limit 3
```

* `report.html`: A beautiful HTML report (if extraction succeeds).
* `result.json`: Structured extraction results.
* `documents.json`: **Raw and cleaned content** of all crawled documents (saved even if extraction fails).

## ⚠️ Configuration

You must configure API keys in `.env` for Agent features to work.

### 2. Crawl Only

Only fetch relevant data.

```bash
webis crawl "Python 3.13 new features" --limit 5 
```

* `output/{timestamp}/documents.json`
* `output/{timestamp}/result.json`


### 3. Extract Only

Use LLMs to extract structured data from local files.

```bash
# Extract from a PDF
webis extract ./report.pdf --task "Extract financial summary"

# Extract with a specific schema
webis extract ./cv.pdf --schema ./schemas/resume.json
```

### 4. Generate HTML Report

Generate `report.html` from an existing `result.json` (optional `documents.json`).

```bash
webis html-report ./output/20260204_113243/result.json --documents ./output/20260204_113243/documents.json
```

By default, output is written to the directory containing `result.json`.

## 🖥️ Visualizer

### 1. Launch the Visualizer

```bash
webis visualizer
```

### 2. Basic Flow

* Add data sources in the left sidebar (web crawling or local upload).
* Run the pipeline and wait for completion.
* Review structured JSON and statistics in the UI.
* Use the AI assistant tab for analysis with source context.

## 🧩 Architecture

The project structure is under `src/webis/`:

* **`core/`**: Core (Agents, Pipeline, Plugin Registry).
* **`plugins/`**:
  * `sources/`: GNews, Google Search, GitHub, etc.
  * `processors/`: PDF parsing, HTML cleaning, etc.
  * `extractors/`: LLMExtractor.
* **`plugin_sdk/`**: Developer-friendly interface for building new plugins.

## 🤝 Contributing

We welcome contributions! To build new plugins with the SDK, see [CONTRIBUTING.md](CONTRIBUTING.md).
