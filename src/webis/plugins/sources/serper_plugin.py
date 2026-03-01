import logging
import os
import json
import requests
from typing import Iterator, Optional, Dict, Any

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext

logger = logging.getLogger(__name__)

class SerperSearchPlugin(SourcePlugin):
    """
    Search using Serper.dev API (Google Search Wrapper).
    Fast and cheap alternative to official Google API.
    """

    name = "serper_search"
    description = "Fast and reliable Google Search using Serper.dev API."
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = os.environ.get("SERPER_API_KEY")

    def fetch(
        self,
        query: str,
        limit: int = 10,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:
        
        if not self.api_key:
            self.api_key = os.environ.get("SERPER_API_KEY")
            
        if not self.api_key:
            if os.environ.get("SERP_API_KEY"):
                logger.warning("Detected SERP_API_KEY (SerpAPI) but serper_search needs SERPER_API_KEY. Skipping serper_search.")
            else:
                logger.error("SERPER_API_KEY not found in environment variables.")
            return

        logger.info(f"[Serper] Searching: {query} (limit={limit})")
        
        url = "https://google.serper.dev/search"
        
        payload = json.dumps({
            "q": query,
            "num": limit
        })
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("organic", [])
            
            for result in results:
                yield WebisDocument(
                    content=result.get("snippet", ""),
                    doc_type=DocumentType.HTML, 
                    meta=DocumentMetadata(
                        url=result.get("link"),
                        title=result.get("title"),
                        source_plugin=self.name,
                        custom={
                            "position": result.get("position"),
                            "date": result.get("date")
                        }
                    )
                )

        except Exception as e:
            logger.error(f"[Serper] Search failed: {e}")
