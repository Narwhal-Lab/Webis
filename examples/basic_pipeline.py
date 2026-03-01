"""
Basic Pipeline Demo for Webis v2.0
"""

import logging
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from webis.core.pipeline import Pipeline
from webis.plugins.sources import TavilySearchPlugin
from webis.plugins.processors import HtmlFetcherPlugin, HtmlCleanerPlugin

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def main():
    # 1. Create Pipeline
    pipeline = Pipeline()
    
    # 2. Register and Add Source
    search_plugin = TavilySearchPlugin(config={"max_results": 3})
    pipeline.registry.register(search_plugin)
    pipeline.add_source(search_plugin.name)
    
    # 3. Register and Add Processors
    fetcher = HtmlFetcherPlugin()
    cleaner = HtmlCleanerPlugin()
    
    pipeline.registry.register(fetcher)
    pipeline.registry.register(cleaner)
    
    pipeline.add_processor(fetcher.name)
    pipeline.add_processor(cleaner.name)
    
    # 4. Run Pipeline
    query = "LLM agent architecture"
    print(f"Running pipeline for query: '{query}'...")
    
    result = pipeline.run(query)
    
    # 5. Display Results
    print(f"\nFound {result.document_count} results:\n")
    for i, doc in enumerate(result.documents, 1):
        print(f"--- Result {i} ---")
        print(f"Title: {doc.meta.title}")
        print(f"URL: {doc.meta.url}")
        
        content_to_show = doc.clean_content if doc.clean_content else doc.content
        print(f"Content Length: {len(content_to_show)} chars")
        print(f"Snippet: {content_to_show[:200]}...")
        print("-" * 50)

if __name__ == "__main__":
    main()
