"""
Content Planner Agent — Image Report Agent 1/2

Consumes the *analysis pack* from ``RAGRetrievalAgent`` and asks the
LLM to produce a detailed **poster layout plan** — a structured JSON
describing the visual composition of an image report.

Modelled after the Paper2Slides **ContentPlanner** stage:
- Requires **substantial content** per section (150+ words)
- Preserves **specific numbers, percentages, data points**
- Structures data for visual rendering (charts, tables, metrics)
- Plans the visual layout with precise art-direction
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

from webis.core.llm.base import get_default_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — Paper2Slides-inspired content planning
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are a senior information-design specialist and data journalist.
You will receive a structured analysis pack (JSON) about a research
topic.  Your task is to produce a **detailed poster / infographic
content plan** in JSON that will be fed VERBATIM to an image-generation
model (Gemini) to draw a single high-quality poster image.

ALL OUTPUT TEXT MUST BE IN ENGLISH.  Even if the source material is in
another language, translate and write every field in English.

## Return format
Return **valid JSON only** (no markdown fences, no trailing commas).

Required top-level keys:

{
  "title": "...",
  "subtitle": "...",
  "color_scheme": {
    "primary": "#RRGGBB",
    "secondary": "#RRGGBB",
    "accent": "#RRGGBB",
    "background": "#RRGGBB",
    "text_dark": "#RRGGBB",
    "text_light": "#RRGGBB"
  },
  "layout_type": "magazine | dashboard | infographic | academic_poster",
  "sections": [
    {
      "id": "section_01",
      "heading": "...",
      "content_type": "overview | metrics | timeline | comparison | analysis | quote",
      "body": "...",
      "bullet_points": ["...", "..."],
      "metrics": [{"label": "...", "value": "...", "trend": "up|down|stable"}],
      "data_table": [{"col1": "...", "col2": "..."}],
      "chart_type": "bar | line | pie | radar | none",
      "visual_hint": "..."
    }
  ],
  "highlight_facts": ["...", "..."],
  "key_statistics": [{"label": "...", "value": "...", "context": "..."}],
  "footer_text": "Generated based on Webis · Intelligent Knowledge Pipeline",
  "style_notes": "..."
}

## CRITICAL CONTENT REQUIREMENTS
1. **SUBSTANTIAL CONTENT**: Each section body MUST contain at least
   100-150 words of detailed, specific information — NOT vague
   summaries.  COPY AND ADAPT text from the source material.
2. **PRESERVE SPECIFIC NUMBERS**: Extract ALL percentages, rankings,
   growth rates, market sizes, dates, scores.  Put them in `metrics`
   arrays AND weave them into the body text.
3. **DATA TABLES**: If the source contains comparison data, extract it
   into `data_table` arrays with actual values.
4. **CHART SUGGESTIONS**: For every section with numeric data, specify
   a `chart_type` so the renderer can visualize it.
5. **5-8 SECTIONS**: Organize into clearly themed sections. Typical
   structure:
   - Executive Overview (the big picture)
   - Key Findings / Data Points (metrics-heavy)
   - Detailed Analysis (2-3 sections covering main themes)
   - Trends / Timeline (if chronological data exists)
   - Conclusions / Outlook
6. **KEY STATISTICS**: Extract 4-6 of the most impactful numbers into
   the top-level `key_statistics` array — these will be rendered as
   large callout stat cards.
7. **HIGHLIGHT FACTS**: 3-5 of the most surprising or newsworthy
   findings — punchy, quotable one-liners.

## COLOR SCHEME GUIDELINES
Use a **MORANDI-inspired palette** (soft, muted, low-saturation,
sophisticated) that is thematically appropriate:
- Technology → muted steel blue + warm grey + soft amber
- Finance → deep navy + dusty gold + sage
- Healthcare → soft teal + warm ivory + muted coral
- Environment → olive green + sand + slate
- General → slate blue + warm taupe + soft orange
The background should be LIGHT (near-white or very light tint).

## STYLE NOTES
Describe the desired aesthetic in 2-3 sentences covering:
- Typography feel (e.g. "clean rounded sans-serif, modern editorial")
- Visual density (e.g. "information-dense but well-organized with
  clear visual hierarchy")
- Mood (e.g. "professional, authoritative, data-driven")
"""


class ContentPlannerAgent:
    """Plan the visual layout of an image poster from an analysis pack."""

    def run(self, analysis_pack: Dict[str, Any], query: str = "") -> Dict[str, Any]:
        """Return a *layout plan* dict."""
        plan = self._call_llm(analysis_pack, query)
        return self._ensure_minimum(plan, analysis_pack, query)

    # ------------------------------------------------------------------
    def _call_llm(
        self, analysis_pack: Dict[str, Any], query: str
    ) -> Dict[str, Any]:
        summary_for_planner = json.dumps(
            analysis_pack, ensure_ascii=False, indent=2
        )
        # Cap the input at ~12 000 chars to stay within token budget
        if len(summary_for_planner) > 12_000:
            summary_for_planner = summary_for_planner[:12_000] + "\n...(truncated)"

        user_msg = (
            f"Topic / query: {query or '(general analysis)'}\n\n"
            f"Analysis pack:\n{summary_for_planner}"
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        try:
            router = get_default_router()
            resp = router.chat(messages, use_cache=False, supports_json_mode=True)
            text = resp.content.strip()
            plan = self._parse_json(text)
            if not isinstance(plan, dict):
                raise ValueError("LLM returned non-dict JSON")
            logger.info(
                "Content plan OK — %d sections, layout=%s",
                len(plan.get("sections", [])),
                plan.get("layout_type", "?"),
            )
            return plan
        except Exception as exc:
            logger.warning("LLM content planning failed (%s), using fallback", exc)
            return self._build_fallback(analysis_pack, query)

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        raw = text.strip()
        if raw.startswith("```"):
            first_nl = raw.find("\n")
            if first_nl != -1:
                raw = raw[first_nl + 1:]
        if raw.endswith("```"):
            raw = raw[:-3].rstrip()
        try:
            return json.loads(raw)
        except Exception:
            pass
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start: end + 1]
            candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
            return json.loads(candidate)
        raise ValueError("Unable to parse valid JSON from LLM output")

    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_minimum(
        plan: Dict[str, Any],
        analysis: Dict[str, Any],
        query: str,
    ) -> Dict[str, Any]:
        """Guarantee required keys exist."""
        if "title" not in plan:
            plan["title"] = analysis.get("report_title", query or "Research Report")
        if "subtitle" not in plan:
            plan["subtitle"] = analysis.get("subtitle", "")
        if "color_scheme" not in plan:
            plan["color_scheme"] = {
                "primary": "#5b7a94",
                "secondary": "#8ba4b8",
                "accent": "#c49a6c",
                "background": "#f7f5f2",
                "text_dark": "#2d3436",
                "text_light": "#ffffff",
            }
        if "sections" not in plan or not plan["sections"]:
            sections = []
            for i, s in enumerate(analysis.get("sections", [])[:8]):
                sections.append({
                    "id": f"section_{i+1:02d}",
                    "heading": s.get("heading", "Section"),
                    "content_type": "analysis",
                    "body": (s.get("content", "") or "")[:500],
                    "bullet_points": s.get("highlights", []),
                    "metrics": [],
                    "chart_type": "none",
                    "visual_hint": "",
                })
            plan["sections"] = sections
        if "highlight_facts" not in plan:
            plan["highlight_facts"] = analysis.get("highlight_facts", [])
        if "key_statistics" not in plan:
            plan["key_statistics"] = []
        if "layout_type" not in plan:
            plan["layout_type"] = "infographic"
        if "footer_text" not in plan:
            plan["footer_text"] = "Generated based on Webis · Intelligent Knowledge Pipeline"
        if "style_notes" not in plan:
            plan["style_notes"] = (
                "Clean rounded sans-serif typography with modern editorial feel. "
                "Information-dense but well-organized with clear visual hierarchy. "
                "Professional, authoritative, data-driven."
            )
        return plan

    # ------------------------------------------------------------------
    @staticmethod
    def _build_fallback(
        analysis: Dict[str, Any], query: str
    ) -> Dict[str, Any]:
        """Deterministic fallback when LLM is unavailable."""
        sections = []
        for i, s in enumerate(analysis.get("sections", [])[:8]):
            sections.append({
                "id": f"section_{i+1:02d}",
                "heading": s.get("heading", "Section"),
                "content_type": "analysis",
                "body": (s.get("content", "") or "")[:500],
                "bullet_points": s.get("highlights", []),
                "metrics": [],
                "chart_type": "none",
                "visual_hint": "",
            })
        return {
            "title": analysis.get("report_title", query or "Research Report"),
            "subtitle": analysis.get(
                "subtitle",
                f"Comprehensive analysis based on {len(analysis.get('sections', []))} sources",
            ),
            "color_scheme": {
                "primary": "#5b7a94",
                "secondary": "#8ba4b8",
                "accent": "#c49a6c",
                "background": "#f7f5f2",
                "text_dark": "#2d3436",
                "text_light": "#ffffff",
            },
            "layout_type": "infographic",
            "sections": sections,
            "highlight_facts": analysis.get(
                "highlight_facts", analysis.get("key_findings", [])
            )[:5],
            "key_statistics": [],
            "footer_text": "Generated based on Webis · Intelligent Knowledge Pipeline",
            "style_notes": (
                "Clean rounded sans-serif typography with modern editorial feel. "
                "Information-dense but well-organized with clear visual hierarchy. "
                "Professional, authoritative, data-driven. "
                "Morandi-inspired muted color palette."
            ),
        }
