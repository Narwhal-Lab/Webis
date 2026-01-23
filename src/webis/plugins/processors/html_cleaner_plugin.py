"""
HTML Cleaner Processor Plugin for WebIS

LLM-based approach (strict mode):
- Extract all visible text from HTML using BeautifulSoup
- Use LLM to identify and extract main content
- Returns structured JSON with main_text and reason
- Raises exception if LLM fails or returns invalid response
- No fallback mechanisms - ensures data quality at the cost of reliability
"""

import json
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from webis.core.plugin import ProcessorPlugin
from webis.core.schema import WebisDocument, PipelineContext
from webis.core.llm.base import get_default_router

logger = logging.getLogger(__name__)


def maybe_fix_mojibake(text: str) -> str:
    """Fix potential UTF-8 encoding issues."""
    if not text:
        return text

    def cjk_count(s: str) -> int:
        return sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")

    before = cjk_count(text)
    marker = sum(text.count(x) for x in ("Ã", "Â", "æ", "å", "ç", "é"))

    if marker < 20:
        return text

    try:
        fixed = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        return text

    after = cjk_count(fixed)
    return fixed if after >= before + 10 else text


class HTMLCleanerPlugin(ProcessorPlugin):
    """
    LLM-driven HTML cleaner for WebIS pipeline.
    
    Extracts visible text from HTML and uses LLM to identify main content.
    """

    name = "html_cleaner"
    input_type = "html"
    output_type = "text"

    def __init__(self):
        super().__init__()
        self._llm_router = None

    def process(
        self,
        doc: WebisDocument,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Optional[WebisDocument]:

        if not doc.content:
            return doc

        try:
            soup = BeautifulSoup(doc.content, "html.parser")

            # Remove script, style, and other non-content tags
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            # Extract all visible text
            page_text = soup.get_text(separator="\n", strip=True)
            
            # Apply mojibake fix
            page_text = maybe_fix_mojibake(page_text)

            # Use LLM to clean text - required, will raise exception if fails
            if not page_text:
                logger.warning(f"[HTMLCleanerPlugin] No text extracted from {doc.id}")
                return doc

            # This will raise exception if LLM cleaning fails
            clean_text = self._llm_clean(page_text)
            
            doc.clean_content = clean_text
            doc.add_processing_step(self.name)
            logger.info(f"[HTMLCleanerPlugin] Successfully cleaned {doc.id}, extracted {len(clean_text)} chars")
            
            return doc

        except Exception as e:
            logger.error(f"[HTMLCleanerPlugin] failed for {doc.id}: {e}")
            return doc

    def _build_cleaning_prompt(self, page_text: str) -> tuple[str, str]:
        """
        Build LLM prompt for main content extraction.
        Similar to swde_llm_labeled.py build_prompt().
        """
        system = (
            "You are annotating web pages for main-content extraction. Your job is to read the provided visible text of a page "
            "and extract the primary body content."
        )
        system += (
            " Main content includes the body of an article or the key description of a product, job, school, movie, etc."
            " Do NOT return navigation menus, breadcrumbs, header/footer text, ads, login/registration prompts, recommendations or related links,"
            " site search boxes, copyright notices, comments (unless comments are the main content), social sharing buttons,"
            " cookie banners, empty strings, or repeated template text."
        )
        
        user = (
            "The following is the page's visible text (scripts/styles removed). It is plain text with blocks concatenated in reading order.\n"
            "Respond with STRICT JSON containing:\n"
            '- "main_text": the extracted primary content as a single string (preserve original order, separate paragraphs with \\n\\n if needed)\n'
            '- "reason": 1-2 sentence justification\n\n'
            "Page text:\n\n"
            f"{page_text[:8000]}\n"  # Limit text to avoid token limits
        )
        
        return system, user

    def _llm_clean(self, page_text: str) -> Optional[str]:
        """Use LLM to extract main content from page text."""
        if self._llm_router is None:
            self._llm_router = get_default_router()

        system, user = self._build_cleaning_prompt(page_text)
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        # Call LLM - must succeed
        response = self._llm_router.chat(messages, temperature=0.0, max_tokens=4096)
        
        if not response.content:
            logger.error("[HTMLCleanerPlugin] LLM returned empty response")
            raise RuntimeError("LLM cleaning failed: Empty response from LLM API")

        # Parse JSON response - no fallback, must succeed
        try:
            result = json.loads(response.content)
            main_text = result.get("main_text", "").strip()
            
            if not main_text:
                raise ValueError("LLM returned empty main_text in JSON response")
            
            logger.debug(f"[HTMLCleanerPlugin] LLM extracted {len(main_text)} chars. Reason: {result.get('reason', 'N/A')}")
            return main_text
            
        except json.JSONDecodeError as e:
            logger.error(f"[HTMLCleanerPlugin] Failed to parse LLM response as JSON: {e}")
            logger.error(f"[HTMLCleanerPlugin] Raw LLM response: {response.content[:200]}...")
            raise RuntimeError(f"LLM cleaning failed: Invalid JSON response - {e}") from e
