"""
Report Assembly Agent — Agent 3/3

Receives the *analysis pack* (Agent 1) and the *presentation pack*
(Agent 2), then asks the LLM to compose a complete, standalone HTML
page.

When the LLM succeeds, its output is used directly (after basic
sanitisation).  When it fails, a deterministic renderer builds
a beautiful HTML page using the CSS theme from Agent 2.

The LLM has full creative freedom over the HTML structure — no
fixed template is imposed.
"""

from __future__ import annotations

import html as html_mod
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

from webis.core.llm.base import get_default_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for HTML generation
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\You are a talented front-end developer and visual storyteller.  You create
HTML reports that are **both content-rich AND visually engaging** — they
should feel like premium digital publications that people actually enjoy
reading, not dry corporate documents.

You will receive two JSON objects:
1. **analysis_pack** — the report content (structure varies per report)
2. **presentation_pack** — a visual theme including a `css_theme` stylesheet

Produce a **complete, standalone HTML document** that combines the content
with the visual design into a clean, professional web page.

## Rules
1. Output ONLY raw HTML — no markdown fences, no explanations.
2. Start with `<!DOCTYPE html>` and end with `</html>`.
3. Embed ALL CSS inside a `<style>` tag in `<head>`.
4. The page must be self-contained — no external deps except Google
   Fonts `@import` if present in the CSS.
5. **Include ALL content** from the analysis_pack — do not skip any
   data.  The report should feel dense and thorough.
6. No external JS frameworks.  Minimal vanilla JS is OK (counters,
   toggles).

## 🎨 Colour (COHESIVE & ENGAGING)
- Embrace the CSS theme palette — use its full range, don't flatten it.
- Section backgrounds: vary between white, light tints, and occasional
  **deeper-toned highlight sections** (e.g. a dark hero banner, a
  coloured callout strip) to create visual interest and rhythm.
- Use accent colours generously on headings, stat numbers, card borders,
  icons, and highlight boxes.
- Cards: accent-coloured borders or subtle gradient backgrounds with
  moderate shadows for depth.
- Gradient text on the main H1 title is OK if it enhances the design.
- The page should feel **colourful and alive** while remaining readable.

## 📐 Layout (COMPACT BUT WITH VISUAL RHYTHM)
- Use a centred container, **max-width 850–950px**.
- **Tight spacing** overall: section padding `1.2–1.5rem 0`, card
  padding `0.8–1rem`, paragraph margin `0.5–0.7em 0`.
- Layout does NOT need to be strictly sequential — allow **visual
  rhythm variation**: mix full-width sections, 2-column card grids,
  sidebar callouts, and highlight panels to keep the reader engaged.
- Stat cards in a compact row (flexbox, gap 0.8rem); use 3–5 cards.
- Occasional layout shifts are welcome — e.g. a key finding panel
  that breaks slightly wider, or a quote floated to one side.
- Two-column grid for card groups; mixed layouts between sections.

## 🖼️ Illustrations & Graphics (BRING THE PAGE TO LIFE)
- **Hero illustration**: create an **inline SVG illustration** (200–
  350px) in the hero section that visually represents the report topic.
  Use SVG paths, shapes, gradients — make it colourful and relevant.
- **Section icons**: inline SVG icons or expressive emoji (30–40px)
  before each section heading.
- **Decorative dividers**: SVG wave patterns, gradient bars, geometric
  accents, or ornamental lines between sections — not plain `<hr>`.
- **Data visualisations**: inline SVG bar charts, donut charts, progress
  rings, or gauges for numeric data.  Size them appropriately (200–
  350px wide).
- **Background accents**: subtle SVG shapes (floating circles, dots,
  abstract patterns) as position:absolute decorations behind key
  sections — adds depth and visual interest.
- **Pull-quote callouts**: visually distinctive boxes for key facts or
  surprising data points — large quotation marks, accent backgrounds.

## 🔤 Typography (CLEAN BODY, EYE-CATCHING HEADINGS)
- Use the Google Fonts from the CSS theme.
- **H1**: 2.5–3.2rem, **bold or black weight**, primary colour.
  Use tight `letter-spacing: -0.02em` for a modern feel.  A subtle
  `text-shadow` or decorative underline is encouraged to make the
  main title stand out and be memorable.
- **H2**: 1.4–1.7rem, semibold, with a coloured underline or left
  accent border — headings should draw the reader's eye.
- **Body**: 0.95rem, line-height 1.65, colour `#333`.  Keep body
  text clean and easy to read.
- Blockquotes: 3px left border in accent colour, italic, indented.
- Code/data labels: monospace, slightly smaller.

## 📊 Data Presentation (RICH & VARIED)
- **Bar charts**: CSS horizontal bars with coloured fills and labels.
- **Donut / pie charts**: CSS `conic-gradient()` or inline SVG.
- **Stat cards**: large bold numbers with coloured backgrounds or
  accent borders — make key numbers impossible to miss.
- **Progress rings**: SVG circles with `stroke-dasharray` for
  percentage visualisation.
- **Tables**: styled with alternating rows, hover effects, and
  accent-coloured header rows.
- **Timelines**: vertical line with coloured nodes and content cards.
- **Tags/badges**: coloured pills that match the section theme.
- Choose the **most visually engaging** format for each data set.

## ✨ Motion & Interactivity
- Page fade-in on load (opacity 0→1, 0.4s).
- Cards: hover lift + shadow deepening (250ms ease).
- Hero: subtle gradient colour-shift or floating SVG animation.
- Stat counters: JS count-up animation when visible (optional).
- Collapsible detail sections with `<details>/<summary>` for dense
  subsections (optional).
- Keep motion **tasteful** — enhance, don't overwhelm.

## 🏷️ Footer Branding (MANDATORY)
- At the very bottom of the page, add a footer with the text:
  **"Generated based on Webis"**
- Style: centred, small font (0.8rem), muted grey colour, with a
  thin top border (`1px solid #e0e0e0`).  Padding `1.5rem 0`.
- Use the CSS class `.webis-footer` from the theme if available.

Overall goal: every report should feel **thorough, information-rich,
AND visually delightful**.  It should have personality — the design,
illustrations, and colour choices should feel inspired by the topic.
A reader should think "this looks great" within the first second, and
"this is really informative" after reading.  Balance substance with style.
"""


class ReportAssemblyAgent:
    """Agent 3: assemble the final HTML report."""

    def run(
        self,
        analysis_pack: Dict[str, Any],
        presentation_pack: Dict[str, Any],
        query: str = "",
    ) -> str:
        """Return a complete HTML string."""
        html = self._call_llm(analysis_pack, presentation_pack, query)
        html = self._post_process(html)
        return html

    # ------------------------------------------------------------------
    def _call_llm(
        self,
        analysis_pack: Dict[str, Any],
        presentation_pack: Dict[str, Any],
        query: str,
    ) -> str:
        """Ask the LLM to generate the full HTML page."""
        # Prepare clean copies for the prompt
        analysis_for_prompt = {k: v for k, v in analysis_pack.items()}
        presentation_for_prompt = {
            k: v for k, v in presentation_pack.items()
            if k != "css_theme"  # exclude large CSS from token usage
        }

        user_msg = (
            "Generate a complete HTML report page.\n\n"
            f"**analysis_pack:**\n```json\n"
            f"{json.dumps(analysis_for_prompt, ensure_ascii=False, indent=2)[:12000]}\n```\n\n"
            f"**presentation_pack (meta):**\n```json\n"
            f"{json.dumps(presentation_for_prompt, ensure_ascii=False, indent=2)}\n```\n\n"
            f"**css_theme:**\n```css\n"
            f"{presentation_pack.get('css_theme', '')}\n```\n\n"
            "Use the css_theme as-is inside a <style> tag.  "
            "Apply the CSS class names in your HTML.  "
            "Include every section from the analysis_pack.  "
            "Make the page visually stunning."
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        try:
            router = get_default_router()
            resp = router.chat(messages, use_cache=False)
            text = resp.content.strip()

            # Strip markdown fences if the model wrapped its output
            if text.startswith("```"):
                first_nl = text.index("\n")
                text = text[first_nl + 1:]
            if text.endswith("```"):
                text = text[:-3].rstrip()

            # Validate it looks like HTML
            if "<html" in text.lower() and "</html>" in text.lower():
                logger.info("LLM HTML generation succeeded (%d chars)", len(text))
                return text
            else:
                logger.warning("LLM output doesn't look like valid HTML, using fallback")
                return self._render_deterministic(analysis_pack, presentation_pack)

        except Exception as exc:
            logger.warning("LLM HTML generation failed (%s), using fallback", exc)
            return self._render_deterministic(analysis_pack, presentation_pack)

    # ------------------------------------------------------------------
    # Deterministic fallback renderer
    # ------------------------------------------------------------------

    def _render_deterministic(
        self,
        analysis: Dict[str, Any],
        presentation: Dict[str, Any],
    ) -> str:
        """Build a beautiful HTML page without an LLM call.

        Uses the CSS theme from the presentation pack and renders all
        analysis_pack content into well-structured HTML with the theme's
        class names.
        """
        css = presentation.get("css_theme", "")
        title = html_mod.escape(str(analysis.get("report_title", "Research Report")))
        subtitle = html_mod.escape(str(analysis.get("subtitle", "")))
        exec_summary = analysis.get("executive_summary", "")
        findings = analysis.get("key_findings", [])
        data_points = analysis.get("data_points", [])
        sections = analysis.get("sections", [])
        conclusions = analysis.get("conclusions", "")
        sources = analysis.get("sources", [])

        parts: List[str] = []

        # DOCTYPE + head
        parts.append(f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
""")

        # Hero
        parts.append(f"""\
<header class="report-hero">
  <h1>{title}</h1>
  <p class="subtitle">{subtitle}</p>
</header>
""")

        parts.append('<main class="report-container">\n')

        # Executive Summary
        if exec_summary:
            parts.append(f"""\
<div class="executive-summary">
  {self._text_to_paragraphs(exec_summary)}
</div>
""")

        # Key Findings
        if findings:
            items = []
            for i, f in enumerate(findings, 1):
                items.append(
                    f'<div class="finding-item">'
                    f'<span class="finding-badge">{i}</span>'
                    f'<span class="finding-text">{html_mod.escape(str(f))}</span>'
                    f'</div>'
                )
            parts.append(f"""\
<div class="findings-section">
  <h2>Key Findings</h2>
  {"".join(items)}
</div>
""")

        # Data Points
        if data_points:
            cards = []
            for dp in data_points:
                label = html_mod.escape(str(dp.get("label", "")))
                value = html_mod.escape(str(dp.get("value", "")))
                desc = html_mod.escape(str(dp.get("description", "")))
                cards.append(
                    f'<div class="data-card">'
                    f'<div class="data-value">{value}</div>'
                    f'<div class="data-label">{label}</div>'
                    f'<div class="data-desc">{desc}</div>'
                    f'</div>'
                )
            parts.append(f"""\
<div class="data-grid">
  {"".join(cards)}
</div>
""")

        # Content Sections
        for sec in sections:
            heading = html_mod.escape(str(sec.get("heading", "")))
            content = sec.get("content", "")
            highlights = sec.get("highlights", [])

            hl_html = ""
            if highlights:
                hl_items = "".join(
                    f"<li>{html_mod.escape(str(h))}</li>" for h in highlights if h
                )
                if hl_items:
                    hl_html = f"<ul>{hl_items}</ul>"

            parts.append(f"""\
<section class="report-section">
  <h2>{heading}</h2>
  {self._text_to_paragraphs(content)}
  {hl_html}
</section>
""")

        # Conclusions
        if conclusions:
            parts.append(f"""\
<div class="conclusions-section">
  <h2>Conclusions</h2>
  {self._text_to_paragraphs(conclusions)}
</div>
""")

        # Sources
        if sources:
            items = []
            for s in sources:
                s_title = html_mod.escape(str(s.get("title", s.get("url", ""))))
                s_url = html_mod.escape(str(s.get("url", "")))
                if s_url:
                    items.append(f'<li><a href="{s_url}" target="_blank">{s_title}</a></li>')
                else:
                    items.append(f'<li>{s_title}</li>')
            parts.append(f"""\
<div class="source-list">
  <h2>Sources</h2>
  <ol>{"".join(items)}</ol>
</div>
""")

        # Also render any extra keys the LLM added
        known_keys = {
            "report_title", "subtitle", "executive_summary",
            "key_findings", "data_points", "sections",
            "conclusions", "sources",
        }
        extra_keys = [k for k in analysis if k not in known_keys]
        for key in extra_keys:
            val = analysis[key]
            if not val:
                continue
            heading = html_mod.escape(key.replace("_", " ").title())
            parts.append(f'<section class="report-section"><h2>{heading}</h2>')
            parts.append(self._render_value(val))
            parts.append('</section>\n')

        # Footer
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        parts.append(f"""\
</main>
<footer class="report-footer">
  Generated on {now} &mdash; Powered by Webis Intelligence Pipeline
</footer>
</body>
</html>
""")

        return "".join(parts)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _text_to_paragraphs(text: str) -> str:
        """Convert plain text with blank-line breaks into <p> tags."""
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return ""
        paragraphs = re.split(r"\n{2,}", text)
        return "".join(f"<p>{html_mod.escape(p.strip())}</p>" for p in paragraphs if p.strip())

    @staticmethod
    def _render_value(val: Any) -> str:
        """Render an arbitrary Python value to HTML."""
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return ""
            paras = re.split(r"\n{2,}", val)
            return "".join(f"<p>{html_mod.escape(p.strip())}</p>" for p in paras if p.strip())

        if isinstance(val, list):
            if not val:
                return ""
            # List of dicts → cards
            if isinstance(val[0], dict):
                cards = []
                for item in val:
                    inner = "".join(
                        f"<div><strong>{html_mod.escape(str(k))}:</strong> "
                        f"{html_mod.escape(str(v))}</div>"
                        for k, v in item.items()
                    )
                    cards.append(f'<div class="report-card">{inner}</div>')
                return "".join(cards)
            # List of strings → bullet list
            items = "".join(f"<li>{html_mod.escape(str(i))}</li>" for i in val)
            return f"<ul>{items}</ul>"

        if isinstance(val, dict):
            rows = "".join(
                f"<tr><td><strong>{html_mod.escape(str(k))}</strong></td>"
                f"<td>{html_mod.escape(str(v))}</td></tr>"
                for k, v in val.items()
            )
            return f'<table class="report-table"><tbody>{rows}</tbody></table>'

        return f"<p>{html_mod.escape(str(val))}</p>"

    # ------------------------------------------------------------------
    @staticmethod
    def _post_process(html_str: str) -> str:
        """Light-touch validation and cleanup."""
        if not html_str or not html_str.strip():
            return "<html><body><p>Report generation failed.</p></body></html>"

        # Ensure DOCTYPE
        if "<!DOCTYPE" not in html_str[:100].upper():
            html_str = "<!DOCTYPE html>\n" + html_str

        # Ensure closing tag
        if "</html>" not in html_str[-50:].lower():
            html_str += "\n</html>"

        return html_str
