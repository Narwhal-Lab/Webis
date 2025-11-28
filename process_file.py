#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webis Main Entry Script
Run file processor from project root directory
"""

import sys
import os

# Add tools directory to Python path
tools_path = os.path.join(os.path.dirname(__file__), 'tools')
sys.path.insert(0, tools_path)

# Import file processor
from file_processor import extract_text_from_file, UnifiedFileProcessor

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Webis - Unified File Processing Tool")
        print("=" * 50)
        print("Usage: python process_file.py <file_path>")
        print()
        
        processor = UnifiedFileProcessor()
        print("Supported file types:")
        for category, exts in processor.get_supported_extensions().items():
            print(f"  {category}: {', '.join(exts)}")
        print()
        print("Examples:")
        print("  python process_file.py tools/data/pdf/example.pdf")
        print("  python process_file.py examples/test.txt")
        print()
        print("More features:")
        print("  python examples/demo.py  # Run complete demo")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # If relative path, search from current directory
    if not os.path.isabs(file_path) and not os.path.exists(file_path):
        # Try searching in common directories
        search_paths = [
            file_path,
            os.path.join('tools/data', file_path),
            os.path.join('examples', file_path),
            os.path.join('tools/processors', file_path)
        ]
        
        found = False
        for search_path in search_paths:
            if os.path.exists(search_path):
                file_path = search_path
                found = True
                break
        
        if not found:
            print(f"Error: File not found {sys.argv[1]}")
            sys.exit(1)
    
    print(f"Processing file: {file_path}")
    print("-" * 50)
    
    result = extract_text_from_file(file_path)
    
    if result["success"]:
        print(f"✓ Processing successful")
        print(f"File type: {result['file_type']}")
        print(f"Text length: {len(result['text'])} characters")
        print()
        print("Extracted text content:")
        print("=" * 50)
        print(result["text"])
    else:
        print(f"✗ Processing failed: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
