#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified File Processor with Output
Supports saving processing results to output folder
"""

import os
import pathlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Union
import logging

# Import processor modules
from processors import DocumentProcessor, PDFProcessor, ImageProcessor, BaseFileProcessor, HTMLProcessor
from file_processor import UnifiedFileProcessor, ProcessorRegistry

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileProcessorWithOutput(UnifiedFileProcessor):
    """Unified File Processor with Output"""
    
    def __init__(self, output_dir: str = "outputs", registry: Optional[ProcessorRegistry] = None):
        super().__init__(registry)
        self.output_dir = output_dir
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Ensure output directory exists"""
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Output directory set to: {os.path.abspath(self.output_dir)}")
    
    def _generate_output_filename(self, input_path: str, suffix: str = "") -> str:
        """
        Generate output filename
        
        Args:
            input_path: Input file path
            suffix: Filename suffix
            
        Returns:
            str: Output file path
        """
        input_file = pathlib.Path(input_path)
        base_name = input_file.stem  # Filename without extension
        
        if suffix:
            output_name = f"{base_name}_{suffix}.txt"
        else:
            output_name = f"{base_name}.txt"
        
        return os.path.join(self.output_dir, output_name)
    
    def process_file_with_output(self, file_path: str, save_output: bool = True, 
                                include_metadata: bool = True) -> Dict[str, Union[str, bool]]:
        """
        Process file and optionally save output
        
        Args:
            file_path: Input file path
            save_output: Whether to save output to file
            include_metadata: Whether to include metadata
            
        Returns:
            Dict: Processing result, including output file path information
        """
        # Call parent class processing method
        result = self.extract_text(file_path)
        
        # Add processing timestamp
        result["processed_at"] = datetime.now().isoformat()
        result["input_file"] = os.path.abspath(file_path)
        
        if save_output and result["success"]:
            try:
                # Generate output file path
                output_path = self._generate_output_filename(file_path)
                
                # Prepare content to save
                content_to_save = []
                
                if include_metadata:
                    content_to_save.extend([
                        f"=== File Processing Result ===",
                        f"Input File: {result['input_file']}",
                        f"File Type: {result['file_type']}",
                        f"Processor: {result['processor']}",
                        f"Processing Time: {result['processed_at']}",
                        f"Text Length: {len(result['text'])} characters",
                        f"",
                        f"=== Extracted Content ===",
                        f""
                    ])
                
                content_to_save.append(result['text'])
                
                # Save to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(content_to_save))
                
                result["output_file"] = os.path.abspath(output_path)
                logger.info(f"Result saved to: {output_path}")
                
            except Exception as e:
                logger.error(f"Failed to save output file: {str(e)}")
                result["output_error"] = str(e)
        
        return result
    
    def batch_process_with_output(self, file_paths: List[str], save_output: bool = True,
                                 include_metadata: bool = True) -> Dict[str, Dict[str, Union[str, bool]]]:
        """
        Batch process files and save output
        
        Args:
            file_paths: List of file paths
            save_output: Whether to save output
            include_metadata: Whether to include metadata
            
        Returns:
            Dict[file_path, processing_result]
        """
        results = {}
        summary = {
            "total_files": len(file_paths),
            "successful": 0,
            "failed": 0,
            "output_files": []
        }
        
        for file_path in file_paths:
            result = self.process_file_with_output(file_path, save_output, include_metadata)
            results[file_path] = result
            
            if result["success"]:
                summary["successful"] += 1
                if "output_file" in result:
                    summary["output_files"].append(result["output_file"])
            else:
                summary["failed"] += 1
        
        # Save batch processing summary
        if save_output:
            summary_path = os.path.join(self.output_dir, f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            try:
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)
                logger.info(f"Batch processing summary saved to: {summary_path}")
            except Exception as e:
                logger.error(f"Failed to save summary file: {str(e)}")
        
        return results
    
    def clear_output_dir(self):
        """Clear output directory"""
        if os.path.exists(self.output_dir):
            import shutil
            shutil.rmtree(self.output_dir)
            self._ensure_output_dir()
            logger.info(f"Output directory cleared: {self.output_dir}")


# Convenience functions
def process_file_with_output(file_path: str, output_dir: str = "outputs", 
                           save_output: bool = True, include_metadata: bool = True) -> Dict[str, Union[str, bool]]:
    """
    Convenience function: Process file and save output
    
    Args:
        file_path: File path
        output_dir: Output directory
        save_output: Whether to save output
        include_metadata: Whether to include metadata
        
    Returns:
        Dict: Processing result
    """
    processor = FileProcessorWithOutput(output_dir)
    return processor.process_file_with_output(file_path, save_output, include_metadata)


def batch_process_with_output(file_paths: List[str], output_dir: str = "outputs",
                            save_output: bool = True, include_metadata: bool = True) -> Dict[str, Dict[str, Union[str, bool]]]:
    """
    Convenience function: Batch process files and save output
    
    Args:
        file_paths: List of file paths
        output_dir: Output directory
        save_output: Whether to save output
        include_metadata: Whether to include metadata
        
    Returns:
        Dict[file_path, processing_result]
    """
    processor = FileProcessorWithOutput(output_dir)
    return processor.batch_process_with_output(file_paths, save_output, include_metadata)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Unified File Processor with Output v2.0")
        print("=" * 50)
        print("Usage:")
        print("  python file_processor_with_output.py <file_path> [output_dir]")
        print()
        print("Parameters:")
        print("  file_path    : File to process")
        print("  output_dir   : Directory to save results (default: outputs)")
        print()
        print("Examples:")
        print("  python file_processor_with_output.py document.pdf")
        print("  python file_processor_with_output.py image.png my_outputs")
        print()
        
        processor = FileProcessorWithOutput()
        print("Supported file types:")
        for category, exts in processor.get_supported_extensions().items():
            print(f"  {category}: {', '.join(exts)}")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "outputs"
    
    print(f"Processing file: {file_path}")
    print(f"Output directory: {output_dir}")
    print("-" * 50)
    
    result = process_file_with_output(file_path, output_dir)
    
    if result["success"]:
        print(f"✓ Processing successful")
        print(f"File type: {result['file_type']}")
        print(f"Processor: {result['processor']}")
        print(f"Text length: {len(result['text'])} characters")
        if "output_file" in result:
            print(f"Output file: {result['output_file']}")
        print()
        print("Text content preview:")
        print("-" * 30)
        preview = result["text"][:500]
        if len(result["text"]) > 500:
            preview += "\n... (content truncated, see output file for full content)"
        print(preview)
    else:
        print(f"✗ Processing failed")
        print(f"Error: {result['error']}")
        if "output_error" in result:
            print(f"Output error: {result['output_error']}")
