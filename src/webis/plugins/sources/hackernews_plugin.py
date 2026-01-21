"""
HackerNews Source Plugin for Webis (Enhanced version).
Based on student implementation - downloads complete article content.
"""

import logging
from typing import Iterator, Optional

import requests

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}


class HackerNewsPlugin(SourcePlugin):
    """
    Search HackerNews and download complete article content.
    Uses Algolia HN Search API.
    """

    name = "hackernews"
    description = "Search HackerNews stories and download full article content"

    def fetch(
        self,
        query: str,
        limit: int = 10,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:

        logger.info(f"[HackerNews] Searching: {query}")

        url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage={limit}"

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            hits = resp.json().get('hits', [])

            for hit in hits:
                link = hit.get('url')
                title = hit.get('title')
                hn_id = hit.get('objectID')
                points = hit.get('points', 0)
                author = hit.get('author', '')

                if not link or not title:
                    continue

                # Download the actual article
                content = self._fetch_page(link)

                yield WebisDocument(
                    content=content,
                    doc_type=DocumentType.HTML,
                    meta=DocumentMetadata(
                        url=link,
                        title=title,
                        source_plugin=self.name,
                        custom={
                            "hn_id": hn_id,
                            "points": points,
                            "author": author,
                            "hn_comments_url": f"https://news.ycombinator.com/item?id={hn_id}"
                        }
                    )
                )

        except Exception as e:
            logger.error(f"[HackerNews] Search failed: {e}")

    def _fetch_page(self, url: str) -> str:
        """Download HTML content from URL."""
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            return r.text

        except Exception as e:
            logger.warning(f"[HackerNews] Failed to fetch {url}: {e}")
            return ""
