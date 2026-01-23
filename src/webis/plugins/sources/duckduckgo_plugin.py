"""
DuckDuckGo Source Plugin for Webis (Enhanced with content download).
Based on student implementation - downloads complete HTML pages.
"""

import logging
from typing import Iterator, Optional

import requests

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7"
}


class DuckDuckGoPlugin(SourcePlugin):
    """
    Search using DuckDuckGo and download complete HTML pages.
    """

    name = "duckduckgo"
    description = "Search using DuckDuckGo and download full HTML content"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.region = self.config.get("region", "wt-wt")
        self.safesearch = self.config.get("safesearch", "moderate")

    def initialize(self, context: Optional[PipelineContext] = None) -> None:
        super().initialize(context)
        if DDGS is None:
            raise ImportError("duckduckgo-search package is required. Install with `pip install duckduckgo-search`")

    def fetch(
        self,
        query: str,
        limit: int = 10,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:
        if not self._initialized:
            self.initialize(context)

        logger.info(f"[DuckDuckGo] Searching: {query}")

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=limit))

                for item in results:
                    url = item.get('href')
                    title = item.get('title')
                    snippet = item.get('body', '')

                    if not url:
                        continue

                    # Download the actual page content
                    content = self._fetch_page(url)

                    yield WebisDocument(
                        content=content,
                        doc_type=DocumentType.HTML,
                        meta=DocumentMetadata(
                            url=url,
                            title=title,
                            source_plugin=self.name,
                            custom={"snippet": snippet}
                        )
                    )

        except Exception as e:
            logger.error(f"[DuckDuckGo] Search failed: {e}")

    def _fetch_page(self, url: str) -> str:
        """
        Download HTML content from URL.
        Enhanced with proper encoding detection.
        """
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()

            # Auto-detect encoding (student's key improvement)
            r.encoding = r.apparent_encoding

            return r.text

        except Exception as e:
            logger.warning(f"[DuckDuckGo] Failed to fetch {url}: {e}")
            return ""
