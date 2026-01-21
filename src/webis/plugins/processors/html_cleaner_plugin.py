"""
HTML Cleaner Processor Plugin for WebIS

Final merged version:
- DOM block-level extraction (no webis_html dependency)
- Deterministic main-content selection (distilled rules)
- Integrated encoding-fix & noise-reduction utilities
"""

import logging
import re
from typing import Optional, List

from bs4 import BeautifulSoup

from webis.core.plugin import ProcessorPlugin
from webis.core.schema import WebisDocument, PipelineContext

logger = logging.getLogger(__name__)


def basic_noise_reduction(text: str) -> str:
    text = re.sub(r"\r\n|\r|\n", "\n", text)
    text = re.sub(r"\s+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if len(line) >= 3]
    return "\n\n".join(lines).strip()


def maybe_fix_mojibake(text: str) -> str:
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
    Deterministic HTML cleaner for WebIS pipeline.
    """

    name = "html_cleaner"
    input_type = "html"
    output_type = "text"


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

            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            blocks = self._extract_blocks(soup)

            texts: List[str] = []
            for block in blocks:
                if self._is_main_content_block(block):
                    texts.append(block["text"])

            raw_text = "\n".join(texts)

            raw_text = maybe_fix_mojibake(raw_text)
            clean_text = basic_noise_reduction(raw_text)

            doc.clean_content = clean_text
            doc.add_processing_step(self.name)
            return doc

        except Exception as e:
            logger.error(f"[HTMLCleanerPlugin] failed for {doc.id}: {e}")
            return doc

    def _extract_blocks(self, soup: BeautifulSoup) -> List[dict]:
        blocks: List[dict] = []

        for elem in soup.find_all(["p", "section", "article", "div", "table"]):
            text = elem.get_text(strip=True)
            if not text:
                continue

            text_len = len(text)
            link_text_len = sum(len(a.get_text(strip=True)) for a in elem.find_all("a"))
            link_density = link_text_len / max(text_len, 1)

            blocks.append({
                "tag": elem.name,
                "text": text,
                "text_len": text_len,
                "link_density": link_density,
            })

        return blocks

    def _is_main_content_block(self, block: dict) -> bool:
        tag = block["tag"]
        text_len = block["text_len"]
        link_density = block["link_density"]

        if tag in {"nav", "footer", "aside", "header"}:
            return False

        if text_len < 30:
            return False

        if text_len >= 80 and link_density <= 0.2:
            return True

        if tag in {"table", "section", "article"} and text_len >= 50:
            return True

        return False
