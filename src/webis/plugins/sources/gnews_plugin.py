"""
GNews Source Plugin for Webis (Enhanced version).
Combines API and scraping fallback based on student implementation.
"""

import logging
import os
from typing import Iterator, Optional

import requests

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext

try:
    from gnews import GNews
except ImportError:
    GNews = None

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


class GNewsPlugin(SourcePlugin):
    """
    Fetch news using GNews API (if available) + Google News scraping fallback.
    Downloads complete article content.
    """

    name = "gnews"
    description = "Search Google News and download full article content"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.language = self.config.get("language", "en")
        self.country = self.config.get("country", "US")
        self.period = self.config.get("period", "7d")
        self._api_key = os.environ.get("GNEWS_API_KEY")
        self._client = None

    def initialize(self, context: Optional[PipelineContext] = None) -> None:
        super().initialize(context)

        # Initialize scraper client as fallback
        if GNews is not None:
            self._client = GNews(
                language=self.language,
                country=self.country,
                period=self.period
            )

    def fetch(
        self,
        query: str,
        limit: int = 10,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:

        if not self._initialized:
            self.initialize(context)

        logger.info(f"[GNews] Searching: {query}")
        seen_urls = set()
        count = 0

        # Try API first (if available)
        if self._api_key:
            try:
                for doc in self._fetch_via_api(query, limit, seen_urls):
                    yield doc
                    count += 1
                    if count >= limit:
                        return
            except Exception as e:
                logger.warning(f"[GNews] API failed: {e}, falling back to scraper")

        # Fallback to scraper
        if count < limit and self._client:
            try:
                for doc in self._fetch_via_scraper(query, limit - count, seen_urls):
                    yield doc
            except Exception as e:
                logger.error(f"[GNews] Scraper also failed: {e}")

    def _fetch_via_api(self, query: str, limit: int, seen_urls: set) -> Iterator[WebisDocument]:
        """Fetch news via GNews official API."""
        url = "https://gnews.io/api/v4/search"
        params = {"q": query, "lang": self.language, "max": limit, "token": self._api_key}

        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])

        for article in articles:
            link = article.get("url")
            if not link or link in seen_urls:
                continue

            seen_urls.add(link)
            content = self._download_article(link)

            yield WebisDocument(
                content=content,
                doc_type=DocumentType.HTML,
                meta=DocumentMetadata(
                    url=link,
                    title=article.get("title", ""),
                    source_plugin=self.name,
                    custom={
                        "source": article.get("source", {}).get("name"),
                        "published_at": article.get("publishedAt"),
                        "description": article.get("description")
                    }
                )
            )

    def _fetch_via_scraper(self, query: str, limit: int, seen_urls: set) -> Iterator[WebisDocument]:
        """Fetch news via GNews scraping library."""
        if not self._client:
            return

        results = self._client.get_news(query)
        count = 0

        for item in results:
            if count >= limit:
                break

            link = item.get('url')
            if not link:
                continue

            try:
                # Resolve redirect
                real_resp = requests.head(link, allow_redirects=True, timeout=10, headers=HEADERS)
                real_url = real_resp.url

                if real_url in seen_urls:
                    continue

                seen_urls.add(real_url)
                content = self._download_article(real_url)

                yield WebisDocument(
                    content=content,
                    doc_type=DocumentType.HTML,
                    meta=DocumentMetadata(
                        url=real_url,
                        title=item.get("title", ""),
                        source_plugin=self.name,
                        custom={
                            "publisher": item.get("publisher", {}).get("title"),
                            "published_date": item.get("published date")
                        }
                    )
                )
                count += 1

            except Exception as e:
                logger.warning(f"[GNews] Failed to process {link}: {e}")
                continue

    def _download_article(self, url: str) -> str:
        """Download full article HTML."""
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()

            # Check content type
            content_type = r.headers.get('Content-Type', '').lower()
            if 'text' in content_type or 'html' in content_type:
                return r.text
            else:
                # Binary content, return empty (will be handled by processor)
                return ""

        except Exception as e:
            logger.warning(f"[GNews] Failed to download {url}: {e}")
            return ""
