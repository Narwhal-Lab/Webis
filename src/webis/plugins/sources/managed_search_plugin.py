"""
Managed Search Plugins for Webis.

This module contains search plugins that rely on managed third-party APIs
(Tavily, Bocha) rather than direct scraping.
"""

import logging
import os
import requests
from typing import Iterator, Optional, Dict, Any, List

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext

logger = logging.getLogger(__name__)


class TavilySearchPlugin(SourcePlugin):
    """
    Search using Tavily API (https://tavily.com).
    Optimized for LLM agents with clean content extraction.
    """

    name = "tavily_search"
    description = "AI-optimized web search using Tavily. Best for complex questions and research."
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = os.environ.get("TAVILY_API_KEY")

    def fetch(
        self,
        query: str,
        limit: int = 10,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:
        
        if not self.api_key:
            self.api_key = os.environ.get("TAVILY_API_KEY")
            
        if not self.api_key:
            logger.error("TAVILY_API_KEY not found in environment variables.")
            return

        logger.info(f"[Tavily] Searching: {query} (limit={limit})")
        
        url = "https://api.tavily.com/search"
        
        # Tavily API parameters
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": kwargs.get("search_depth", "basic"),  # or "advanced"
            "include_answer": False,
            "include_images": False,
            "include_raw_content": True,
            "max_results": limit,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            
            for result in results:
                # Prefer raw HTML content for better analysis/filtering
                # Fallback to snippet if raw not available
                content = result.get("raw_content")
                if not content:
                    content = result.get("content", "")

                yield WebisDocument(
                    content=content,
                    doc_type=DocumentType.HTML, # Treated as text/html for pipeline compatibility
                    meta=DocumentMetadata(
                        url=result.get("url"),
                        title=result.get("title"),
                        source_plugin=self.name,
                        custom={
                            "score": result.get("score"),
                            "published_date": result.get("published_date")
                        }
                    )
                )

        except Exception as e:
            if 'response' in locals():
                logger.error(f"[Tavily] Search failed: {e}. Response: {response.text}")
            else:
                logger.error(f"[Tavily] Search failed: {e}")


class BochaSearchPlugin(SourcePlugin):
    """
    Search using Bocha AI Web Search API.
    """

    name = "bocha_search"
    description = "Web search using Bocha AI. Good for general reliable web results."
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = os.environ.get("BOCHA_API_KEY")

    def fetch(
        self,
        query: str,
        limit: int = 10,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:
        
        if not self.api_key:
            # Try getting from config if not in env (fallback)
            self.api_key = self.config.get("api_key") or os.environ.get("BOCHA_API_KEY")
            
        if not self.api_key:
            logger.error("BOCHA_API_KEY not found in environment variables.")
            return

        logger.info(f"[Bocha] Searching: {query} (limit={limit})")
        
        url = "https://api.bochaai.com/v1/web-search"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "freshness": "noLimit", # or "oneDay", "oneWeek", "oneMonth", "oneYear"
            "summary": True,
            "count": limit
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Bocha response structure usually has 'data' or 'webPages' -> 'value'
            # Based on common structures, let's assume standard logic or adapt
            # If structure is unknown, we log it for debugging first time, but here we assume standard:
            # { "code": 200, "data": { "webPages": { "value": [ ... ] } } }
            # Or direct list in some versions. Let's try parsing defensively.
            
            results = []
            if "data" in data and isinstance(data["data"], dict) and "webPages" in data["data"]:
                 results = data["data"]["webPages"].get("value", [])
            elif "webPages" in data:
                 results = data["webPages"].get("value", [])
            elif isinstance(data.get("data"), list):
                 results = data["data"]
            
            if not results:
                 logger.warning(f"[Bocha] No results found or unknown format. Response keys: {list(data.keys())}")

            for result in results:
                # Map fields
                title = result.get("name") or result.get("title")
                url_link = result.get("url")
                snippet = result.get("snippet") or result.get("summary") or ""
                
                if url_link:
                    yield WebisDocument(
                        content=snippet,
                        doc_type=DocumentType.HTML,
                        meta=DocumentMetadata(
                            url=url_link,
                            title=title,
                            source_plugin=self.name,
                            custom={
                                "date_last_crawled": result.get("dateLastCrawled")
                            }
                        )
                    )

        except Exception as e:
            if 'response' in locals():
                logger.error(f"[Bocha] Search failed: {e}. Response: {response.text}")
            else:
                logger.error(f"[Bocha] Search failed: {e}")
