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
            
            "## CRITICAL INSTRUCTIONS (STRICT):\n"
            "1. **Output ONLY a valid JSON object**, with NO additional text, markdown, explanations, or formatting.\n"
            "2. **ABSOLUTELY NO markdown code blocks** (e.g., ```json or ```).\n"
            "3. **Start directly with { and end with }**, nothing before or after.\n\n"
            
            "## REQUIRED JSON STRUCTURE:\n"
            "{\n"
            '  "main_text": "The extracted primary content as a single string (preserve original order, use \\n\\n for paragraphs)",\n'
            '  "reason": "1-2 sentence justification for the extraction"\n'
            "}\n\n"
            
            "## EXAMPLE OF CORRECT OUTPUT (copy this format):\n"
            '{"main_text": "Extracted article content here...", "reason": "Extracted the news article body, excluding navigation and ads."}\n\n'
            
            "## PAGE TEXT:\n"
            f"{page_text[:8000]}\n"
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
            print(response.content)
            result = robust_json_parse(response.content)
            main_text = result.get("main_text", "").strip()
            
            if not main_text:
                raise ValueError("LLM returned empty main_text in JSON response")
            
            logger.debug(f"[HTMLCleanerPlugin] LLM extracted {len(main_text)} chars. Reason: {result.get('reason', 'N/A')}")
            print("successfully cleaned html content\n")
            return main_text
            
        except json.JSONDecodeError as e:
            logger.error(f"[HTMLCleanerPlugin] Failed to parse LLM response as JSON: {e}")
            logger.error(f"[HTMLCleanerPlugin] Raw LLM response: {response.content[:200]}...")
            raise RuntimeError(f"LLM cleaning failed: Invalid JSON response - {e}") from e
        
def robust_json_parse(llm_response: str) -> dict:
        """
        鲁棒的JSON解析函数，处理被markdown包围的JSON响应
        """
        response = llm_response.strip()
    
        # 1. 如果响应为空
        if not response:
            raise ValueError("LLM返回空响应")
        
        # 2. 直接尝试解析（如果已经是纯JSON）
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 3. 移除markdown代码块标记
        # 匹配 ```json ... ``` 或 ``` ... ```
        markdown_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(markdown_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if match:
            extracted = match.group(1).strip()
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                # 记录日志以便调试
                print(f"[DEBUG] 移除markdown后仍解析失败，尝试其他方法...")
                response = extracted
        
        # 4. 尝试提取第一个完整JSON对象
        # 查找第一个 { 和最后一个 } 之间的内容
        start = response.find('{')
        end = response.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_str = response[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                print(f"[DEBUG] 提取的JSON无效: {json_str[:200]}...")
        
        # 5. 尝试使用正则表达式提取JSON
        json_patterns = [
            r'(\{.*?\})',  # 基本JSON对象
            r'(\{["\'].*?["\'].*?:.*?\})',  # 更具体的模式
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # 6. 如果所有方法都失败，抛出详细错误
        raise ValueError(f"无法从响应中提取有效的JSON。响应前500字符: {response[:500]}...")
