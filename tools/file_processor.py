
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified File Processing Interface
Supports text extraction from documents, PDFs, images, and HTML
"""

import os
import pathlib
from typing import Dict, List, Optional, Union
import logging

# Import processor modules
from processors import DocumentProcessor, PDFProcessor, ImageProcessor, BaseFileProcessor,HTMLProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessorRegistry:
    """Processor Registry - Manages all processors"""
    
    def __init__(self):
        self.processors = []
        self._register_default_processors()
    
    def _register_default_processors(self):
        """Register default processors"""
        self.register_processor(DocumentProcessor())
        self.register_processor(PDFProcessor())
        self.register_processor(ImageProcessor())
        self.register_processor(HTMLProcessor())
    
    def register_processor(self, processor: BaseFileProcessor):
        """
        Register a new processor
        
        Args:
            processor: Processor instance inheriting from BaseFileProcessor
        """
        if not isinstance(processor, BaseFileProcessor):
            raise TypeError("Processor must inherit from BaseFileProcessor")
        
        self.processors.append(processor)
        logger.info(f"Registered processor: {processor.get_processor_name()}")
    
    def get_processor_for_file(self, file_path: str) -> Optional[BaseFileProcessor]:
        """
        Get appropriate processor for file path
        
        Args:
            file_path: File path
            
        Returns:
            BaseFileProcessor or None: Matching processor or None
        """
        for processor in self.processors:
            if processor.can_process(file_path):
                return processor
        return None
    
    def get_supported_extensions(self) -> Dict[str, List[str]]:
        """Get all file extensions supported by processors"""
        extensions = {}
        for processor in self.processors:
            processor_name = processor.get_processor_name().replace("Processor", "").lower()
            extensions[processor_name] = list(processor.get_supported_extensions())
        return extensions
    
    def list_processors(self) -> List[str]:
        """List all registered processors"""
        return [processor.get_processor_name() for processor in self.processors]


class UnifiedFileProcessor:
    """Unified File Processor - Automatically determines file type and calls corresponding processor"""
    
    def __init__(self, registry: Optional[ProcessorRegistry] = None):
        self.registry = registry or ProcessorRegistry()
    
    def register_processor(self, processor: BaseFileProcessor):
        """
        Register a new processor
        
        Args:
            processor: Processor instance inheriting from BaseFileProcessor
        """
        self.registry.register_processor(processor)
    
    def get_file_type(self, file_path: str) -> str:
        """
        Determine file type
        
        Args:
            file_path: File path
            
        Returns:
            str: Processor type name or 'unknown'
        """
        processor = self.registry.get_processor_for_file(file_path)
        if processor:
            return processor.get_processor_name().replace("Processor", "").lower()
        return 'unknown'
    
    def get_processor_name(self, file_path: str) -> str:
        """
        Get processor name
        
        Args:
            file_path: File path
            
        Returns:
            str: Processor name or 'unknown'
        """
        processor = self.registry.get_processor_for_file(file_path)
        return processor.get_processor_name() if processor else 'unknown'
    
    def extract_text(self, file_path: str) -> Dict[str, Union[str, bool]]:
        """
        Unified text extraction interface
        
        Args:
            file_path: File path
            
        Returns:
            Dict containing: success(bool), text(str), error(str), file_type(str), processor(str)
        """
        processor = self.registry.get_processor_for_file(file_path)
        
        if not processor:
            ext = pathlib.Path(file_path).suffix.lower()
            return {
                "success": False, 
                "text": "", 
                "error": f"Unsupported file type: {ext}",
                "file_type": "unknown",
                "processor": "unknown"
            }
        
        # Process file using processor
        result = processor.process_file(file_path)
        result["file_type"] = self.get_file_type(file_path)
        
        return result
    
    def get_supported_extensions(self) -> Dict[str, List[str]]:
        """Get supported file extensions"""
        return self.registry.get_supported_extensions()
    
    def list_processors(self) -> List[str]:
        """List all registered processors"""
        return self.registry.list_processors()


# Convenience functions
def extract_text_from_file(file_path: str) -> Dict[str, Union[str, bool]]:
    """
    Convenience function: Extract text from file
    
    Args:
        file_path: File path
        
    Returns:
        Dict containing: success(bool), text(str), error(str), file_type(str)
    """
    processor = UnifiedFileProcessor()
    return processor.extract_text(file_path)


def batch_extract_text(file_paths: List[str]) -> Dict[str, Dict[str, Union[str, bool]]]:
    """
    Batch extract text
    
    Args:
        file_paths: List of file paths
        
    Returns:
        Dict[file_path, extraction_result]
    """
    processor = UnifiedFileProcessor()
    results = {}
    
    for file_path in file_paths:
        results[file_path] = processor.extract_text(file_path)
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Unified File Processor v2.0")
        print("=" * 40)
        print("Usage: python file_processor.py <file_path>")
        print()
        
        processor = UnifiedFileProcessor()
        print("Registered processors:")
        for proc_name in processor.list_processors():
            print(f"  • {proc_name}")
        print()
        
        print("Supported file types:")
        for category, exts in processor.get_supported_extensions().items():
            print(f"  {category}: {', '.join(exts)}")
        print()
        print("Examples:")
        print("  python file_processor.py document.pdf")
        print("  python file_processor.py image.png")
        sys.exit(1)
    
    file_path = sys.argv[1]
    result = extract_text_from_file(file_path)
    
    if result["success"]:
        print(f"✓ Processing successful")
        print(f"File type: {result['file_type']}")
        print(f"Processor: {result['processor']}")
        print(f"Text length: {len(result['text'])} characters")
        print("-" * 50)
        print(result["text"])
    else:
        print(f"✗ Processing failed")
        print(f"File type: {result.get('file_type', 'unknown')}")
        print(f"Processor: {result.get('processor', 'unknown')}")
        print(f"Error: {result['error']}")
