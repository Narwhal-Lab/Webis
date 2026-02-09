# Plugin Development Guide

Learn how to create custom plugins for Webis.

## Overview

Webis is built on a plugin architecture that allows you to extend its functionality. There are three main types of plugins:

1. **Source Plugins** - Fetch data from various sources
2. **Processor Plugins** - Transform and clean data
3. **Extractor Plugins** - Extract structured information

## Plugin Structure

### Basic Plugin Template

Create a plugin by extending the base plugin class:

```python
from webis.core.plugin import BasePlugin, PluginConfig
from typing import Dict, Any, List, Optional
from webis.core.schema import WebisDocument

class MyPlugin(BasePlugin):
    name = "my_plugin"
    description = "My custom plugin"
    version = "1.0.0"
    author = "Your Name"
    email = "your@email.com"

    class Config(PluginConfig):
        param1: str = "default_value"
        param2: int = 10

    def setup(self):
        """Initialize plugin resources"""
        pass

    def run(self, input_data: Any) -> Any:
        """Execute plugin logic"""
        pass

    def cleanup(self):
        """Clean up plugin resources"""
        pass
```

### Plugin Registration

Plugins are automatically discovered through entry points. Add this to `pyproject.toml`:

```toml
[project.entry-points."webis.plugins.sources"]
my_plugin = "my_package.plugins:MySourcePlugin"

[project.entry-points."webis.plugins.processors"]
my_plugin = "my_package.plugins:MyProcessorPlugin"

[project.entry-points."webis.plugins.extractors"]
my_plugin = "my_package.plugins:MyExtractorPlugin"
```

## Source Plugins

Source plugins fetch data from external sources.

### Base Source Plugin

```python
from webis.core.plugin import BaseSourcePlugin
from typing import List, Optional
from webis.core.schema import WebisDocument, DocumentType

class MySourcePlugin(BaseSourcePlugin):
    name = "my_source"
    description = "My custom data source"

    async def search(self, query: str, config: Dict[str, Any]) -> List[WebisDocument]:
        """
        Search for documents using the plugin

        Args:
            query: Search query
            config: Plugin configuration

        Returns:
            List of WebisDocument objects
        """
        # Implement your search logic here
        results = []

        # Example: Fetch from API
        response = requests.get(
            "https://api.example.com/search",
            params={"q": query}
        )

        # Convert to WebisDocument
        for item in response.json()["results"]:
            doc = WebisDocument(
                content=item["content"],
                url=item["url"],
                title=item.get("title"),
                doc_type=DocumentType.HTML,
                source_plugin=self.name
            )
            results.append(doc)

        return results

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize plugin configuration"""
        # Set defaults
        config.setdefault("max_results", 10)

        # Validate parameters
        if config["max_results"] < 1:
            raise ValueError("max_results must be > 0")

        return config
```

### Example: Custom News Source

```python
from webis.core.plugin import BaseSourcePlugin
from typing import List
from webis.core.schema import WebisDocument, DocumentType

class NewsSourcePlugin(BaseSourcePlugin):
    name = "custom_news"
    description = "Custom news source"

    async def search(self, query: str, config: Dict[str, Any]) -> List[WebisDocument]:
        # Mock news data
        mock_news = [
            {
                "title": f"News about {query}",
                "content": "Sample news content...",
                "url": "https://example.com/news/1",
                "published_at": "2024-01-01"
            },
            # ... more news items
        ]

        results = []
        for item in mock_news[:config["max_results"]]:
            doc = WebisDocument(
                content=item["content"],
                url=item["url"],
                title=item["title"],
                doc_type=DocumentType.HTML,
                metadata={
                    "published_at": item["published_at"]
                },
                source_plugin=self.name
            )
            results.append(doc)

        return results
```

## Processor Plugins

Processor plugins transform and clean data.

### Base Processor Plugin

```python
from webis.core.plugin import BaseProcessorPlugin
from typing import List
from webis.core.schema import WebisDocument

class MyProcessorPlugin(BaseProcessorPlugin):
    name = "my_processor"
    description = "My custom processor"

    async def process(self, documents: List[WebisDocument], config: Dict[str, Any]) -> List[WebisDocument]:
        """
        Process a list of documents

        Args:
            documents: Input documents
            config: Plugin configuration

        Returns:
            Processed documents
        """
        processed = []

        for doc in documents:
            # Process document content
            processed_content = self._clean_content(doc.content)

            # Create processed document
            processed_doc = doc.model_copy()
            processed_doc.clean_content = processed_content
            processed_doc.metadata = processed_doc.metadata or {}
            processed_doc.metadata["processed_by"] = self.name

            processed.append(processed_doc)

        return processed

    def _clean_content(self, content: str) -> str:
        """Clean document content"""
        # Implement your cleaning logic
        content = content.strip()
        content = " ".join(content.split())  # Remove extra whitespace
        return content
```

### Example: Content Cleaner

```python
from webis.core.plugin import BaseProcessorPlugin
from typing import List
from webis.core.schema import WebisDocument
import re

class ContentCleanerPlugin(BaseProcessorPlugin):
    name = "content_cleaner"
    description = "Clean HTML and remove unwanted content"

    async def process(self, documents: List[WebisDocument], config: Dict[str, Any]) -> List[WebisDocument]:
        processed = []

        for doc in documents:
            # Remove HTML tags
            clean_content = re.sub(r'<[^>]+>', '', doc.content)

            # Remove extra whitespace
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()

            # Update document
            processed_doc = doc.model_copy()
            processed_doc.clean_content = clean_content
            processed_doc.metadata = processed_doc.metadata or {}
            processed_doc.metadata["cleaned_at"] = "2024-01-01T00:00:00Z"

            processed.append(processed_doc)

        return processed
```

## Extractor Plugins

Extractor plugins extract structured information from documents.

### Base Extractor Plugin

```python
from webis.core.plugin import BaseExtractorPlugin
from typing import List, Dict, Any
from webis.core.schema import WebisDocument, StructuredResult

class MyExtractorPlugin(BaseExtractorPlugin):
    name = "my_extractor"
    description = "My custom extractor"

    async def extract(self, documents: List[WebisDocument], config: Dict[str, Any]) -> StructuredResult:
        """
        Extract structured information from documents

        Args:
            documents: Input documents
            config: Plugin configuration

        Returns:
            StructuredResult containing extracted data
        """
        data = {}

        for doc in documents:
            # Extract information
            extracted = self._extract_from_document(doc, config)

            # Merge data
            self._merge_data(data, extracted)

        return StructuredResult(
            data=data,
            schema=self.get_schema()
        )

    def _extract_from_document(self, doc: WebisDocument, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract from a single document"""
        # Implement your extraction logic
        return {
            "title": self._extract_title(doc),
            "key_points": self._extract_key_points(doc)
        }

    def get_schema(self) -> Dict[str, Any]:
        """Get the extraction schema"""
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }
```

### Example: Entity Extractor

```python
from webis.core.plugin import BaseExtractorPlugin
from typing import List, Dict, Any
from webis.core.schema import WebisDocument, StructuredResult

class EntityExtractorPlugin(BaseExtractorPlugin):
    name = "entity_extractor"
    description = "Extract entities from text"

    async def extract(self, documents: List[WebisDocument], config: Dict[str, Any]) -> StructuredResult:
        entities = []

        for doc in documents:
            # Simple entity extraction (mock implementation)
            entities.append({
                "document_id": doc.id,
                "entities": self._find_entities(doc.content),
                "metadata": {
                    "extractor": self.name,
                    "config": config
                }
            })

        return StructuredResult(
            data={"entities": entities},
            schema=self.get_schema()
        )

    def _find_entities(self, text: str) -> List[Dict[str, Any]]:
        """Find entities in text"""
        # Simple pattern matching
        entities = []

        # Find names (simplified)
        words = text.split()
        for i, word in enumerate(words):
            if word.istitle() and len(word) > 3:
                entities.append({
                    "text": word,
                    "type": "NAME",
                    "position": i
                })

        return entities

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "document_id": {"type": "string"},
                            "entities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "type": {"type": "string"},
                                        "position": {"type": "integer"}
                                    }
                                }
                            },
                            "metadata": {"type": "object"}
                        }
                    }
                }
            }
        }
```

## Plugin Configuration

### PluginConfig Schema

Define your plugin configuration using Pydantic:

```python
from pydantic import BaseModel, Field
from typing import Optional

class MyPluginConfig(BaseModel):
    api_key: str = Field(..., description="API key for the service")
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    enable_cache: bool = Field(True, description="Enable caching")

    class Config:
        schema_extra = {
            "example": {
                "api_key": "your_api_key",
                "timeout": 30,
                "max_retries": 3,
                "enable_cache": True
            }
        }
```

### Configuration Validation

```python
class MyPlugin(BasePlugin):
    class Config(PluginConfig):
        api_key: str
        timeout: int = 30
        max_retries: int = 3

    def setup(self):
        # Validate configuration
        if not self.config.api_key:
            raise ValueError("API key is required")

        # Initialize resources
        self.client = self._create_client()

    def _create_client(self):
        # Create API client with config
        return APIClient(
            api_key=self.config.api_key,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )
```

## Plugin Testing

### Writing Tests

```python
import pytest
from unittest.mock import Mock
from webis.core.plugin import MyPlugin
from webis.core.schema import WebisDocument

@pytest.fixture
def plugin():
    return MyPlugin()

@pytest.fixture
def sample_document():
    return WebisDocument(
        content="Sample document content",
        doc_type="text",
        metadata={"source": "test"}
    )

def test_plugin_initialization(plugin):
    """Test plugin initialization"""
    assert plugin.name == "my_plugin"
    assert plugin.version == "1.0.0"

def test_plugin_setup(plugin):
    """Test plugin setup"""
    plugin.setup()
    assert hasattr(plugin, 'client')

async def test_plugin_process(plugin, sample_document):
    """Test document processing"""
    result = await plugin.process([sample_document], {})

    assert len(result) == 1
    assert result[0].content == "processed content"

def test_config_validation():
    """Test configuration validation"""
    # Valid config
    config = {"api_key": "test_key", "timeout": 30}
    validated = plugin.validate_config(config)
    assert validated["timeout"] == 30

    # Invalid config
    with pytest.raises(ValueError):
        plugin.validate_config({"api_key": ""})
```

### Integration Tests

```python
import pytest
from webis.core.pipeline import Pipeline

@pytest.mark.asyncio
async def test_plugin_integration():
    """Test plugin integration with pipeline"""
    pipeline = Pipeline()
    pipeline.add_source("my_plugin", "source")
    pipeline.add_processor("my_processor", "process")

    context = PipelineContext(query="test query")
    result = await pipeline.run(context)

    assert len(result.documents) > 0
    assert all(doc.source_plugin == "my_plugin" for doc in result.documents)
```

## Plugin Best Practices

### 1. Follow the Interface

Always implement the required methods:
- `setup()` - Initialize resources
- `run()` - Main logic
- `cleanup()` - Release resources

### 2. Handle Errors Gracefully

```python
async def search(self, query: str, config: Dict[str, Any]) -> List[WebisDocument]:
    try:
        # Your implementation
        pass
    except Exception as e:
        # Log error
        self.logger.error(f"Error searching: {e}")

        # Return empty list or raise appropriate exception
        return []
```

### 3. Use Async/await

All plugin methods should be async:

```python
async def process(self, documents: List[WebisDocument], config: Dict[str, Any]) -> List[WebisDocument]:
    # Async implementation
    await asyncio.sleep(1)  # Example async operation
    return documents
```

### 4. Add Proper Logging

```python
import logging

logger = logging.getLogger(__name__)

class MyPlugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    def setup(self):
        self.logger.info("Initializing my plugin")
```

### 5. Document Your Plugin

```python
class MyPlugin(BasePlugin):
    """
    A plugin that extracts data from external sources.

    This plugin supports the following features:
    - Search functionality
    - Filtering and sorting
    - Pagination
    """

    def get_documentation(self) -> str:
        return """
        # My Plugin Documentation

        ## Features
        - Feature 1: Description
        - Feature 2: Description

        ## Configuration
        - `param1`: Description (required)
        - `param2`: Description (optional, default: 10)

        ## Example
        ```python
        plugin = MyPlugin()
        plugin.setup()
        results = await plugin.search("query", {"param1": "value"})
        ```
        """
```

### 6. Version Your Plugins

```python
class MyPlugin(BasePlugin):
    name = "my_plugin"
    version = "1.0.0"
    api_version = "v1"

    def check_compatibility(self):
        """Check compatibility with Webis version"""
        from webis import __version__
        required_version = "2.0.0"

        if version.parse(__version__) < version.parse(required_version):
            raise CompatibilityError(
                f"Plugin requires Webis >= {required_version}, got {__version__}"
            )
```

---

For more information:
- [API Reference](api.md) - Complete API documentation
- [User Guide](user-guide.md) - Complete feature walkthrough
- [Quick Start](quickstart.md) - Get started in 5 minutes