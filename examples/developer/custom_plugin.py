"""
Custom Plugin Development Example

This example demonstrates how to create custom plugins for Webis.
"""
import asyncio
from typing import List, Dict, Any
from webis.core.plugin import BaseSourcePlugin, BaseProcessorPlugin, BaseExtractorPlugin
from webis.core.schema import WebisDocument, StructuredResult, DocumentType
from webis.core.pipeline import Pipeline


class MockNewsPlugin(BaseSourcePlugin):
    """Mock news source plugin for demonstration"""

    name = "mock_news"
    description = "Mock news source for testing"
    version = "1.0.0"

    async def search(self, query: str, config: Dict[str, Any]) -> List[WebisDocument]:
        """Mock search implementation"""
        mock_articles = [
            {
                "title": f"Breaking: {query} breakthrough announced",
                "content": f"Scientists have made a significant breakthrough in {query}. The new discovery promises to revolutionize the field.",
                "url": "https://news.example.com/article1",
                "published_at": "2024-01-15",
                "source": "Tech News Daily"
            },
            {
                "title": f"New study on {query} shows promising results",
                "content": f"A recent study published in Nature reveals new insights about {query}. Researchers are excited about the implications.",
                "url": "https://news.example.com/article2",
                "published_at": "2024-01-14",
                "source": "Science Magazine"
            }
        ]

        documents = []
        max_results = config.get("max_results", 5)

        for article in mock_articles[:max_results]:
            doc = WebisDocument(
                content=article["content"],
                url=article["url"],
                title=article["title"],
                doc_type=DocumentType.HTML,
                metadata={
                    "published_at": article["published_at"],
                    "source": article["source"],
                    "source_plugin": self.name
                }
            )
            documents.append(doc)

        return documents


class ContentSummarizerPlugin(BaseProcessorPlugin):
    """Content summarizer processor plugin"""

    name = "content_summarizer"
    description = "Summarizes document content"
    version = "1.0.0"

    async def process(self, documents: List[WebisDocument], config: Dict[str, Any]) -> List[WebisDocument]:
        """Process documents by summarizing content"""
        processed_docs = []

        for doc in documents:
            # Simple mock summarization
            summary = self._generate_summary(doc.content)

            # Create processed document
            processed_doc = doc.model_copy()
            processed_doc.clean_content = summary
            processed_doc.metadata = processed_doc.metadata or {}
            processed_doc.metadata["summary"] = summary
            processed_doc.metadata["summarized_by"] = self.name

            processed_docs.append(processed_doc)

        return processed_docs

    def _generate_summary(self, content: str) -> str:
        """Generate a simple summary"""
        words = content.split()
        if len(words) > 100:
            return " ".join(words[:100]) + "..."
        return content


class KeywordExtractorPlugin(BaseExtractorPlugin):
    """Keyword extractor plugin"""

    name = "keyword_extractor"
    description = "Extracts keywords from text"
    version = "1.0.0"

    async def extract(self, documents: List[WebisDocument], config: Dict[str, Any]) -> StructuredResult:
        """Extract keywords from documents"""
        all_keywords = []

        for doc in documents:
            keywords = self._extract_keywords(doc.content)

            all_keywords.append({
                "document_id": doc.id,
                "keywords": keywords,
                "title": doc.title
            })

        return StructuredResult(
            data={"keywords": all_keywords},
            schema=self.get_schema()
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        words = text.lower().split()
        word_freq = {}

        # Count word frequencies
        for word in words:
            # Simple filtering
            if len(word) > 3 and word.isalpha():
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:5]]

    def get_schema(self) -> Dict[str, Any]:
        """Get extraction schema"""
        return {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "document_id": {"type": "string"},
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "title": {"type": "string"}
                        }
                    }
                }
            }
        }


async def demonstrate_custom_plugins():
    """Demonstrate custom plugin usage"""

    print("=" * 60)
    print("Custom Plugin Development Example")
    print("=" * 60)

    # Create pipeline with custom plugins
    pipeline = Pipeline()
    pipeline.add_source("mock_news", "search", max_results=3)
    pipeline.add_processor("content_summarizer", "summarize")
    pipeline.add_extractor("keyword_extractor", "extract_keywords")

    # Define context
    context = PipelineContext(query="artificial intelligence")

    print("\n1. Running Pipeline with Custom Plugins")
    print("-" * 60)

    result = await pipeline.run(context)

    print(f"Processed {len(result.documents)} documents")

    # Display results
    print("\n2. Processed Documents")
    print("-" * 60)

    for i, doc in enumerate(result.documents, 1):
        print(f"\nDocument {i}:")
        print(f"  Title: {doc.title}")
        print(f"  Source: {doc.metadata.get('source')}")
        print(f"  Published: {doc.metadata.get('published_at')}")
        print(f"  Summary: {doc.metadata.get('summary', 'N/A')}")

    # Display extracted keywords
    print("\n3. Extracted Keywords")
    print("-" * 60)

    if result.structured_result and "keywords" in result.structured_result.data:
        for keyword_data in result.structured_result.data["keywords"]:
            print(f"\nDocument: {keyword_data['title']}")
            print(f"  Keywords: {', '.join(keyword_data['keywords'])}")


async def show_plugin_configuration():
    """Show how to configure custom plugins"""
    print("\n4. Plugin Configuration")
    print("-" * 60)

    # Create pipeline with configuration
    pipeline = Pipeline()
    pipeline.add_source(
        "mock_news",
        "search",
        max_results=2,  # Configuration
        timeout=30
    )
    pipeline.add_processor(
        "content_summarizer",
        "summarize",
        max_summary_length=200
    )

    context = PipelineContext(query="machine learning")
    result = await pipeline.run(context)

    print(f"Configured pipeline completed with {len(result.documents)} documents")


if __name__ == "__main__":
    # Register custom plugins (in a real scenario, these would be in your package)
    # For demonstration, we'll run directly
    asyncio.run(demonstrate_custom_plugins())
    asyncio.run(show_plugin_configuration())