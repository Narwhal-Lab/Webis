"""
Semantic Scholar Source Plugin for Webis (Enhanced with arXiv and PDF download).
Based on student implementation - prioritizes PDF downloads over metadata.
"""

import logging
import os
from typing import Iterator, Optional

import requests

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext

try:
    import arxiv
except ImportError:
    arxiv = None

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


class SemanticScholarPlugin(SourcePlugin):
    """
    Search academic papers using arXiv (with PDF download) and Semantic Scholar.
    Downloads PDFs when available, otherwise saves abstracts.
    """

    name = "semantic_scholar"
    description = "Search academic papers (arXiv + Semantic Scholar) and download PDFs"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._s2_api_key = os.environ.get("S2_API_KEY")

    def initialize(self, context: Optional[PipelineContext] = None) -> None:
        super().initialize(context)
        if arxiv is None:
            logger.warning("[Academic] arxiv package not installed. Only Semantic Scholar will be used.")

    def fetch(
        self,
        query: str,
        limit: int = 5,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:

        if not self._initialized:
            self.initialize(context)

        logger.info(f"[Academic] Searching: {query}")
        count = 0

        # Try arXiv first (better PDF availability)
        if arxiv is not None:
            try:
                search = arxiv.Search(
                    query=query,
                    max_results=limit,
                    sort_by=arxiv.SortCriterion.Relevance
                )

                for result in search.results():
                    if count >= limit:
                        break

                    # Download PDF content
                    pdf_content = self._download_arxiv_pdf(result)

                    yield WebisDocument(
                        content=pdf_content or result.summary,  # Fallback to summary if download fails
                        doc_type=DocumentType.PDF if pdf_content else DocumentType.HTML,
                        meta=DocumentMetadata(
                            url=result.entry_id,
                            title=result.title,
                            source_plugin=self.name,
                            custom={
                                "authors": [author.name for author in result.authors],
                                "published": str(result.published),
                                "pdf_url": result.pdf_url,
                                "categories": result.categories
                            }
                        )
                    )
                    count += 1

            except Exception as e:
                logger.warning(f"[Academic] arXiv search failed: {e}")

        # Supplement with Semantic Scholar if needed
        if count < limit:
            try:
                for doc in self._search_semantic_scholar(query, limit - count):
                    yield doc
            except Exception as e:
                logger.error(f"[Academic] Semantic Scholar search failed: {e}")

    def _download_arxiv_pdf(self, result) -> str:
        """
        Download arXiv PDF and return content as text.
        Returns empty string if download fails.
        """
        try:
            # Download PDF to temp location
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                result.download_pdf(dirpath=os.path.dirname(tmp.name), filename=os.path.basename(tmp.name))
                tmp_path = tmp.name

            # Read PDF content (will be processed by PDFPlugin later)
            with open(tmp_path, 'rb') as f:
                pdf_bytes = f.read()

            # Clean up temp file
            os.unlink(tmp_path)

            # Return as base64 for storage (will be decoded by processor)
            import base64
            return base64.b64encode(pdf_bytes).decode('utf-8')

        except Exception as e:
            logger.warning(f"[Academic] Failed to download arXiv PDF: {e}")
            return ""

    def _search_semantic_scholar(self, query: str, limit: int) -> Iterator[WebisDocument]:
        """Search Semantic Scholar API."""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {}
        if self._s2_api_key:
            headers["x-api-key"] = self._s2_api_key

        params = {
            "query": query,
            "limit": limit,
            "fields": "title,url,openAccessPdf,abstract,authors,year"
        }

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json().get('data', [])

            for paper in data:
                title = paper.get('title', 'Untitled')
                abstract = paper.get('abstract', '')
                paper_url = paper.get('url', '')

                # Try to download PDF if available
                pdf_info = paper.get('openAccessPdf')
                content = ""
                doc_type = DocumentType.HTML

                if pdf_info and pdf_info.get('url'):
                    pdf_url = pdf_info['url']
                    content = self._download_pdf_content(pdf_url)
                    if content:
                        doc_type = DocumentType.PDF

                # Fallback to abstract
                if not content and abstract:
                    content = f"Title: {title}\n\nAbstract:\n{abstract}"

                yield WebisDocument(
                    content=content,
                    doc_type=doc_type,
                    meta=DocumentMetadata(
                        url=paper_url,
                        title=title,
                        source_plugin=self.name,
                        custom={
                            "authors": [a.get('name') for a in paper.get('authors', [])],
                            "year": paper.get('year'),
                            "pdf_url": pdf_info.get('url') if pdf_info else None
                        }
                    )
                )

        except Exception as e:
            logger.error(f"[Academic] Semantic Scholar API error: {e}")

    def _download_pdf_content(self, url: str) -> str:
        """Download PDF and return as base64."""
        try:
            r = requests.get(url, headers=HEADERS, timeout=30, stream=True)
            r.raise_for_status()

            import base64
            return base64.b64encode(r.content).decode('utf-8')

        except Exception as e:
            logger.warning(f"[Academic] Failed to download PDF from {url}: {e}")
            return ""
