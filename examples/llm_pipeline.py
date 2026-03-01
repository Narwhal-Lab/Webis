"""
LLM Pipeline Demo for Webis v2.0
"""

import logging
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from webis.core.pipeline import Pipeline
from webis.plugins.sources import TavilySearchPlugin
from webis.plugins.processors import HtmlFetcherPlugin, HtmlCleanerPlugin, SummarizerPlugin

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def main():
    # 1. Create Pipeline
    pipeline = Pipeline()
    
    # 2. Register and Add Source
    search = TavilySearchPlugin(config={"max_results": 2})
    pipeline.registry.register(search)
    pipeline.add_source(search.name)
    
    # 3. Register and Add Processors
    fetcher = HtmlFetcherPlugin()
    cleaner = HtmlCleanerPlugin()
    pipeline.registry.register(fetcher)
    pipeline.registry.register(cleaner)
    
    pipeline.add_processor(fetcher.name)
    pipeline.add_processor(cleaner.name)
    
    # Add Summarizer (requires OPENAI_API_KEY or similar)
    # We use a try-except block to handle missing keys gracefully in demo
    try:
        summarizer = SummarizerPlugin(config={"model": "gpt-4o-mini"})
        pipeline.registry.register(summarizer)
        pipeline.add_processor(summarizer.name)
    except Exception as e:
        print(f"Skipping summarizer: {e}")
    
    # 4. Run Pipeline
    query = "Latest advancements in AI agents 2024"
    print(f"Running pipeline for query: '{query}'...")
    
    result = pipeline.run(query)
    
    # 5. Display Results
    print(f"\nFound {result.document_count} results:\n")
    for i, doc in enumerate(result.documents, 1):
        print(f"--- Result {i} ---")
        print(f"Title: {doc.meta.title}")
        print(f"URL: {doc.meta.url}")
        
        summary = doc.meta.custom.get("summary")
        if summary:
            print(f"Summary: {summary}")
        else:
            print(f"Snippet: {doc.content[:200]}...")
            
        print("-" * 50)

if __name__ == "__main__":
    main()
