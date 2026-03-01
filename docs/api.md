# API Reference

Core classes, CLI commands, and data models for Webis v2.

## CLI Commands

### `webis run`

Execute the intelligent crawl pipeline.

```bash
webis run <TASK> [OPTIONS]

Arguments:
  TASK                  Natural language task description (required)

Options:
  --limit INTEGER       Maximum documents to collect (default: 5)
  --output, -o PATH     Output directory (default: ./output/<timestamp>/)
```

### `webis html-report`

Generate an HTML report from a RAG knowledge base.

```bash
webis html-report <RAG_STORE> [OPTIONS]

Arguments:
  RAG_STORE             Path to rag_store.json (required)

Options:
  --output, -o PATH     Output directory
  --query TEXT          Report focus query
```

### `webis markdown-report`

Generate a Markdown report from a RAG knowledge base.

```bash
webis markdown-report <RAG_STORE> [OPTIONS]

Arguments:
  RAG_STORE             Path to rag_store.json (required)

Options:
  --query TEXT          Report focus query
```

### `webis extract`

Extract structured data from local files.

```bash
webis extract <FILES...> [OPTIONS]

Arguments:
  FILES                 One or more file paths (required)

Options:
  --task TEXT           Extraction task (default: "Extract main information")
  --schema PATH        JSON schema file for structured output
  --output, -o PATH    Output directory
```

### `webis visualizer`

Launch the Streamlit web interface.

```bash
webis visualizer
```

Opens at `http://localhost:8501`.

---

## Core Classes

### LLMRouter

LLM orchestrator with automatic fallback, caching, and cost tracking.

```python
from webis.core.llm.base import get_default_router

router = get_default_router()
```

#### `router.chat(messages, temperature=0.7, max_tokens=4096, json_mode=False)`

Send a chat completion request with automatic fallback.

**Parameters:**
- `messages` (list[dict]) — Chat messages (`[{"role": "system", "content": "..."}, ...]`)
- `temperature` (float) — Sampling temperature (default: 0.7)
- `max_tokens` (int) — Max response tokens (default: 4096)
- `json_mode` (bool) — Request JSON output (default: False)

**Returns:** `LLMResponse`

**Example:**

```python
response = router.chat(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Summarize quantum computing."},
    ],
    temperature=0.3,
    max_tokens=2000,
)
print(response.content)
print(f"Tokens: {response.usage}")
```

#### `router.get_stats()`

Returns usage statistics: total tokens, cost, cache hits.

---

### ModelConfig

Configuration for a single LLM model.

```python
from webis.core.llm.base import ModelConfig
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | — | Display name |
| `model_name` | str | — | Actual API model name |
| `provider` | str | — | Provider key (openai, deepseek, siliconflow, anthropic) |
| `api_key_env` | str | — | Environment variable for API key |
| `base_url` | str | — | API base URL |
| `max_tokens` | int | 4096 | Default max output tokens |
| `context_window` | int | 64000 | Context window size |
| `supports_json_mode` | bool | False | JSON mode support |
| `supports_vision` | bool | False | Vision support |
| `cost_per_1k_tokens` | float | 0.0 | Cost tracking |

#### Built-in Models

| Key | Model | Provider | Context | Features |
|-----|-------|----------|---------|----------|
| `deepseek-v3.2` | `deepseek-chat` | deepseek | 64K | JSON mode |
| `deepseek-r1` | `deepseek-reasoner` | deepseek | 64K | Reasoning |
| `qwen-coder-32b` | `Qwen/Qwen2.5-Coder-32B-Instruct` | siliconflow | 32K | JSON mode |
| `gpt-4o` | `gpt-4o` | openai | 128K | JSON mode + Vision |
| `gpt-4o-mini` | `gpt-4o-mini` | openai | 128K | JSON mode |
| `claude-sonnet` | `claude-sonnet-4-20250514` | anthropic | 200K | Vision |

---

### WebisDocument

Core document model used throughout the pipeline. Based on Pydantic v2.

```python
from webis.core.schema import WebisDocument
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | str (UUID) | Unique document identifier |
| `content` | str | Raw document content |
| `clean_content` | str \| None | Cleaned content |
| `doc_type` | DocumentType | Document type enum |
| `status` | DocumentStatus | Processing status enum |
| `meta` | DocumentMetadata \| None | Rich metadata |
| `chunks` | list[DocumentChunk] | Chunked segments for RAG |
| `embeddings` | list[float] | Vector embeddings |
| `parent_id` | str \| None | Parent document ID |
| `processing_history` | list[dict] | Processing audit trail |

**Methods:**

```python
doc = WebisDocument(content="Hello World", doc_type=DocumentType.TEXT)
data = doc.to_dict()
doc2 = WebisDocument.from_dict(data)
```

---

### DocumentMetadata

```python
from webis.core.schema import DocumentMetadata
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `url` | str \| None | Source URL |
| `title` | str \| None | Document title |
| `author` | str \| None | Author |
| `published_at` | str \| None | Publication date |
| `fetched_at` | str \| None | Fetch timestamp |
| `source_plugin` | str \| None | Source plugin name |
| `language` | str \| None | Language code |
| `tags` | list[str] | Tags |
| `custom` | dict | Custom key-value metadata |

Configured with `extra="allow"` — arbitrary extra fields are preserved.

---

### Enums

#### DocumentType

```python
from webis.core.schema import DocumentType

DocumentType.HTML      # "html"
DocumentType.PDF       # "pdf"
DocumentType.TEXT      # "text"
DocumentType.MARKDOWN  # "markdown"
DocumentType.IMAGE     # "image"
DocumentType.AUDIO     # "audio"
DocumentType.VIDEO     # "video"
DocumentType.JSON      # "json"
DocumentType.UNKNOWN   # "unknown"
```

#### DocumentStatus

```python
from webis.core.schema import DocumentStatus

DocumentStatus.PENDING     # "pending"
DocumentStatus.PROCESSING  # "processing"
DocumentStatus.COMPLETED   # "completed"
DocumentStatus.FAILED      # "failed"
DocumentStatus.SKIPPED     # "skipped"
```

---

### PipelineContext

Shared context object passed through all pipeline stages.

```python
from webis.core.schema import PipelineContext
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | str (UUID) | Pipeline run identifier |
| `task` | str | Task description |
| `config` | dict | Pipeline configuration |
| `started_at` | str | Start timestamp |
| `current_stage` | str | Current pipeline stage |
| `is_dry_run` | bool | Dry run mode |
| `is_debug` | bool | Debug mode |
| `total_tokens_used` | int | Cumulative LLM token usage |
| `total_cost_usd` | float | Cumulative LLM cost |
| `output_dir` | str | Output directory |
| `state` | dict | Arbitrary shared state |

---

### StructuredResult

Result of LLM-based structured extraction.

```python
from webis.core.schema import StructuredResult
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | str (UUID) | Result identifier |
| `schema_id` | str \| None | Schema identifier |
| `data` | dict | Extracted data |
| `raw_output` | str \| None | Raw LLM output |
| `lineage` | Lineage \| None | Data provenance |
| `is_valid` | bool | Schema validation passed |
| `validation_errors` | list[str] | Validation error messages |
| `needs_review` | bool | Flagged for human review |

---

### PluginRegistry

Singleton registry for all plugin types.

```python
from webis.core.plugin import get_default_registry

registry = get_default_registry()

# Get a source plugin
tavily = registry.get_source("tavily_search")

# Get an output plugin
html_report = registry.get_output("html_report")

# List all sources
all_sources = registry.list_sources()
```

---

## Agent Classes

### CrawlerAgent

Selects and executes search plugins via LLM guidance.

```python
from webis.core.agent.crawler_agent import CrawlerAgent

agent = CrawlerAgent(registry)
documents = agent.run(
    task="Latest AI news",
    limit=5,
    context=pipeline_context,
    exclude_urls=set(),
    iteration=1,
)
```

### ValidationAgent

LLM-scored document relevance validation.

```python
from webis.core.agent.validation_agent import ValidationAgent, AgentState

agent = ValidationAgent()
state = AgentState()

score = agent.check_relevance(document, task="Latest AI news")
# score: float 0.0–1.0

state.add_decision(document, score, threshold=0.7)
```

### AgentState

Tracks pipeline state across iterations.

**Fields:**
- `accepted` — list of accepted documents
- `rejected` — list of rejected documents
- `seen_urls` — set of already-processed URLs
- `is_url_seen(doc)` — check if a document URL was already processed

---

## Report Pipeline Classes

### RAGRetrievalAgent

Agent 1/3 — loads RAG documents, generates analysis pack.

```python
from webis.plugins.outputs.rag_retrieval_agent import RAGRetrievalAgent

agent = RAGRetrievalAgent()
analysis_pack = agent.run(rag_store_path="path/to/rag_store.json", query="...")
# Returns dict with: report_title, executive_summary, kpis, insights,
#   patterns, actions, risks, evidence_matrix, methodology, _rag_payload
```

### TemplateDesignAgent

Agent 2/3 — designs CSS theme and presentation layout.

```python
from webis.plugins.outputs.template_design_agent import TemplateDesignAgent

agent = TemplateDesignAgent()
presentation_pack = agent.run(analysis_pack=analysis_pack, query="...")
# Returns dict with: hero_subtitle, kpi_cards, insight_cards,
#   pattern_cards, matrix_rows, action_items, risk_flags,
#   methodology_points, css_theme
```

### ReportAssemblyAgent

Agent 3/3 — assembles final standalone HTML5 report.

```python
from webis.plugins.outputs.report_assembly_agent import ReportAssemblyAgent

agent = ReportAssemblyAgent()
html_string = agent.run(
    analysis_pack=analysis_pack,
    presentation_pack=presentation_pack,
    query="...",
)
# Returns complete HTML5 string
```

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `WEBIS_LLM_MODEL` | Override default LLM model key |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `SILICONFLOW_API_KEY` | SiliconFlow API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `TAVILY_API_KEY` | Tavily search API key |
| `BOCHA_API_KEY` | Bocha search API key |
| `EXA_API_KEY` | Exa search API key |
| `SERPER_API_KEY` | Serper search API key |
| `SERPAPI_API_KEY` | SerpAPI key |
| `BRIGHTDATA_API_TOKEN` | Bright Data token |
| `CUSTOM_API_KEY` | Custom LLM endpoint key |
| `CUSTOM_MODEL_NAME` | Custom LLM model name |
| `CUSTOM_BASE_URL` | Custom LLM base URL |
| `HF_HUB_OFFLINE` | Force offline mode for HuggingFace |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING) |

### ConfigManager

```python
from webis.core.config import ConfigManager

config = ConfigManager()
value = config.get("OPENAI_API_KEY")
```

Supports loading from `.env`, environment variables, and optional YAML
config files (via `WEBIS_CONFIG` env var).

---

For more information:
- [User Guide](user-guide.md) — Complete feature walkthrough
- [Plugin Development](plugins.md) — Create custom plugins
- [Quick Start](quickstart.md) — Get started in 5 minutes
