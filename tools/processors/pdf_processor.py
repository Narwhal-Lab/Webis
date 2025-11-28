#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Processor
Process PDF files
"""

import logging
from typing import Dict, Union
from .base_processor import BaseFileProcessor

logger = logging.getLogger(__name__)


class PDFProcessor(BaseFileProcessor):
    """PDF Processor - Process PDF files"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.pdf'}
    
    def get_processor_name(self) -> str:
        """Get processor name"""
        return "PDFProcessor"
    
    def get_supported_extensions(self) -> set:
        """Get supported file extensions"""
        return self.supported_extensions
    
    def extract_text(self, file_path: str) -> Dict[str, Union[str, bool]]:
        """
        Extract PDF text
        
        Args:
            file_path: PDF file path
            
        Returns:
            Dict containing: success(bool), text(str), error(str)
        """
        try:
            from langchain_community.document_loaders import PyPDFLoader
            
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            
            # Organize text by page
            text_parts = []
            for i, doc in enumerate(docs, 1):
                page_text = doc.page_content.strip()
                if page_text:
                    text_parts.append(f"--- Page {i} ---\n{page_text}")
            
            text = "\n\n".join(text_parts)
            
            logger.info(f"[PDFProcessor] Successfully processed PDF: {file_path}, pages: {len(docs)}, text length: {len(text)}")
            return {"success": True, "text": text, "error": ""}
            
        except ImportError as e:
            error_msg = f"Missing dependency: {str(e)}. Please install: pip install langchain-community pypdf"
            logger.error(f"[PDFProcessor] {error_msg}")
            return {"success": False, "text": "", "error": error_msg}
        except Exception as e:
            error_msg = f"Failed to process PDF: {str(e)}"
            logger.error(f"[PDFProcessor] Failed to process PDF {file_path}: {str(e)}")
            return {"success": False, "text": "", "error": error_msg}
