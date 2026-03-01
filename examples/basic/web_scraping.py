"""
Basic Web Scraping Example

This example demonstrates how to use Webis to collect data from the web.
"""
import asyncio
from webis import WebisClient
from webis.core.pipeline import Pipeline, PipelineContext


async def main():
    """Basic web scraping example"""

    # Initialize client
    client = WebisClient()

    print("=" * 50)
    print("Basic Web Scraping Example")
    print("=" * 50)

    # Example 1: Simple search
    print("\n1. Simple Search")
    print("-" * 50)

    result = await client.run(
        query="Latest artificial intelligence news",
        sources=["hackernews"],
        limit=3
    )

    print(f"Found {len(result.documents)} documents")
    for i, doc in enumerate(result.documents, 1):
        print(f"\nDocument {i}:")
        print(f"  Title: {doc.title}")
        print(f"  URL: {doc.url}")
        print(f"  Type: {doc.doc_type}")

    # Example 2: Multiple sources
    print("\n2. Multiple Sources")
    print("-" * 50)

    result = await client.run(
        query="Python programming tutorials",
        sources=["github", "stackoverflow"],
        limit=5
    )

    print(f"Found {len(result.documents)} documents from multiple sources")
    for doc in result.documents:
        print(f"  [{doc.source_plugin}] {doc.title}")

    # Example 3: With RAG mode
    print("\n3. RAG Mode (Knowledge Base)")
    print("-" * 50)

    result = await client.run(
        query="Machine learning research papers",
        sources=["semantic_scholar"],
        limit=5,
        rag_mode=True
    )

    print(f"Created knowledge base with {len(result.documents)} documents")
    print(f"Vector store: {result.metadata.get('vector_store_path')}")

    # Example 4: Custom output directory
    print("\n4. Custom Output Directory")
    print("-" * 50)

    result = await client.run(
        query="Recent tech news",
        sources=["gnews", "hackernews"],
        limit=10,
        output="./output/tech_news"
    )

    print(f"Results saved to: {result.metadata.get('output_path')}")

    # Example 5: Using Pipeline directly
    print("\n5. Advanced Pipeline Configuration")
    print("-" * 50)

    pipeline = Pipeline()
    pipeline.add_source("hackernews", "search", max_results=5)
    pipeline.add_processor("html_cleaner", "clean")
    pipeline.add_extractor("llm_extractor", "extract", model="gpt-3.5")

    context = PipelineContext(
        query="Natural language processing techniques"
    )

    result = await pipeline.run(context)

    print(f"Pipeline completed with {len(result.documents)} documents")
    print(f"Extraction results: {result.structured_result.data}")


if __name__ == "__main__":
    asyncio.run(main())