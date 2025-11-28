#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image OCR Processor
Process image files and perform text recognition
"""

import logging
from typing import Dict, Union
from .base_processor import BaseFileProcessor

logger = logging.getLogger(__name__)


class ImageProcessor(BaseFileProcessor):
    """Image OCR Processor - Uses EasyOCR"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
        self._reader = None
    
    def get_processor_name(self) -> str:
        """Get processor name"""
        return "ImageProcessor"
    
    def get_supported_extensions(self) -> set:
        """Get supported file extensions"""
        return self.supported_extensions
    
    def _get_reader(self):
        """Lazy load EasyOCR to avoid loading model at startup"""
        if self._reader is None:
            try:
                import easyocr
                logger.info("[ImageProcessor] Initializing EasyOCR model...")
                self._reader = easyocr.Reader(['ch_sim', 'en'])
                logger.info("[ImageProcessor] EasyOCR model initialization completed")
            except ImportError:
                raise ImportError("Please install easyocr: pip install easyocr")
        return self._reader
    
    def extract_text(self, file_path: str) -> Dict[str, Union[str, bool]]:
        """
        Extract text from image
        
        Args:
            file_path: Image file path
            
        Returns:
            Dict containing: success(bool), text(str), error(str)
        """
        try:
            reader = self._get_reader()
            results = reader.readtext(file_path)
            
            # Extract all recognized text
            text_lines = []
            for (bbox, text, confidence) in results:
                if confidence > 0.5:  # Filter low confidence results
                    text_lines.append(text.strip())
            
            text = "\n".join(text_lines)
            
            logger.info(f"[ImageProcessor] Successfully processed image: {file_path}, recognized {len(text_lines)} lines, text length: {len(text)}")
            return {"success": True, "text": text, "error": ""}
            
        except ImportError as e:
            error_msg = f"Missing dependency: {str(e)}. Please install: pip install easyocr"
            logger.error(f"[ImageProcessor] {error_msg}")
            return {"success": False, "text": "", "error": error_msg}
        except Exception as e:
            error_msg = f"Failed to process image: {str(e)}"
            logger.error(f"[ImageProcessor] Failed to process image {file_path}: {str(e)}")
            return {"success": False, "text": "", "error": error_msg}
