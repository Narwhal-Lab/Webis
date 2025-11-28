#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Processor Interface
Defines common interface for all file processors
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Union
import os
import pathlib


class BaseFileProcessor(ABC):
    """Base File Processor - Defines unified interface"""
    
    def __init__(self):
        self.supported_extensions = set()
    
    @abstractmethod
    def get_processor_name(self) -> str:
        """Get processor name"""
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> set:
        """Get supported file extensions"""
        pass
    
    def can_process(self, file_path: str) -> bool:
        """
        Check if file type is supported
        
        Args:
            file_path: File path
            
        Returns:
            bool: Whether the file can be processed
        """
        ext = pathlib.Path(file_path).suffix.lower()
        return ext in self.get_supported_extensions()
    
    def validate_file(self, file_path: str) -> Dict[str, Union[str, bool]]:
        """
        Validate file exists and can be processed
        
        Args:
            file_path: File path
            
        Returns:
            Dict: Validation result
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        
        if not self.can_process(file_path):
            ext = pathlib.Path(file_path).suffix.lower()
            return {"success": False, "error": f"Unsupported file type: {ext}"}
        
        return {"success": True, "error": ""}
    
    @abstractmethod
    def extract_text(self, file_path: str) -> Dict[str, Union[str, bool]]:
        """
        Extract text from file
        
        Args:
            file_path: File path
            
        Returns:
            Dict containing: success(bool), text(str), error(str), processor(str)
        """
        pass
    
    def process_file(self, file_path: str) -> Dict[str, Union[str, bool]]:
        """
        Complete file processing workflow (includes validation)
        
        Args:
            file_path: File path
            
        Returns:
            Dict containing: success(bool), text(str), error(str), processor(str)
        """
        # Validate file
        validation = self.validate_file(file_path)
        if not validation["success"]:
            return {
                "success": False,
                "text": "",
                "error": validation["error"],
                "processor": self.get_processor_name()
            }
        
        # Process file
        result = self.extract_text(file_path)
        result["processor"] = self.get_processor_name()
        return result
