"""
Template Design Agent — Agent 2/3

Consumes the *analysis pack* from Agent 1 and asks the LLM to design
a bespoke **visual theme** — colour palette, typography, layout ideas,
and a complete CSS stylesheet.

The LLM has full creative freedom; the only constraint is the output
format so that Agent 3 can consume it.  A polished default theme is
available as fallback.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

from webis.core.llm.base import get_default_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — let the LLM be a UI designer
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are a professional web UI designer.  You will receive a structured
analysis pack (JSON) describing a research report.

Your mission: design a **visually distinctive, topic-inspired theme** for
a standalone HTML report.  The report should feel like a high-quality
digital publication — polished and professional, but also **visually
engaging and memorable**.  It should have personality, not look like a
generic template.

## Return format
Return **valid JSON only** (no markdown fences, no comments) with these
two required keys:

- `"theme_name"` — a descriptive name for your design
- `"css_theme"` — a complete, self-contained CSS stylesheet (string)

You may add any extra keys you find useful (colour palette, font list,
layout notes, etc.).

## 🎨 Colour Palette (TOPIC-INSPIRED & HARMONIOUS)
- Design a **topic-inspired palette** with personality: 1 primary colour,
  1–2 accent colours, plus neutrals.  The palette should feel connected
  to the report subject (e.g. warm copper tones for technology, ocean
  blues for maritime, earthy greens for sustainability).
- Gradients are encouraged — use **2–3 colour stop gradients** for hero
  backgrounds, section highlights, and decorative elements.
- Section backgrounds: mix white, light tints, and occasional deeper-
  toned highlight sections to create visual rhythm and break monotony.
- Cards: use light backgrounds with accent-coloured borders or subtle
  gradient backgrounds.  Moderate shadows are fine for depth.
- The overall feel should be **warm and inviting**, not clinical.

## 📐 Layout (COMPACT BUT RHYTHMIC)
- Use a single-column or 2-column layout as the backbone, but allow
  **visual rhythm variation**: alternate between full-width sections,
  card grids, and text-with-sidebar panels to keep the reader engaged.
- **Tight spacing** overall: section padding `1.5rem 0`, card padding
  `1rem`, paragraph margin `0.6em 0` — the report should feel dense.
- Use a **max-width** container (850–950px) centred on page.
- Allow occasional layout shifts — e.g. a highlight section can break
  out slightly wider, or a quote panel can float to one side.
- Cards and stat rows should feel well-integrated, not rigidly stacked.

## 🖼️ Illustrations (MODERATE & PURPOSEFUL)
- Include **topic-relevant inline SVG illustrations** at key points:
  a medium-sized hero graphic (150–250px), section-header icons
  (28–36px), and small decorative accents between sections.
- Hero area: a **tasteful SVG illustration** that visually represents
  the report topic, paired with the title.  Keep it elegant, not
  overwhelming.
- Decorative dividers: styled `<hr>` with subtle gradient or thin
  SVG patterns (simple waves, dots, or geometric lines).
- Background decorations: very light textures (opacity <0.06) are OK
  in hero or highlight sections.

## 🔤 Typography (CLEAN BUT EXPRESSIVE HEADINGS)
- Import **2–3 Google Fonts**: a **display/heading font** that is
  distinctive and eye-catching (e.g. Playfair Display, DM Serif
  Display, Space Grotesk, Outfit, Sora), plus a clean body font
  (e.g. Inter, Source Sans 3, Noto Sans).
- **H1**: 2.5–3.2rem, bold or black weight, primary colour.  May use
  `letter-spacing: -0.02em` for a tight, modern feel.  A subtle
  `text-shadow` or accent underline is OK to make it stand out.
- **H2**: 1.4–1.7rem, semibold, with a coloured underline, left
  border, or small decorative accent to draw the eye.
- **Body text**: 0.95–1rem, line-height 1.6–1.7, dark grey (`#333`).
  Keep body text clean and readable.
- Blockquotes: subtle left border (3px accent colour), slightly
  indented, italic.
- Overall: headings should feel **distinctive and memorable** while
  body text stays professional and easy to read.

## 📊 Data Presentation
- Pre-define CSS classes for **horizontal bar charts** (CSS width%),
  **stat cards** (compact: large number + small label), and **styled
  tables** with alternating row backgrounds and hover highlight.
- Stat cards should use the primary colour for numbers and be compact
  (not oversized).
- Timelines: simple vertical line with small coloured dots and
  compact content.
- Tags / badges: small pills with low-contrast backgrounds.

## ✨ Motion & Effects
- `fade-in` on page load (opacity 0→1, 0.4s).
- Hover effects on cards (lift + shadow deepening, 250ms ease).
- Subtle `@keyframes` for hero elements — e.g. a gentle gradient shift
  or a slow floating accent SVG.
- Keep motion tasteful — enhance the experience, don't distract.

The CSS must be self-contained (no external dependencies except
Google Fonts @import).  Balance **information density** with **visual
appeal** — the report should be both content-rich and a pleasure to look
at.  Every design should feel unique and topic-appropriate.

## Footer Branding
- Include a styled footer section at the very bottom with the text:
  **"Generated based on Webis"** — centred, small font, muted colour,
  with a thin top border.  Pre-define a `.webis-footer` CSS class.
"""


class TemplateDesignAgent:
    """Agent 2: design a visual theme for the report."""

    def run(self, analysis_pack: Dict[str, Any], query: str = "") -> Dict[str, Any]:
        """Return a *presentation pack* dict with theme + CSS."""
        design = self._call_llm(analysis_pack, query)
        # Ensure css_theme is present (minimal fallback if empty)
        if not design.get("css_theme"):
            design["css_theme"] = self._minimal_fallback_css()
        return design

    # ------------------------------------------------------------------
    def _call_llm(self, analysis_pack: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Ask the LLM for a theme design."""
        # Build a concise summary of the analysis for the designer
        summary = {
            "report_title": analysis_pack.get("report_title", ""),
            "subtitle": analysis_pack.get("subtitle", ""),
            "num_sections": len(analysis_pack.get("sections", [])),
            "section_headings": [
                s.get("heading", "") for s in analysis_pack.get("sections", [])
            ],
            "num_key_findings": len(analysis_pack.get("key_findings", [])),
            "num_data_points": len(analysis_pack.get("data_points", [])),
            "topic_query": query,
        }

        user_msg = (
            "Design a beautiful theme for this report.\n\n"
            f"Report info:\n{json.dumps(summary, ensure_ascii=False, indent=2)}"
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        try:
            router = get_default_router()
            resp = router.chat(messages, use_cache=False, supports_json_mode=True)
            text = resp.content.strip()

            design = self._parse_json_text(text)
            if not isinstance(design, dict):
                raise ValueError("Non-dict JSON from LLM")

            logger.info(
                "LLM theme design OK — theme=%s",
                design.get("theme_name", "(unnamed)"),
            )
            return design

        except Exception as exc:
            logger.warning("LLM theme design failed (%s), using default theme", exc)
            return self._build_fallback(analysis_pack)

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
    def _build_fallback(analysis_pack: Dict[str, Any]) -> Dict[str, Any]:
        """Return a minimal fallback design pack."""
        return {
            "theme_name": "Minimal Fallback",
            "css_theme": TemplateDesignAgent._minimal_fallback_css(),
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _minimal_fallback_css() -> str:
        """Minimal emergency fallback — only used when LLM fails."""
        return """\
/* ========== Minimal Fallback Theme ========== */

* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #f5f5f5; color: #222;
  line-height: 1.7; max-width: 1100px;
  margin: 0 auto; padding: 32px 24px;
}
h1 { font-size: 2rem; margin-bottom: 0.5em; }
h2 { font-size: 1.4rem; margin: 1.5em 0 0.5em; }
p { margin-bottom: 1em; }
a { color: #1a73e8; }
@media print { body { background: #fff; } }
"""
