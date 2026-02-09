# API Reference

Complete API documentation for Webis.

## Core Classes

### WebisClient

Main client for interacting with Webis API.

```python
from webis import WebisClient

client = WebisClient(
    api_key="your_api_key",
    base_url="http://localhost:8000"
)
```

#### Methods

##### `run(query, sources=None, limit=10, **kwargs)`

Execute a pipeline to collect and process data.

**Parameters:**
- `query` (str): Search query or task description
- `sources` (list, optional): List of data sources to use
- `limit` (int, optional): Maximum number of results (default: 10)
- `rag_mode` (bool, optional): Enable RAG mode (default: False)
- `output` (str, optional): Output directory path

**Returns:** `PipelineResult`

**Example:**
```python
result = client.run(
    query="Latest AI news",
    sources=["duckduckgo", "gnews"],
    limit=10,
    rag_mode=True
)
```

##### `extract(file, task, schema=None, **kwargs)`

Extract structured data from a file.

**Parameters:**
- `file` (str): Path to the file
- `task` (str): Extraction task description
- `schema` (dict, optional): Custom JSON schema
- `output` (str, optional): Output file path

**Returns:** `ExtractionResult`

**Example:**
```python
result = client.extract(
    file="./report.pdf",
    task="Extract financial summary"
)
```

##### `get_status(task_id)`

Get the status of a running task.

**Parameters:**
- `task_id` (str): Task identifier

**Returns:** `TaskStatus`

**Example:**
```python
status = client.get_status("abc123")
print(status.status)  # "processing", "completed", etc.
```

### Pipeline

Main pipeline orchestrator.

```python
from webis.core.pipeline import Pipeline

pipeline = Pipeline()
```

#### Methods

##### `add_source(plugin_name, stage_name, **config)`

Add a data source plugin.

**Example:**
```python
pipeline.add_source(
    "duckduckgo",
    "search",
    max_results=10
)
```

##### `add_processor(plugin_name, stage_name, **config)`

Add a data processor plugin.

**Example:**
```python
pipeline.add_processor("html_cleaner", "clean")
pipeline.add_processor("chunking", "chunk", size=1000)
```

##### `add_extractor(plugin_name, stage_name, **config)`

Add an extractor plugin.

**Example:**
```python
pipeline.add_extractor("llm_extractor", "extract", model="gpt-4")
```

##### `run(context)`

Execute the pipeline.

**Example:**
```python
from webis.core.pipeline import PipelineContext

context = PipelineContext(query="Latest AI news")
result = pipeline.run(context)
```

### WebisDocument

Represents a document in the pipeline.

#### Properties

- `id` (str): Document identifier
- `content` (str): Document content
- `clean_content` (str, optional): Cleaned content
- `url` (str, optional): Source URL
- `title` (str, optional): Document title
- `doc_type` (DocumentType): Document type
- `status` (DocumentStatus): Document status
- `metadata` (DocumentMetadata, optional): Document metadata

#### Methods

##### `to_dict()`

Convert document to dictionary.

**Returns:** dict

**Example:**
```python
doc = WebisDocument(content="Hello, World!")
data = doc.to_dict()
```

##### `from_dict(data)`

Create document from dictionary.

**Parameters:**
- `data` (dict): Dictionary data

**Returns:** `WebisDocument`

**Example:**
```python
data = {"content": "Hello, World!"}
doc = WebisDocument.from_dict(data)
```

### StructuredResult

Represents extracted structured data.

#### Properties

- `data` (dict): Extracted data
- `schema` (dict, optional): Schema used
- `confidence` (float, optional): Confidence score
- `metadata` (dict, optional): Additional metadata

#### Methods

##### `to_json()`

Convert result to JSON string.

**Returns:** str

**Example:**
```python
result = StructuredResult(data={"title": "Example"})
json_str = result.to_json()
```

##### `to_file(path)`

Save result to a file.

**Parameters:**
- `path` (str): Output file path

**Example:**
```python
result = StructuredResult(data={"title": "Example"})
result.to_file("./result.json")
```

## Enums

### DocumentType

Document type enumeration.

```python
from webis.core.schema import DocumentType

types = [
    DocumentType.HTML,
    DocumentType.PDF,
    DocumentType.TEXT,
    DocumentType.MARKDOWN,
    DocumentType.IMAGE,
    DocumentType.AUDIO,
    DocumentType.VIDEO,
    DocumentType.JSON,
    DocumentType.UNKNOWN
]
```

### DocumentStatus

Document status enumeration.

```python
from webis.core.schema import DocumentStatus

statuses = [
    DocumentStatus.PENDING,
    DocumentStatus.PROCESSING,
    DocumentStatus.COMPLETED,
    DocumentStatus.FAILED,
    DocumentStatus.SKIPPED
]
```

## Exceptions

### WebisError

Base exception for all Webis errors.

```python
try:
    client.run("query")
except WebisError as e:
    print(f"Webis error: {e}")
```

### PluginNotFoundError

Raised when a requested plugin is not found.

### APIKeyNotFoundError

Raised when required API keys are missing.

### TaskExecutionError

Raised when a task execution fails.

## Utility Functions

### `get_config(key, default=None)`

Get configuration value.

```python
from webis.core.config import get_config

api_key = get_config("OPENAI_API_KEY")
```

### `set_config(key, value)`

Set configuration value.

```python
from webis.core.config import set_config

set_config("OPENAI_API_KEY", "your_key")
```

### `load_env()`

Load environment variables from `.env` file.

```python
from webis.core.config import load_env

load_env()
```

## CLI Commands

### `webis run`

Execute a pipeline.

```bash
webis run "query" [OPTIONS]

Options:
  --sources TEXT        Comma-separated list of sources
  --limit INTEGER       Maximum number of results
  --rag-mode          Enable RAG mode
  --output PATH         Output directory
  --config PATH         Pipeline configuration file
```

### `webis extract`

Extract data from a file.

```bash
webis extract FILE --task TASK [OPTIONS]

Options:
  --schema PATH        JSON schema file
  --output PATH        Output file
  --model TEXT         LLM model to use
```

### `webis visualizer`

Launch the web visualizer.

```bash
webis visualizer [OPTIONS]

Options:
  --port INTEGER        Port number (default: 8501)
  --host TEXT         Host address (default: localhost)
```

### `webis html-report`

Generate HTML report.

```bash
webis html-report RESULT [OPTIONS]

Options:
  --documents PATH    Path to documents.json
  --output PATH       Output file path
```

### `webis markdown-report`

Generate Markdown report.

```bash
webis markdown-report RAG_STORE [OPTIONS]

Options:
  --query TEXT        Report focus query
  --output PATH       Output file path
```

## Examples

### Basic Usage

```python
from webis import WebisClient
from webis.core.pipeline import Pipeline

# Using client
client = WebisClient()
result = client.run("Latest AI news")

# Using pipeline
pipeline = Pipeline()
pipeline.add_source("duckduckgo", "search")
context = PipelineContext(query="AI news")
result = pipeline.run(context)
```

### Advanced Usage

```python
from webis import WebisClient
from webis.core.schema import DocumentType, DocumentStatus

client = WebisClient()

# Create document
doc = WebisDocument(
    content="Example content",
    doc_type=DocumentType.TEXT,
    status=DocumentStatus.COMPLETED
)

# Extract with schema
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"}
    }
}

result = client.extract(
    file="./report.pdf",
    task="Extract key points",
    schema=schema
)
```

### Error Handling

```python
from webis import WebisClient
from webis.core.exceptions import (
    WebisError,
    PluginNotFoundError,
    APIKeyNotFoundError
)

client = WebisClient()

try:
    result = client.run("query")
except PluginNotFoundError as e:
    print(f"Plugin not found: {e.plugin_name}")
except APIKeyNotFoundError as e:
    print(f"Missing API key: {e.key}")
except WebisError as e:
    print(f"Error: {e}")
```

---

For more information:
- [User Guide](user-guide.md) - Complete feature walkthrough
- [Plugin Development](plugins.md) - Create custom plugins
- [Quick Start](quickstart.md) - Get started in 5 minutes