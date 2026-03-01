"""
RAG Retrieval Agent — Agent 1/3

Loads documents from the RAG knowledge base (``rag_store.json``),
deduplicates and ranks them, then calls the LLM to produce a rich
**analysis pack** — a free-form JSON object containing the report's
core content.

The LLM is given full creative freedom to decide what structure best
fits the data.  A lightweight fallback ensures the pipeline never
stalls even when the LLM call fails.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from webis.core.llm.base import get_default_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — encourages the LLM to analyse creatively
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are a senior research analyst.  You will receive a batch of web-sourced
documents about a given topic.  Deeply analyse them and produce a
**comprehensive, well-organised content pack** in JSON format.  This JSON
will later be used to generate a professional HTML report.

You have creative freedom over the JSON structure — choose whatever keys,
nesting, and grouping best represent the content.  There is NO fixed schema.

## Core Guidelines
- Extract **as many concrete facts, data points, statistics, key insights,
  and notable quotes** as possible — the final report should feel dense
  and information-rich, not sparse.
- Organise information into clearly delineated sections with descriptive
  headings; every section should carry substantial, specific content.
- Surface contrasting viewpoints fairly when they exist.
- Include source attribution so the reader can verify claims.
- Write in a professional, clear, and fluent tone.
- Do NOT invent data — only synthesise what the source material contains.
- Return **valid JSON only** (no markdown fences, no comments).

## Data Structuring for Presentation
- **Numeric data**: extract numbers, percentages, rankings, ratings,
  growth rates, scores, etc.  Structure them as arrays of
  `{"label": ..., "value": ...}` for downstream chart rendering.
- **Comparisons**: produce comparison tables / feature matrices.
- **Timelines**: output a dated event list if chronological data exists.
- **Processes / Flows**: output ordered step lists.
- **Quotes & Highlights**: extract notable quotes and key takeaways
  as standalone items.

## Visual & Creative Hints
- Include a `visual_hints` object with:
  - A **colour mood** inspired by the topic (e.g. "warm tech copper &
    charcoal", "ocean blue & sand", "forest green & gold").  Be creative
    — the palette should feel **inspired by the subject matter**, not
    generic corporate blue.
  - Potential illustration themes (e.g. "circuit board patterns",
    "growth arrows", "globe & connectivity").
  - A suggested emoji/icon per section for visual decoration.
- Include a `highlight_facts` array: 3–5 of the most surprising or
  impactful data points, perfect for visual callout boxes.
"""


class RAGRetrievalAgent:
    """Agent 1: analyse RAG documents and produce a content pack."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, rag_store_path: str, query: str = "") -> Dict[str, Any]:
        """Return an *analysis pack* dict."""
        docs = self._load_documents(rag_store_path)
        logger.info("Loaded %d documents from RAG store", len(docs))

        analysis = self._call_llm(docs, query)
        return analysis

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_documents(rag_store_path: str) -> List[Dict[str, Any]]:
        """Load, deduplicate, and return docs from rag_store.json."""
        path = Path(rag_store_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"rag_store.json not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        docs_map = raw.get("documents", {}) if isinstance(raw, dict) else {}
        if not isinstance(docs_map, dict) or not docs_map:
            raise ValueError(f"No documents in RAG store: {path}")

        seen = set()
        docs: List[Dict[str, Any]] = []
        for entry in docs_map.values():
            if not isinstance(entry, dict):
                continue
            content = (entry.get("content") or "").strip()
            if not content:
                continue
            source = str(entry.get("source") or "Unknown")
            key = (source, content)
            if key in seen:
                continue
            seen.add(key)

            meta = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
            docs.append({
                "source": source,
                "title": meta.get("title", ""),
                "content": content,
            })

        if not docs:
            raise ValueError(f"No valid docs in RAG store: {path}")
        return docs

    # ------------------------------------------------------------------
    def _call_llm(self, docs: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """Send docs to LLM and parse the JSON analysis pack."""
        # Build user message
        doc_texts = []
        for i, d in enumerate(docs, 1):
            title = d.get("title") or d["source"]
            snippet = d["content"][:6000]  # cap per-doc length
            doc_texts.append(f"--- Document {i}: {title} ---\n{snippet}")
        all_docs_text = "\n\n".join(doc_texts)

        user_msg = f"Topic / query: {query or '(general analysis)'}\n\n{all_docs_text}"

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        try:
            router = get_default_router()
            resp = router.chat(messages, use_cache=False, supports_json_mode=True)
            text = resp.content.strip()

            analysis = self._parse_json_text(text)
            if not isinstance(analysis, dict):
                raise ValueError("LLM returned non-dict JSON")
            logger.info("LLM analysis pack OK — keys: %s", list(analysis.keys()))
            return self._ensure_minimum_keys(analysis, docs, query)

        except Exception as exc:
            logger.warning("LLM analysis failed (%s), using fallback", exc)
            return self._build_fallback(docs, query)

    @staticmethod
    def _parse_json_text(text: str) -> Dict[str, Any]:
        raw = text.strip()

        if raw.startswith("```"):
            first_nl = raw.find("\n")
            if first_nl != -1:
                raw = raw[first_nl + 1 :]
        if raw.endswith("```"):
            raw = raw[:-3].rstrip()

        try:
            return json.loads(raw)
        except Exception:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start : end + 1]
            candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
            return json.loads(candidate)

        raise ValueError("Unable to parse valid JSON from LLM output")

    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_minimum_keys(
        pack: Dict[str, Any],
        docs: List[Dict[str, Any]],
        query: str,
    ) -> Dict[str, Any]:
        """Guarantee the pack has a title and source references."""
        # Find a title-like key; add one if absent
        title_keys = [k for k in pack if "title" in k.lower()]
        if not title_keys:
            pack["report_title"] = query or "Research Report"
        # Ensure source references exist somewhere
        source_keys = [k for k in pack if "source" in k.lower() or "ref" in k.lower()]
        if not source_keys:
            pack["sources"] = [
                {"title": d.get("title") or d["source"], "url": d["source"]}
                for d in docs
            ]
        return pack

    # ------------------------------------------------------------------
    @staticmethod
    def _build_fallback(docs: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """Deterministic fallback when LLM is unavailable."""
        sources = [
            {"title": d.get("title") or d["source"], "url": d["source"]}
            for d in docs
        ]
        sections = []
        for i, d in enumerate(docs, 1):
            title = d.get("title") or f"Source {i}"
            sections.append({
                "heading": title,
                "content": d["content"][:3000],
                "highlights": [],
            })

        return {
            "report_title": query or "Research Report",
            "subtitle": f"Analysis based on {len(docs)} sources",
            "executive_summary": (
                f"This report synthesises information from {len(docs)} sources "
                f"on the topic: {query or 'general research'}."
            ),
            "key_findings": [s.get("heading", "") for s in sections[:5]],
            "sections": sections,
            "data_points": [],
            "conclusions": "Please refer to the individual source sections above for detailed information.",
            "sources": sources,
        }
