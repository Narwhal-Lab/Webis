# Plugin Development Guide

Learn how to create custom plugins for Webis v2.

## Overview

Webis uses a **plugin architecture** with six plugin base types:

| Type | Base Class | Purpose |
|------|-----------|---------|
| **Source** | `SourcePlugin` | Fetch data from external sources |
| **Processor** | `ProcessorPlugin` | Transform and clean documents |
| **Extractor** | `ExtractorPlugin` | Extract structured information |
| **Output** | `OutputPlugin` | Generate output artifacts (reports, etc.) |
| **Model** | `ModelPlugin` | ML model wrappers |
| **Notification** | `NotificationPlugin` | Alert/notification integrations |

Plugins are registered via the singleton `PluginRegistry` and discovered
automatically when their module is imported.

## Registered Plugins (v2.0)

### Source Plugins (10)

| Name | Class | API Key | Description |
|------|-------|---------|-------------|
| `tavily_search` | `TavilySearchPlugin` | `TAVILY_API_KEY` | Tavily AI search |
| `bocha_search` | `BochaSearchPlugin` | `BOCHA_API_KEY` | Bocha search API |
| `exa_firecrawl_crawler` | `ExaFirecrawlCrawler` | `EXA_API_KEY` | Exa + Firecrawl |
| `serper_search` | `SerperSearchPlugin` | `SERPER_API_KEY` | Serper Google search |
| `serpapi` | `SerpApiPlugin` | `SERPAPI_API_KEY` | SerpAPI |
| `bright_data` | `BrightDataPlugin` | `BRIGHTDATA_API_TOKEN` | Bright Data scraping |
| `github` | `GitHubSearchPlugin` | `GITHUB_TOKEN` | GitHub search |
| `gnews` | `GNewsPlugin` | `GNEWS_API_KEY` | Google News |
| `hackernews` | `HackerNewsPlugin` | *(none)* | Hacker News |
| `semantic_scholar` | `SemanticScholarPlugin` | *(none)* | Academic papers |

### Processor Plugins (5)

| Name | Class | Description |
|------|-------|-------------|
| `html_cleaner` | `HTMLCleanerPlugin` | HTML → clean text |
| `html_fetcher` | `HtmlFetcherPlugin` | Fetch full HTML from URL |
| `pdf_extractor` | `PDFPlugin` | PDF text extraction |
| `document_parser` | `DocumentParsePlugin` | Generic document parsing |
| `video_processor` | `VideoPlugin` | Video processing |

### Extractor Plugins (1)

| Name | Class | Description |
|------|-------|-------------|
| `llm_extractor` | `LLMExtractorPlugin` | LLM-based structured extraction |

### Output Plugins (1)

| Name | Class | Description |
|------|-------|-------------|
| `html_report` | `HtmlReportPlugin` | 3-agent HTML report pipeline |

### Additional (not auto-registered)

- `EmbeddingGemmaPlugin` — instantiated on demand for RAG embedding
- `baidu_search`, `smart_fetcher`, `mock_source` — available but not auto-loaded
- `dingtalk_plugin`, `slack_plugin` — notification plugins (manual registration)

## Plugin Interface

### SourcePlugin

All source plugins must implement the `fetch()` method:

```python
from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, PipelineContext
from typing import Iterator

class MySearchPlugin(SourcePlugin):
    """Custom search source plugin."""

    name = "my_search"
    description = "My custom search source"
    source_type = "web"              # web | api | file | stream
    supports_pagination = False
    supports_incremental = False
    max_results_per_call = 20

    def fetch(
        self,
        query: str,
        limit: int = 10,
        context: PipelineContext = None,
        **kwargs,
    ) -> Iterator[WebisDocument]:
        """
        Fetch documents matching the query.

        Args:
            query: Search query string
            limit: Maximum results to return
            context: Pipeline context (shared state)
            **kwargs: Additional parameters

        Yields:
            WebisDocument instances
        """
        # Your search logic here
        import requests

        resp = requests.get(
            "https://api.example.com/search",
            params={"q": query, "limit": limit},
            headers={"Authorization": f"Bearer {self._get_api_key()}"},
        )

        for item in resp.json().get("results", []):
            yield WebisDocument(
                content=item["content"],
                doc_type="html",
                meta={
                    "url": item["url"],
                    "title": item.get("title"),
                    "source_plugin": self.name,
                },
            )

    def _get_api_key(self) -> str:
        import os
        return os.environ.get("MY_SEARCH_API_KEY", "")
```

### ProcessorPlugin

Processor plugins transform documents:

```python
from webis.core.plugin import ProcessorPlugin
from webis.core.schema import WebisDocument, PipelineContext
from typing import List

class MyCleanerPlugin(ProcessorPlugin):
    """Custom document cleaner."""

    name = "my_cleaner"
    description = "Custom content cleaner"

    def process(
        self,
        documents: List[WebisDocument],
        context: PipelineContext = None,
        **kwargs,
    ) -> List[WebisDocument]:
        """
        Process and return cleaned documents.

        Args:
            documents: Input documents
            context: Pipeline context

        Returns:
            Processed documents
        """
        result = []
        for doc in documents:
            doc.clean_content = self._clean(doc.content)
            result.append(doc)
        return result

    def _clean(self, text: str) -> str:
        import re
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
```

### ExtractorPlugin

Extractor plugins produce structured output:

```python
from webis.core.plugin import ExtractorPlugin
from webis.core.schema import WebisDocument, StructuredResult, PipelineContext
from typing import List

class MyExtractorPlugin(ExtractorPlugin):
    """Custom structured extractor."""

    name = "my_extractor"
    description = "Extract entities from documents"

    def extract(
        self,
        documents: List[WebisDocument],
        context: PipelineContext = None,
        **kwargs,
    ) -> StructuredResult:
        """
        Extract structured data from documents.

        Args:
            documents: Input documents
            context: Pipeline context

        Returns:
            StructuredResult with extracted data
        """
        entities = []
        for doc in documents:
            entities.extend(self._find_entities(doc.content))

        return StructuredResult(
            data={"entities": entities},
            is_valid=True,
        )

    def _find_entities(self, text: str) -> list:
        # Your extraction logic
        return []
```

### OutputPlugin

Output plugins generate final artifacts:

```python
from webis.core.plugin import OutputPlugin

class MyReportPlugin(OutputPlugin):
    """Custom report generator."""

    name = "my_report"
    description = "Generate custom report"

    def save(self, **kwargs) -> bool:
        """
        Generate and save the output artifact.

        Returns:
            True on success, False otherwise.
        """
        rag_store_path = kwargs.get("rag_store_path")
        output_dir = kwargs.get("output_dir")
        query = kwargs.get("query", "")

        # Generate your report
        report_content = self._generate(rag_store_path, query)

        # Save to file
        import os
        output_path = os.path.join(output_dir, "report.txt")
        with open(output_path, "w") as f:
            f.write(report_content)

        return True
```

## Plugin Registration

### Automatic Registration

Add your plugin to the appropriate `__init__.py` so it's imported at
startup:

```python
# src/webis/plugins/sources/__init__.py
from .my_search_plugin import MySearchPlugin  # auto-registers on import
```

### Manual Registration

```python
from webis.core.plugin import get_default_registry

registry = get_default_registry()
registry.register_source(MySearchPlugin())
```

### Entry Points (pyproject.toml)

For installable plugins, use entry points:

```toml
[project.entry-points."webis.plugins.sources"]
my_search = "my_package.plugins:MySearchPlugin"
```

## Using the LLM Router in Plugins

Plugins can leverage the shared LLM router for AI-powered processing:

```python
from webis.core.llm.base import get_default_router, LLMResponse

router = get_default_router()

response: LLMResponse = router.chat(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Classify this text: ..."},
    ],
    temperature=0.3,
    max_tokens=500,
    json_mode=True,
)

result = json.loads(response.content)
```

The router handles:
- Automatic fallback to backup models
- Response caching (SHA256-keyed)
- Token and cost tracking
- Provider abstraction (OpenAI, DeepSeek, SiliconFlow, Anthropic)

## Testing Plugins

### Unit Test

```python
import pytest
from webis.core.schema import WebisDocument, DocumentType

def test_my_plugin_process():
    from my_package.plugins import MyCleanerPlugin

    plugin = MyCleanerPlugin()
    docs = [
        WebisDocument(
            content="<p>Hello <b>world</b></p>",
            doc_type=DocumentType.HTML,
        )
    ]

    result = plugin.process(docs)
    assert len(result) == 1
    assert result[0].clean_content == "Hello world"
```

### Integration Test with Pipeline

```python
import pytest
from webis.core.plugin import get_default_registry

def test_plugin_registered():
    registry = get_default_registry()
    plugin = registry.get_source("my_search")
    assert plugin is not None
    assert plugin.name == "my_search"
```

## Best Practices

1. **Implement `fetch()` as a generator** — use `yield` for memory efficiency
2. **Handle errors gracefully** — return empty results rather than crashing
3. **Respect rate limits** — use `tenacity` or `time.sleep()` for API calls
4. **Log meaningfully** — use `logging.getLogger(__name__)`
5. **Use environment variables** for API keys — never hardcode credentials
6. **Add metadata** — populate `DocumentMetadata` (url, title, source_plugin)
7. **Version your plugin** — maintain compatibility with Webis core

---

For more information:
- [API Reference](api.md) — Core classes and CLI reference
- [User Guide](user-guide.md) — Complete feature walkthrough
- [Quick Start](quickstart.md) — Get started in 5 minutes
