#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 Processor Module
Contains processors for all file types
"""

from .base_processor import BaseFileProcessor
from .document_processor import DocumentProcessor
from .pdf_processor import PDFProcessor
from .image_processor import ImageProcessor
from .html_processor import HTMLProcessor

__all__ = [
    'BaseFileProcessor',
    'DocumentProcessor', 
    'PDFProcessor',
    'ImageProcessor',
    'HTMLProcessor'
]
