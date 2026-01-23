"""
Baidu Search Source Plugin for Webis (Enhanced version).
Based on student implementation - handles redirect URL resolution.
"""

import logging
from typing import Iterator, Optional

import requests
from bs4 import BeautifulSoup

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}


class BaiduSearchPlugin(SourcePlugin):
    """
    Search using Baidu and download complete HTML pages.
    Handles Baidu's redirect URLs to get real destination.
    """

    name = "baidu_search"
    description = "Search using Baidu (China) and download full HTML content"

    def fetch(
        self,
        query: str,
        limit: int = 10,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:

        logger.info(f"[Baidu] Searching: {query}")

        url = "https://www.baidu.com/s"
        params = {"wd": query}

        # Try multiple times to handle network instability
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
                resp.raise_for_status()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"[Baidu] Search failed after {max_retries} attempts: {e}")
                    return
                logger.warning(f"[Baidu] Search attempt {attempt+1} failed: {e}. Retrying...")

        try:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Baidu results are typically in h3.t a tags, or sometimes slightly different structure
            # Enhanced selector to catch more result types
            results = soup.select("h3.t a, .c-container .t a")
            
            # Remove duplicates based on link
            seen_links = set()

            count = 0
            for a in results:
                if count >= limit:
                    break

                link = a.get("href")
                # Ensure it's a valid Baidu link (usually starts with http://www.baidu.com/link)
                if not link or link in seen_links:
                    continue
                
                title = a.get_text(strip=True)
                seen_links.add(link)

                try:
                    # Resolve Baidu's redirect to get real URL
                    # Use GET instead of HEAD for better compatibility with some servers
                    real_resp = requests.get(
                        link,
                        headers=HEADERS,
                        allow_redirects=True,
                        timeout=8,
                        stream=True  # Don't download body yet
                    )
                    real_url = real_resp.url
                    real_resp.close() # Close stream

                    # Download the actual page
                    logger.info(f"   Fetching: {real_url}")
                    content = self._fetch_page(real_url)

                    if content and len(content) > 100:
                        yield WebisDocument(
                            content=content,
                            doc_type=DocumentType.HTML,
                            meta=DocumentMetadata(
                                url=real_url,
                                title=title,
                                source_plugin=self.name,
                                custom={"baidu_redirect_url": link}
                            )
                        )
                        count += 1
                    else:
                         logger.warning(f"   Skipped empty/short content: {real_url}")

                except Exception as e:
                    logger.warning(f"[Baidu] Failed to process result '{title}': {e}")
                    continue

        except Exception as e:
            logger.error(f"[Baidu] Parsing failed: {e}")

    def _fetch_page(self, url: str) -> str:
        """Download HTML content from URL."""
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            return r.text

        except Exception as e:
            logger.warning(f"[Baidu] Failed to fetch {url}: {e}")
            return ""
