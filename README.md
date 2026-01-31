# Webis: AI-Powered Data Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Webis** is a modular, plugin-based framework designed to power the next generation of AI applications. It connects diverse data sources (Web, SaaS, DBs) to Large Language Models (LLMs) through a robust pipeline of sourcing, processing, and extraction.

## 🚀 Key Features

* **Plugin-First Architecture**: Everything is a plugin (Source, Processor, Extractor, Model).
* **Intelligent Crawler Agent**: Uses LLMs to dynamically select the best data sources and formulate queries.
* **RAG-Ready**: Built-in support for cleaning, chunking, and preparing data for Retrieval Augmented Generation.
* **LLM Extraction**: Turn unstructured PDFs/Webpages into structured JSON using dynamic schemas.
* **Unified CLI**: Simple `webis` command for all operations.

## 📦 Installation

```bash
cd webis
pip install -e .
```

## 🛠️ Usage

Webis operates primarily through the `webis` CLI.

### 1. End-to-End Run

Execute a full pipeline: identifying sources -> crawling -> cleaning -> extracting.

```bash
# Example: Find news about Peking University in the last three months and generate a report
webis run "Find news about Peking University in the last three months and generate a report" --limit 3
```

✨ **New**: Results are automatically saved to `output/{timestamp}/`.

* `report.html`: A beautiful HTML report (if extraction succeeds).
* `result.json`: Structured extracted data.
* `documents.json`: **Full raw and cleaned content** of all crawled documents (saved even if extraction fails).

## ⚠️ Configuration

You must configure your API keys in `.env` for Agent features to work.

### 2. Crawl Only

Fetch documents without extraction. Returns a JSON list of `WebisDocument`.

```bash
webis crawl "Python 3.13 new features" --limit 5 -o crawl_results.json
```

### 3. Extract Only

Extract structured data from local files using LLMs.

```bash
# Extract from a PDF
webis extract ./report.pdf --task "Extract financial summary"

# Extract with a specific schema
webis extract ./cv.pdf --schema ./schemas/resume.json
```

## 🧩 Architecture

The project is structured under `src/webis/`:

* **`core/`**: The kernel (Agents, Pipeline, Plugin Registry).
* **`plugins/`**:
  * `sources/`: GNews, Google Search, GitHub, etc.
  * `processors/`: PDF Parser, HTML Cleaner, etc.
  * `extractors/`: LLMExtractor.
* **`plugin_sdk/`**: Developer-friendly interface for building new plugins.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to write new plugins using the SDK.
