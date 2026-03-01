"""
Image Render Agent — Image Report Agent 2/2

Takes the *layout plan* from ``ContentPlannerAgent`` and calls the
**Gemini image-generation model** to produce a high-quality poster /
infographic as a single image.

Modelled after the Paper2Slides Stage-4 approach with its exact
prompt layering strategy:

  **Format → Style → Layout → Content → Visualization → Consistency**

Key design principles borrowed from Paper2Slides:
- MORANDI color palette (soft, muted, low-saturation, sophisticated)
- ROUNDED sans-serif fonts for all text
- Data visualization with CHARTS (bar, line, pie, radar)
- SPACIOUS and ELEGANT layout with breathing room
- Sharp, readable text at proper sizes

Model: ``gemini-3-pro-image-preview``
Endpoint:
  ``https://zhouliuai.online/v1beta/models/gemini-3-pro-image-preview:generateContent``
Auth key env var: ``ZHOULIU_API_KEY``
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_GEMINI_URL = (
    "https://zhouliuai.online/v1beta/models/"
    "gemini-3-pro-image-preview:generateContent"
)
_ENV_KEY = "ZHOULIU_API_KEY"

_MAX_RETRIES = 2
_RETRY_DELAY = 5  # seconds

# ---------------------------------------------------------------------------
# Paper2Slides-style prompt constants (adapted for poster format)
# ---------------------------------------------------------------------------

# Format prefix — equivalent to Paper2Slides' FORMAT_POSTER
_FORMAT_PREFIX = """\
Generate a SINGLE high-resolution information poster image.
Portrait orientation, approximately 1080×1920 pixels.
Just ONE poster — NOT multiple pages, NOT code, NOT markdown, NOT HTML.
The output must be a beautiful, print-ready infographic image."""

# Style hints — equivalent to Paper2Slides' SLIDE_STYLE_HINTS["academic"]
_STYLE_HINTS = """\
Professional MODERN EDITORIAL style. English text only.
Use ROUNDED SANS-SERIF FONTS for ALL text (similar to Inter, Source Sans,
Noto Sans, or SF Pro). NO serif fonts, no decorative fonts.
Use MORANDI COLOR PALETTE (soft, muted, low-saturation colors) for a
sophisticated, premium feel. LIGHT background (near-white or very light tint).
Clean simple lines. Subtle shadows for depth on cards. Thin accent borders.
Layout should be SPACIOUS and ELEGANT — avoid crowding, leave generous
breathing room between sections. Content should feel DENSE with information
but CLEAN in presentation.
Overall feel: minimal, scholarly, professional, sophisticated, data-driven."""

# Visualization hints — equivalent to Paper2Slides' VISUALIZATION_HINTS
_VISUALIZATION_HINTS = """\
DATA VISUALIZATION REQUIREMENTS:
- Visualize numeric data with CHARTS: bar charts, line charts, pie charts,
  radar charts, or progress bars where appropriate.
- REDRAW all charts to match the poster's visual style and color scheme.
- Make charts LARGE and meaningful — they should be focal visual elements.
- Use accent colors for chart elements, muted background for chart area.
- Stat cards: display key numbers LARGE (36-48pt) and BOLD in accent color,
  with small descriptive labels below (12-14pt).
- Comparison data: use clean side-by-side bar charts or styled tables
  with alternating row backgrounds.
- Timelines: simple vertical or horizontal line with colored dots and
  compact content blocks."""

# Consistency hint — equivalent to Paper2Slides' CONSISTENCY_HINT
_CONSISTENCY_HINT = """\
IMPORTANT: Maintain CONSISTENT colors and style throughout the entire poster.
Same background color, same accent color, same font style, same chart/icon
style across all sections. Keep visual consistency."""

# Typography rules
_TYPOGRAPHY_RULES = """\
TYPOGRAPHY HIERARCHY (STRICT):
- TITLE: 48-64pt, bold/black weight, primary color or white on dark header.
  Letter-spacing: -0.02em for tight modern feel.
- SECTION HEADINGS: 24-32pt, semibold, with a colored underline or left
  accent border (3px). Use primary or secondary color.
- BODY TEXT: 14-18pt, regular weight, dark grey (#2d3436 or similar).
  Line-height 1.5-1.7. Clean and highly readable.
- STAT NUMBERS: 36-48pt, bold, accent color. Must be eye-catching.
- LABELS / CAPTIONS: 10-13pt, medium weight, muted grey.
- FOOTER: 10-12pt, centered, muted color, thin top border.
ALL TEXT MUST BE SHARP, CRISP, AND PERFECTLY READABLE — no blurriness,
no anti-aliasing artifacts. Text is the most important element."""

# Layout rules
_LAYOUT_RULES = """\
LAYOUT STRUCTURE:
- Use a single-column backbone with occasional 2-column card grids for
  metrics and comparisons.
- Section padding: 24-32px vertical between sections.
- Card padding: 16-20px internal. Cards have subtle rounded corners (8-12px)
  and very light shadows.
- Max content width: centered, with 40-60px side margins.
- Visual rhythm: alternate between full-width sections, card grids, and
  text-with-chart panels to keep the reader engaged.
- Header/Hero: full-width gradient band (primary → secondary) with white
  title text, taking roughly 10-15% of poster height.
- Footer: thin line + small centered text at the very bottom."""


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_image_prompt(layout_plan: Dict[str, Any], query: str = "") -> str:
    """Build a rich, layered prompt for Gemini image generation.

    Follows the Paper2Slides 6-layer prompt architecture:
      Format → Style → Typography → Layout → Content → Visualization → Consistency
    """
    title = layout_plan.get("title", "Report")
    subtitle = layout_plan.get("subtitle", "")
    layout_type = layout_plan.get("layout_type", "infographic")
    colors = layout_plan.get("color_scheme", {})
    sections = layout_plan.get("sections", [])
    highlights = layout_plan.get("highlight_facts", [])
    key_stats = layout_plan.get("key_statistics", [])
    style_notes = layout_plan.get("style_notes", "")
    footer = layout_plan.get("footer_text", "Generated based on Webis")

    # Color values
    primary = colors.get("primary", "#5b7a94")
    secondary = colors.get("secondary", "#8ba4b8")
    accent = colors.get("accent", "#c49a6c")
    bg = colors.get("background", "#f7f5f2")
    text_dark = colors.get("text_dark", "#2d3436")
    text_light = colors.get("text_light", "#ffffff")

    parts: list[str] = []

    # ── Layer 1: FORMAT ──
    parts.append(_FORMAT_PREFIX)
    parts.append("")

    # ── Layer 2: STYLE ──
    parts.append(_STYLE_HINTS)
    parts.append("")
    parts.append(f"COLOR PALETTE for this poster:")
    parts.append(f"  Primary: {primary}  |  Secondary: {secondary}  |  Accent: {accent}")
    parts.append(f"  Background: {bg}  |  Dark text: {text_dark}  |  Light text: {text_light}")
    if style_notes:
        parts.append(f"Art direction: {style_notes}")
    parts.append("")

    # ── Layer 3: TYPOGRAPHY ──
    parts.append(_TYPOGRAPHY_RULES)
    parts.append("")

    # ── Layer 4: LAYOUT ──
    parts.append(_LAYOUT_RULES)
    parts.append("")

    # ── Layer 5: CONTENT (the actual poster content) ──
    parts.append("=" * 60)
    parts.append("POSTER CONTENT — Render all of the following:")
    parts.append("=" * 60)
    parts.append("")

    # Hero header
    parts.append(f'## HEADER / HERO SECTION')
    parts.append(f'Title: "{title}"')
    if subtitle:
        parts.append(f'Subtitle: "{subtitle}"')
    parts.append(
        f"Render as: full-width gradient band ({primary} → {secondary}), "
        f"white text, centered. Title in 48-64pt bold."
    )
    parts.append("")

    # Key statistics callout row (if available)
    if key_stats:
        parts.append("## KEY STATISTICS ROW (render as large stat cards)")
        for ks in key_stats[:6]:
            label = ks.get("label", "")
            value = ks.get("value", "")
            context = ks.get("context", "")
            parts.append(
                f"  [{value}] {label}"
                + (f" — {context}" if context else "")
            )
        parts.append(
            "Render each stat as a compact card with the VALUE in 36-48pt "
            "bold accent color and the LABEL in 12pt below."
        )
        parts.append("")

    # Sections
    for i, sec in enumerate(sections, 1):
        sid = sec.get("id", f"section_{i:02d}")
        heading = sec.get("heading", f"Section {i}")
        ctype = sec.get("content_type", "analysis")
        body = sec.get("body", "")
        bullets = sec.get("bullet_points", [])
        metrics = sec.get("metrics", [])
        data_table = sec.get("data_table", [])
        chart_type = sec.get("chart_type", "none")
        visual = sec.get("visual_hint", "")

        parts.append(f"## SECTION {i}: {heading} [{ctype}]")

        if body:
            # Include substantial body text — up to 400 chars
            parts.append(f"Content: {body[:400]}")

        if bullets:
            for b in bullets[:6]:
                parts.append(f"  • {str(b)[:150]}")

        if metrics:
            parts.append("  Key metrics:")
            for m in metrics[:6]:
                label = m.get("label", "")
                value = m.get("value", "")
                trend = m.get("trend", "")
                trend_str = f" (↑)" if trend == "up" else f" (↓)" if trend == "down" else ""
                parts.append(f"    {label}: {value}{trend_str}")

        if data_table:
            parts.append("  Data table:")
            for row in data_table[:5]:
                parts.append(f"    {row}")

        if chart_type and chart_type != "none":
            parts.append(
                f"  → Visualize with a {chart_type.upper()} CHART using accent colors. "
                f"Make the chart LARGE and clear."
            )

        if visual:
            parts.append(f"  Visual suggestion: {visual}")

        parts.append("")

    # Highlight facts
    if highlights:
        parts.append("## HIGHLIGHT CALLOUT BOXES")
        parts.append(
            "Render these as visually prominent callout boxes with accent "
            "background or border. Place them between relevant sections."
        )
        for h in highlights[:5]:
            parts.append(f'  ★ "{str(h)[:200]}"')
        parts.append("")

    # Footer
    parts.append(f'## FOOTER')
    parts.append(
        f'Text: "{footer}" — small (10pt), centered, muted grey, thin top border.'
    )
    parts.append("")

    # ── Layer 6: VISUALIZATION ──
    parts.append(_VISUALIZATION_HINTS)
    parts.append("")

    # ── Layer 7: CONSISTENCY ──
    parts.append(_CONSISTENCY_HINT)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Gemini API caller
# ---------------------------------------------------------------------------

class ImageRenderAgent:
    """Agent 2: render a poster image via Gemini image-generation model."""

    def __init__(self, api_key: str | None = None, endpoint: str | None = None):
        self._api_key = api_key or os.environ.get(_ENV_KEY, "")
        self._endpoint = endpoint or _GEMINI_URL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        layout_plan: Dict[str, Any],
        query: str = "",
        output_path: str | Path | None = None,
    ) -> tuple[bytes, str]:
        """Generate a poster image and return ``(raw_bytes, mime_type)``.

        If *output_path* is given the image is also written to disk.
        """
        if not self._api_key:
            raise RuntimeError(
                f"Image generation requires {_ENV_KEY} to be set. "
                "Please add it to your .env file."
            )

        prompt = _build_image_prompt(layout_plan, query)
        logger.info("Image prompt length: %d chars", len(prompt))
        logger.debug("Image prompt:\n%s", prompt[:2000])

        image_bytes, mime_type = self._call_gemini(prompt)

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(image_bytes)
            logger.info("Image saved to %s (%d bytes)", out, len(image_bytes))

        return image_bytes, mime_type

    # ------------------------------------------------------------------
    # Gemini API
    # ------------------------------------------------------------------

    def _call_gemini(self, prompt: str) -> tuple[bytes, str]:
        """Call the Gemini generateContent endpoint and extract the image.

        Returns ``(image_bytes, mime_type)``.
        """
        url = f"{self._endpoint}?key={self._api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["image", "text"],
            },
        }

        headers = {"Content-Type": "application/json"}

        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 2):
            try:
                logger.info(
                    "Gemini image request attempt %d/%d …",
                    attempt,
                    _MAX_RETRIES + 1,
                )
                resp = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=180,
                )

                if resp.status_code == 429:
                    wait = _RETRY_DELAY * attempt
                    logger.warning("Rate limited (429). Retrying in %ds…", wait)
                    time.sleep(wait)
                    continue

                if resp.status_code != 200:
                    error_text = resp.text[:500]
                    raise RuntimeError(
                        f"Gemini API returned {resp.status_code}: {error_text}"
                    )

                data = resp.json()
                return self._extract_image(data)

            except RuntimeError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning("Gemini call failed: %s", exc)
                if attempt <= _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY)

        raise RuntimeError(
            f"Gemini image generation failed after {_MAX_RETRIES + 1} attempts: "
            f"{last_error}"
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_image(response_json: Dict[str, Any]) -> tuple[bytes, str]:
        """Walk the Gemini response JSON and return ``(image_bytes, mime_type)``."""
        candidates = response_json.get("candidates", [])
        if not candidates:
            # Check for a promptFeedback block (safety filter)
            feedback = response_json.get("promptFeedback", {})
            block_reason = feedback.get("blockReason", "")
            if block_reason:
                raise RuntimeError(
                    f"Gemini blocked the request: {block_reason}. "
                    f"Feedback: {json.dumps(feedback, ensure_ascii=False)}"
                )
            raise RuntimeError(
                "Gemini returned no candidates. Full response: "
                + json.dumps(response_json, ensure_ascii=False)[:1000]
            )

        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                inline_data = part.get("inlineData")
                if inline_data and inline_data.get("data"):
                    mime = inline_data.get("mimeType", "image/png")
                    b64 = inline_data["data"]
                    image_bytes = base64.b64decode(b64)
                    logger.info(
                        "Extracted image: mime=%s, size=%d bytes",
                        mime,
                        len(image_bytes),
                    )
                    return image_bytes, mime

        # No image part found — dump text parts for debugging
        text_parts = []
        for candidate in candidates:
            for part in candidate.get("content", {}).get("parts", []):
                if "text" in part:
                    text_parts.append(part["text"][:500])

        raise RuntimeError(
            "Gemini response contained no image data. "
            f"Text parts: {text_parts[:3]}"
        )
