#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML Processor (Integrated with Webis_HTML library)
Dependency: webis-html (install via pip install webis-html)
"""

from typing import Dict, Union, Set
from .base_processor import BaseFileProcessor
import os
import tempfile

try:
    import webis_html
except ImportError:
    webis_html = None

class HTMLProcessor(BaseFileProcessor):
    """HTML File Processor (Based on Webis_HTML library)"""
    def __init__(self, api_key: str = None):
        super().__init__()
        self.supported_extensions = {".html", ".htm"}
        # Prefer DEEPSEEK_API_KEY from environment variables if exists, otherwise use provided api_key
        self.api_key = os.environ.get("DEEPSEEK_API_KEY") or api_key
    
    def get_processor_name(self) -> str:
        return "HTMLProcessor"
    
    def get_supported_extensions(self) -> Set[str]:
        return self.supported_extensions
    
    def extract_text(self, file_path: str) -> Dict[str, Union[str, bool]]:
        if not os.path.exists(file_path):
            return {"success": False, "text": "", "error": f"File not found: {file_path}"}
        
        if webis_html is None:
            return {
                "success": False, 
                "text": "", 
                "error": "webis_html module not installed. Please run: pip install webis-html"
            }
        
        try:
            # Ensure API key is available before execution
            if not self.api_key:
                return {
                    "success": False,
                    "text": "",
                    "error": (
                        "DeepSeek API key not detected (DEEPSEEK_API_KEY environment variable not set, "
                        "and not provided in constructor). Please set DEEPSEEK_API_KEY environment variable "
                        "or pass api_key when creating HTMLProcessor."
                    ),
                }

            # Read HTML file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Create temporary output directory
            with tempfile.TemporaryDirectory() as temp_output_dir:
                # Call webis_html library function with determined API key
                result = webis_html.extract_from_html(
                    html_content=html_content,
                    api_key=self.api_key,
                    output_dir=temp_output_dir
                )
                
                if not result.get("success", False):
                    error_msg = result.get("error", "Unknown error")
                    return {"success": False, "text": "", "error": f"Extraction failed: {error_msg}"}
                
                # Merge all result texts
                results = result.get("results", [])
                if not results:
                    return {"success": False, "text": "", "error": "No content extracted"}
                
                # Merge all text content
                text_parts = []
                for item in results:
                    content = item.get("content", "")
                    if content:
                        text_parts.append(content)
                
                extracted_text = "\n\n".join(text_parts)
                
                return {
                    "success": True,
                    "text": extracted_text,
                    "error": "",
                    "meta": {
                        "output_dir": result.get("output_dir", ""),
                        "file_count": len(results)
                    }
                }
                
        except Exception as e:
            return {"success": False, "text": "", "error": f"Processing failed: {str(e)}"}
