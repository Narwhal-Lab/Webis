"""
SerpApi Source Plugin for Webis.
https://serpapi.com/search-api
"""

import logging
import os
from typing import Iterator, Optional, Dict, Any

import requests

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext

logger = logging.getLogger(__name__)


class SerpApiPlugin(SourcePlugin):
    """
    Search using SerpApi (serpapi.com).
    Supports Google, Bing, and other search engines.
    API docs: https://serpapi.com/search-api
    """

    name = "serpapi"
    description = "Google Search via SerpApi (serpapi.com)"
    required_env_vars = ["SERPAPI_API_KEY"]

    # Official API endpoint per documentation
    BASE_URL = "https://serpapi.com/search.json"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.engine = self.config.get("engine", "google")
        self.gl = self.config.get("gl", "")  # country code, e.g. 'us', 'cn'
        self.hl = self.config.get("hl", "")  # language code, e.g. 'en', 'zh-cn'
        self.api_key = self._resolve_api_key()

    @staticmethod
    def _resolve_api_key() -> Optional[str]:
        """Resolve API key with fallbacks."""
        key = os.environ.get("SERPAPI_API_KEY")
        if key:
            return key
        # Fallback: some users accidentally store the SerpApi key under SERPER_API_KEY
        fallback = os.environ.get("SERPER_API_KEY")
        if fallback:
            logger.info("SERPAPI_API_KEY not found, falling back to SERPER_API_KEY")
            return fallback
        return None

    def fetch(
        self,
        query: str,
        limit: int = 10,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:

        if not self.api_key:
            self.api_key = self._resolve_api_key()
        if not self.api_key:
            logger.error("Missing SERPAPI_API_KEY – set it in .env or environment")
            return

        params: Dict[str, Any] = {
            "engine": self.engine,
            "q": query,
            "api_key": self.api_key,
            "num": min(limit, 100),  # SerpApi caps at 100
        }
        # Optional locale parameters
        if self.gl:
            params["gl"] = self.gl
        if self.hl:
            params["hl"] = self.hl

        logger.info(f"[SerpApi] Searching: {query} (engine={self.engine}, limit={limit})")

        try:
            resp = requests.get(
                self.BASE_URL,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            # Check for API-level errors
            if "error" in data:
                logger.error(f"[SerpApi] API error: {data['error']}")
                return

            organic_results = data.get("organic_results", [])
            logger.info(f"[SerpApi] Got {len(organic_results)} organic results")

            count = 0
            for item in organic_results:
                if count >= limit:
                    break

                snippet = item.get("snippet", "")
                title = item.get("title", "")
                link = item.get("link", "")

                if not link:
                    continue

                yield WebisDocument(
                    content=snippet,  # Provide snippet as initial content
                    doc_type=DocumentType.HTML,
                    meta=DocumentMetadata(
                        url=link,
                        title=title,
                        source_plugin=self.name,
                        custom={
                            "snippet": snippet,
                            "position": item.get("position"),
                            "displayed_link": item.get("displayed_link", ""),
                            "date": item.get("date", ""),
                        }
                    )
                )
                count += 1

            # Also yield knowledge graph summary if present
            kg = data.get("knowledge_graph")
            if kg and count < limit:
                kg_title = kg.get("title", "")
                kg_desc = kg.get("description", "")
                kg_source = kg.get("source", {})
                if kg_desc:
                    yield WebisDocument(
                        content=f"{kg_title}: {kg_desc}",
                        doc_type=DocumentType.TEXT,
                        meta=DocumentMetadata(
                            url=kg_source.get("link", ""),
                            title=f"Knowledge Graph: {kg_title}",
                            source_plugin=self.name,
                            custom={
                                "type": "knowledge_graph",
                                "snippet": kg_desc,
                            }
                        )
                    )

        except requests.exceptions.Timeout:
            logger.error("[SerpApi] Request timed out")
        except requests.exceptions.HTTPError as e:
            logger.error(f"[SerpApi] HTTP error: {e.response.status_code} – {e.response.text[:200]}")
        except Exception as e:
            logger.error(f"[SerpApi] Search failed: {e}")
