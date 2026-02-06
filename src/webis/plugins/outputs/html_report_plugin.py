
import json
import os
import re
import datetime
from typing import List, Union, Any, Dict, Optional

from webis.core.plugin import OutputPlugin
from webis.core.schema import WebisDocument, StructuredResult, PipelineContext
from webis.core.llm.base import get_default_router

class HtmlReportPlugin(OutputPlugin):
    """
    Generates a beautiful HTML report from pipeline results using LLM generation.
    """
    name = "html_report"
    description = "Generates a standalone HTML report by asking an LLM to render the data."

    def save(
        self,
        data: Union[StructuredResult, List[Any]],
        context: Optional[PipelineContext] = None,
        output_dir: Optional[str] = None,
        **kwargs
    ) -> bool:
        if not output_dir:
            return False
            
        # Prepare content for the LLM
        result_data = {}
        documents = []
        task_name = "Webis Task"
        
        if context:
            task_name = context.task
            
        if isinstance(data, StructuredResult):
            result_data = data.data
            documents = kwargs.get("documents", [])
        elif isinstance(data, list):
            if data and isinstance(data[0], WebisDocument):
                documents = data
                result_data = {"info": "Raw document list"}
            else:
                result_data = {"data": data}
        else:
             result_data = data
             
        # Generate HTML using LLM
        html_content = self._generate_with_llm(task_name, result_data, documents)
        
        # Save
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "report.html")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        return True

    def _generate_with_llm(self, task: str, data: Dict, docs: List[WebisDocument]) -> str:
        """
        Uses LLM to write the HTML code dynamically.
        """
        # 1. Prepare Content Context
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        # Summarize sources to avoid hitting token limits
        sources_summary = []
        for i, doc in enumerate(docs[:10]): # Limit to top 10 sources
            title = doc.meta.title or f"Source {i+1}"
            url = doc.meta.url or "#"
            sources_summary.append(f"- [{title}]({url})")
        
        sources_text = "\n".join(sources_summary)

        # 2. Construct Prompt (Migrated from demo_html.py)
        system_prompt = """You are a professional web developer. Generate valid, complete, standalone HTML5 code.
        
        CRITICAL REQUIREMENTS:
        1. Start with <!DOCTYPE html> and end with </html>
        2. Use modern, clean UI (Tailwind or inline CSS).
        3. Visualize the "Core Content" effectively (cards, tables, or lists).
        4. Add a footer section with:
           - Dark background (dark gray/black, e.g., #2b2d42 or #1a1a1a)
           - Two-column layout for data sources
           - Blue headings (e.g., "Reference Sources" and "Additional Resources")
           - Light gray text for source items
           - "Generated based on Webis" at the very bottom in small, subtle style
        5. NO explanations, NO markdown fences (```html). JUST the raw HTML code.
        6. Ensure all tags are properly closed.
        """

        user_content = f"""
Task Objective: {task}

Core Data (JSON):
{json_str}

Reference Sources:
{sources_text}
"""

        user_prompt = f"""Task: {task}
        
        Core Content:
        {user_content}
        
        Requirements:
        - Create a beautiful, modern HTML page
        - Add a dark footer section (dark gray/black background) with:
          * Two columns: "Reference Sources" (left) and "Additional Resources" (right)
          * Blue section headings
          * Light gray text for source items from the provided reference sources
          * Split the reference sources evenly between the two columns
          * At the very bottom: "Generated based on Webis" in small, centered, subtle text
        - Make the main content visually appealing with cards or modern layout
        
        Generate the HTML now."""

        # 3. Call LLM
        try:
            router = get_default_router()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Using the same model parameters as demo_html.py
            response = router.chat(
                messages,
                model="deepseek-v3.2",
                temperature=0.7,
                max_tokens=4000
            )
            raw_html = response.content
            
        except Exception as e:
            # Fallback if generation fails
            print(f"LLM Generation failed: {e}")
            return f"<html><body><h1>Error Generating Report</h1><p>{e}</p></body></html>"

        # 4. Sanitize, Validate, Repair (if needed)
        sanitized_html = self._sanitize_html(raw_html)
        issues = self._validate_html(sanitized_html)
        if issues:
            try:
                repaired_html = self._repair_html(router, sanitized_html, issues)
                sanitized_html = self._sanitize_html(repaired_html)
            except Exception as e:
                print(f"LLM Repair failed: {e}")

        return sanitized_html

    def _strip_markdown_fences(self, text: str) -> str:
        stripped = text.strip()
        m = re.search(r"```(?:html)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()[1:]
            stripped = "\n".join(lines)
            stripped = re.sub(r"\n```\s*$", "", stripped)
            return stripped.strip()
        return stripped

    def _sanitize_html(self, html: str) -> str:
        s = self._strip_markdown_fences(html)

        s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

        # Fix common model glitch patterns like '<< section ...' and '< / div >'
        s = re.sub(r"<<\s*/\s*([A-Za-z])", r"</\1", s)
        s = re.sub(r"<<\s*([A-Za-z])", r"<\1", s)

        s = re.sub(r"<\s*/\s*([A-Za-z][\w:-]*)\s*>", r"</\1>", s)
        s = re.sub(r"<\s+([!/A-Za-z])", r"<\1", s)

        attrs = r"(?:class|id|href|src|style|lang|type|rel|name|content|crossorigin|role)"
        s = re.sub(rf"(<\s*/?\s*)([A-Za-z][\w:-]*?)({attrs})\s*=", r"\1\2 \3=", s)
        s = re.sub(r"(<\s*/?\s*)([A-Za-z][\w:-]*?)(aria-[\w-]+)\s*=", r"\1\2 \3=", s)

        s = re.sub(r'(\s[\w:-]+)\s*=\s*"', r'\1="', s)

        def _normalize_style_block(m: re.Match) -> str:
            style = m.group(1)
            style = (
                style.replace("：", ":")
                .replace("；", ";")
                .replace("（", "(")
                .replace("）", ")")
                .replace("，", ",")
            )
            style = re.sub(r"\b(var|calc|rgba|rgb)\s*\(\s*", r"\1(", style)
            style = re.sub(r"\(\s*--", "(--", style)
            return f"<style>{style}</style>"

        s = re.sub(r"<style[^>]*>(.*?)</style>", _normalize_style_block, s, flags=re.DOTALL | re.IGNORECASE)
        return s.strip()

    def _validate_html(self, html: str) -> List[str]:
        issues = []
        if "<!DOCTYPE html" not in html and "<!doctype html" not in html:
            issues.append("missing_doctype")
        if "</html>" not in html.lower():
            issues.append("missing_html_close")
        if re.search(r"<<\s*/?\s*[A-Za-z]", html):
            issues.append("double_angle_brackets_in_tags")
        if "```" in html:
            issues.append("markdown_fence_remaining")
        if any(ch in html for ch in ["“", "”", "‘", "’"]):
            issues.append("curly_quotes_remaining")
        return issues

    def _repair_html(self, router, broken_html: str, issues: List[str]) -> str:
        system_prompt = (
            "You are an HTML Repair Expert. "
            f"The following HTML has issues: {', '.join(issues)}.\n\n"
            "Please fix the HTML so it is valid HTML5.\n"
            "- Ensure <!DOCTYPE html> is present.\n"
            "- Fix broken tags.\n"
            "- Remove markdown fences.\n"
            "- Return ONLY the fixed HTML."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": broken_html},
        ]
        response = router.chat(
            messages,
            model="deepseek-v3.2",
            temperature=0.1,
            max_tokens=8000
        )
        return response.content
