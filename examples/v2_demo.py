"""
Webis v2.0 Demo Script
"""

import logging
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from webis.core.plugin import get_default_registry
from webis.plugins.sources import (
    GNewsPlugin, 
    GitHubSearchPlugin,
    HackerNewsPlugin
)
from webis.plugins.processors import HtmlFetcherPlugin, HtmlCleanerPlugin

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("webis_demo")

def main():
    logger.info("Starting Webis v2.0 Demo")
    
    # 1. Initialize Registry
    registry = get_default_registry()
    
    # 2. Register Plugins
    registry.register_class(GNewsPlugin)
    registry.register_class(GitHubSearchPlugin)
    registry.register_class(HackerNewsPlugin)
    registry.register_class(HtmlFetcherPlugin)
    registry.register_class(HtmlCleanerPlugin)
    
    logger.info(f"Registered Sources: {registry.list_sources()}")
    logger.info(f"Registered Processors: {registry.list_processors()}")
    
    # 3. Run a simple pipeline
    source = registry.get_source("hackernews")
    fetcher = registry.get_processor("html_fetcher")
    cleaner = registry.get_processor("html_cleaner")
    
    query = "python programming language"
    logger.info(f"Searching for: '{query}' using {source.name}")
    
    try:
        # Fetch
        docs = list(source.fetch(query, limit=3))
        logger.info(f"Found {len(docs)} documents")
        
        for i, doc in enumerate(docs):
            logger.info(f"Processing Document {i+1}: {doc.meta.title}")
            
            # Fetch Content
            doc = fetcher.process(doc)
            logger.info(f"  - Fetched content length: {len(doc.content) if doc.content else 0}")
            
            # Clean Content
            doc = cleaner.process(doc)
            logger.info(f"  - Cleaned content length: {len(doc.clean_content) if doc.clean_content else 0}")
            
            # Show snippet
            snippet = doc.clean_content[:200].replace("\n", " ") if doc.clean_content else "No content"
            logger.info(f"  - Snippet: {snippet}...")
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
