#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webis Batch File Processing Demo
Supports batch text extraction and output for documents, PDFs, images, and HTML
"""

import sys
import os

# Add tools directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.join(os.path.dirname(current_dir), 'tools')
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)

from file_processor_with_output import batch_process_with_output
import logging

# Set logging level to WARNING to reduce output
logging.getLogger().setLevel(logging.WARNING)

def main():
    """Batch process all example files"""
    # Get script directory (examples directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Webis - Multimodal Data Cleaning Tool")
    print("=" * 50)
    print("Supports documents(.docx/.txt/.md), PDF(.pdf), images(.jpg/.png), HTML(.html/.htm)")
    print()
    
    # Collect all available example files
    available_files = []
    demo_files = [
        ("doc_example.docx", "Word Document"),
        ("pdf_example.pdf", "PDF Document"), 
        ("pic_example.jpg", "Image File"),
        ("html_example.html", "HTML File")
    ]
    
    print("Checking example files:")
    for file_name, file_desc in demo_files:
        # Use script directory as base path
        file_path = os.path.join(script_dir, file_name)
        if os.path.exists(file_path):
            available_files.append(file_path)
            print(f"  ✓ {file_desc}: {file_name}")
        else:
            print(f"  ✗ {file_desc}: {file_name} (file not found)")
    
    if not available_files:
        print("\n✗ No processable example files found")
        return
    
    print(f"\nStarting batch processing of {len(available_files)} files...")
    print()
    
    # Execute batch processing
    # Output directory also based on script directory
    output_dir = os.path.join(script_dir, "outputs")
    results = batch_process_with_output(
        file_paths=available_files,
        output_dir=output_dir,
        save_output=True,
        include_metadata=True
    )
    
    # Display processing results
    print("Processing Results:")
    print("-" * 40)
    
    success_count = 0
    total_chars = 0
    
    for file_path, result in results.items():
        file_name = os.path.basename(file_path)
        if result["success"]:
            success_count += 1
            total_chars += len(result["text"])
            print(f"✓ {file_name}")
            print(f"   Type: {result['file_type']}")
            print(f"   Processor: {result['processor']}")
            print(f"   Text length: {len(result['text'])} characters")
            if "output_file" in result:
                output_name = os.path.basename(result['output_file'])
                print(f"   Output file: {output_name}")
        else:
            print(f"✗ {file_name}")
            print(f"   Error: {result['error']}")
        print()
    
    # Display statistics
    print("Statistics:")
    print(f"  Success rate: {success_count}/{len(available_files)} ({success_count/len(available_files)*100:.1f}%)")
    print(f"  Total text: {total_chars:,} characters")
    print(f"  Output directory: {output_dir}")
    
    # Display output file list
    if os.path.exists(output_dir):
        files = [f for f in os.listdir(output_dir) if f.endswith('.txt') or f.endswith('.json')]
        if files:
            print(f"\nGenerated files ({len(files)} files):")
            for file_name in sorted(files):
                file_path = os.path.join(output_dir, file_name)
                size = os.path.getsize(file_path)
                if file_name.endswith('.json'):
                    print(f"  {file_name} ({size} bytes) - Processing summary")
                else:
                    print(f"  {file_name} ({size} bytes)")
    
    print(f"\nBatch processing completed!")
    print(f"View outputs/ directory for all output files")

if __name__ == "__main__":
    main()
