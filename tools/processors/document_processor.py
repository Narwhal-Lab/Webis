#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Processor
Process doc/docx/txt/md files
"""

import logging
from typing import Dict, Union
from .base_processor import BaseFileProcessor

logger = logging.getLogger(__name__)


class DocumentProcessor(BaseFileProcessor):
    """Document Processor - Process doc/docx/txt/md files"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.doc', '.docx', '.txt', '.md'}
    
    def get_processor_name(self) -> str:
        """Get processor name"""
        return "DocumentProcessor"
    
    def get_supported_extensions(self) -> set:
        """Get supported file extensions"""
        return self.supported_extensions
    
    def extract_text(self, file_path: str) -> Dict[str, Union[str, bool]]:
        """
        Extract document text
        
        Args:
            file_path: File path
            
        Returns:
            Dict containing: success(bool), text(str), error(str)
        """
        try:
            from langchain_community.document_loaders import Docx2txtLoader, TextLoader
            import pathlib
            
            ext = pathlib.Path(file_path).suffix.lower()
            
            if ext in [".docx", ".doc"]:
                # Use same tool for both .docx and .doc files
                loader = Docx2txtLoader(file_path)
                docs = loader.load()
            elif ext in [".txt", ".md"]:
                loader = TextLoader(file_path, encoding="utf-8")
                docs = loader.load()
            else:
                return {"success": False, "text": "", "error": f"Unsupported file type: {ext}"}
            
            # Merge all document content
            text = "\n".join(doc.page_content for doc in docs).strip()
            
            logger.info(f"[DocumentProcessor] Successfully processed document: {file_path}, text length: {len(text)}")
            return {"success": True, "text": text, "error": ""}
            
        except ImportError as e:
            error_msg = f"Missing dependency: {str(e)}. Please install: pip install langchain-community docx2txt"
            logger.error(f"[DocumentProcessor] {error_msg}")
            return {"success": False, "text": "", "error": error_msg}
        except Exception as e:
            error_msg = f"Failed to process document: {str(e)}"
            logger.error(f"[DocumentProcessor] Failed to process document {file_path}: {str(e)}")
            return {"success": False, "text": "", "error": error_msg}
