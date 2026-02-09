# User Guide

Complete guide for using Webis's features.

## Table of Contents

1. [Installation](#installation)
2. [Web Data Collection](#web-data-collection)
3. [Document Processing](#document-processing)
4. [Knowledge Base Building](#knowledge-base-building)
5. [Web Interface](#web-interface)
6. [Advanced Features](#advanced-features)
7. [Troubleshooting](#troubleshooting)

## Installation

### Quick Install

```bash
# Using setup script
bash setup/conda_setup.sh
```

### Manual Install

```bash
# Install from source
git clone https://github.com/Narwhal-Lab/Webis.git
cd webis
pip install -e .
```

### Docker Install

```bash
# Using Docker Compose
docker-compose up

# Detached mode
docker-compose up -d
```

## Web Data Collection

### Basic Search

```bash
webis run "Latest AI news" --limit 5
```

### Using Specific Sources

```bash
webis run "Machine learning tutorials" \
  --sources github,stackoverflow \
  --limit 10
```

### Advanced Search

```bash
webis run "Recent developments in quantum computing" \
  --sources semantic_scholar,arxiv \
  --limit 20 \
  --date-range "2024-01-01:2024-12-31"
```

### Available Sources

| Source | Description | Use Case |
|---|---|---|
| `duckduckgo` | General web search | General queries |
| `github` | GitHub repositories | Code, projects |
| `semantic_scholar` | Academic papers | Research |
| `gnews` | Google News | News articles |
| `reddit` | Reddit discussions | Community opinions |
| `hackernews` | Hacker News | Tech news |

## Document Processing

### Processing PDFs

```bash
# Extract from a PDF
webis extract ./report.pdf --task "Extract financial summary and key metrics"
```

### Processing Multiple Files

```bash
# Batch processing
webis batch process ./documents/ --task "Extract entities"
```

### Custom Schema

Create a schema file `schema.json`:

```json
{
  "type": "object",
  "properties": {
    "title": {"type": "string"},
    "author": {"type": "string"},
    "date": {"type": "string"},
    "summary": {"type": "string"},
    "key_findings": {
      "type": "array",
      "items": {"type": "string"}
    }
  }
}
```

Use the schema:

```bash
webis extract ./paper.pdf \
  --schema ./schema.json \
  --output result.json
```

## Knowledge Base Building

### Basic RAG Setup

```bash
webis run "AI research papers" \
  --rag-mode \
  --limit 10
```

### Advanced RAG Configuration

```bash
webis run "Recent ML tutorials" \
  --rag-mode \
  --chunk-size 1000 \
  --chunk-overlap 200 \
  --embed-model all-MiniLM-L6-v2
```

### Custom Embedding Model

```bash
# Use a different embedding model
webis run "NLP research" \
  --rag-mode \
  --embed-model sentence-transformers/all-mpnet-base-v2
```

## Web Interface

### Starting the Visualizer

```bash
webis visualizer
```

Access at: `http://localhost:8501`

### Main Features

#### Data Sources Panel
- Add web crawling tasks
- Upload local files
- Configure data sources
- View source status

#### Pipeline Dashboard
- Real-time progress tracking
- Pipeline visualization
- Step-by-step execution view
- Performance metrics

#### Results Panel
- Multiple view modes (table, JSON, raw)
- Export options (CSV, JSON, Excel, Markdown)
- Statistical summaries
- Data filtering and sorting

#### AI Assistant
- Natural language queries
- Source-referenced answers
- Context-aware responses
- Quick analysis prompts

### Interface Navigation

| Feature | Access Method | Purpose |
|---|---|---|
| Add Data | Left sidebar | Add new data sources |
| Pipeline | Main tab | View and manage pipelines |
| Results | Results tab | View and export processed data |
| AI Assistant | AI tab | Query your knowledge base |

## Advanced Features

### Custom Pipeline Configuration

Create a pipeline configuration file `pipeline.yaml`:

```yaml
pipeline:
  sources:
    - name: duckduckgo
      config:
        max_results: 10

  processors:
    - name: html_cleaner
    - name: deduplicator

  extractors:
    - name: llm_extractor
      config:
        model: gpt-4
```

Run the custom pipeline:

```bash
webis run --config ./pipeline.yaml "Your query here"
```

### Batch Operations

```bash
# Process multiple queries
webis batch run queries.txt --output ./results/

# Process multiple files
webis batch extract ./documents/ --task "Extract summaries"
```

### API Integration

```python
from webis import WebisClient

client = WebisClient(api_key="your_api_key")

# Run a pipeline
result = client.run(
    query="Latest AI news",
    sources=["duckduckgo"],
    limit=5
)

# Get results
print(result.data)
```

## Troubleshooting

### Common Issues

#### Issue: API Keys Not Found

**Error**: `APIKeyNotFoundError`

**Solution**:
```bash
# Check .env file
cat .env

# Verify keys are set
print($env:OPENAI_API_KEY)
```

#### Issue: Model Download Failed

**Error**: `ModelDownloadError`

**Solution**:
```bash
# Set HuggingFace mirror (for China)
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DOWNLOAD_TIMEOUT=120

# Download model manually
hf download sentence-transformers/all-MiniLM-L6-v2
```

#### Issue: Memory Error

**Error**: `MemoryError` during processing

**Solution**:
```bash
# Process smaller batches
webis run "Your query" --limit 5 --batch-size 2

# Use smaller chunk size
webis run "Your query" --rag-mode --chunk-size 500
```

### Getting Help

- 📖 [Documentation](https://narwhal-lab.github.io/webis)
- 🐛 [Report a Bug](https://github.com/Narwhal-Lab/Webis/issues)
- 💬 [Discussions](https://github.com/Narwhal-Lab/Webis/discussions)
- 📧 [Email Support](mailto:contact@webis.dev)

## Best Practices

1. **Start Small**
   - Begin with small datasets
   - Test with 2-3 sources
   - Gradually increase complexity

2. **Use RAG for Large Datasets**
   - Enable RAG mode for better search
   - Choose appropriate chunk sizes
   - Test different embedding models

3. **Monitor Performance**
   - Check pipeline status regularly
   - Review performance metrics
   - Optimize based on results

4. **Save Configuration**
   - Create reusable pipeline configs
   - Document custom schemas
   - Keep track of working parameters

---

Ready for more? Check out:
- [API Reference](api.md) - Complete API documentation
- [Plugin Development](plugins.md) - Create custom plugins
- [Deployment Guide](deployment.md) - Production setup