# Webis - Multimodal Data Extraction Framework

[English](README.md) | [中文](README_CN.md)

![Python Version](https://img.shields.io/badge/Python-3.9+-blue)  

![License](https://img.shields.io/badge/License-Open%20Source-green) 

## Overview

Webis is a full-link efficient processing pipeline covering web data crawling, multimodal data cleaning, and thematic knowledge base construction. The framework deeply integrates professional cleaning tools for multimodal data such as documents, PDFs, images, and HTML web pages. It can automatically identify file types, intelligently match corresponding processing modules, support batch processing of various data, and output standardized structured results. Currently, Webis has integrated four core modal data processing tools, among which Webis_HTML is an independently developed web page data extraction tool by the team — relying on three-level denoising technology, it can accurately strip redundant web page information and efficiently extract core valuable content. This tool has been simultaneously released as an independent Python package to the PyPi repository for developers to directly install and call.

## Table of Contents

- [Quick Start](#quick-start)

- [Environment Configuration](#environment-configuration)

- [API Documentation](#api-documentation)

- [Usage Examples](#usage-examples)

- [Supported File Types](#supported-file-types)

- [Features](#features)

- [Development and Extension](#development-and-extension)

- [Frequently Asked Questions](#frequently-asked-questions)

- [License and Contribution](#license-and-contribution)

## Quick Start

### Prerequisites

- Python 3.9+

- Conda environment or uv environment

### Environment Configuration

#### Method 1: Automatic Configuration Script (Recommended)

```
# Run the automatic configuration script
bash setup/conda_setup.sh
# For uv environment
bash setup/uv_setup.sh
```

#### Method 2: Manual Configuration

```
# Create and activate Conda environment
conda create -n webis python=3.9 -y
conda activate webis

# Install dependencies
pip install -r setup/requirements.txt
```

#### Method 3: Using Homebrew (macOS)

```
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python

# Verify installation
python3 --version
pip3 --version

# Install dependencies
pip install -r setup/requirements.txt
```

### Basic Usage

```
# Activate the environment
conda activate webis

# Process a single file
python process_file.py tools/data/pdf/example.pdf

# Run full demo
python examples/demo.py

# Run crawler knowledge base demo
python examples/crawler_demo.py "keywords" --limit 5
```

## API Documentation

### 1. Individual Processor Interfaces

#### DocumentProcessor - Document Processor

```
from file_processor import DocumentProcessor

processor = DocumentProcessor()

# Check if file type is supported
if processor.can_process("test.docx"):
    # Extract text
    result = processor.extract_text("test.docx")
    if result["success"]:
        print(result["text"])
    else:
        print(f"Error: {result['error']}")
```

#### PDFProcessor - PDF Processor

```
from file_processor import PDFProcessor

processor = PDFProcessor()

# Extract text from PDF
result = processor.extract_text("document.pdf")
if result["success"]:
    print(result["text"])  # Includes page number information
```

#### ImageProcessor - Image OCR Processor

```
from file_processor import ImageProcessor

processor = ImageProcessor()

# OCR recognition for images
result = processor.extract_text("image.png")
if result["success"]:
    print(result["text"])
```

> **Note**: The first time you use the image processor, it will automatically download the open-source EasyOCR model, which may take some time. Please be patient. Subsequent uses will directly load the downloaded model. If the download fails, we recommend trying to use a VPN.

#### HTMLProcessor - HTML Processor

**Webis_HTML** is an independent HTML web page data extraction tool developed for Webis. [html_processor.py](http://html_processor.py) implements this functionality by directly calling the webis-html Python library.

- **Installation**: Install via pip install webis-html (already included in requirements.txt)

- **No Server Required**: The webis-html library automatically handles HTML content extraction without the need to start additional servers

**Usage Example**:

```
from file_processor import HTMLProcessor

processor = HTMLProcessor()

# Extract text from HTML
result = processor.extract_text("example.html")
if result["success"]:
    print(result["text"])
```

**API Key Configuration** (Required for HTML Processing):

- **Obtain API Key**: Visit [SiliconFlow](https://www.siliconflow.com/) to register an account and get an API key

- **Configure Environment Variables**:

```
export DEEPSEEK_API_KEY="your-siliconflow-api-key"
# Or
export LLM_PREDICTOR_API_KEY="your-siliconflow-api-key"
```

- **Conda Environment Configuration** (Recommended):

```
conda env config vars set DEEPSEEK_API_KEY="your-siliconflow-api-key" -n webis
conda activate webis  # Reactivate the environment for changes to take effect
```

> **Important**: The HTML processing function requires content filtering optimization via the SiliconFlow API, which requires configuring the corresponding API key. Please obtain the API key from [SiliconFlow](https://www.siliconflow.com/). The HTML processing function cannot be used without configuring the API key.

### 2. Unified Processor Interface

#### UnifiedFileProcessor - Unified Processor

```
from file_processor import UnifiedFileProcessor

processor = UnifiedFileProcessor()

# Automatically determine file type and process
result = processor.extract_text("any_file.pdf")
print(f"File Type: {result['file_type']}")
print(f"Text Content: {result['text']}")
```

### 3. Convenience Function Interfaces

#### Single File Processing

```
from file_processor import extract_text_from_file

# Simplest usage
result = extract_text_from_file("file.pdf")
if result["success"]:
    print(f"File Type: {result['file_type']}")
    print(f"Text Length: {len(result['text'])} characters")
    print(result["text"])
```

#### Batch File Processing

```
from file_processor import batch_extract_text

# Batch process multiple files
file_paths = ["doc1.pdf", "doc2.docx", "image1.png"]
results = batch_extract_text(file_paths)

for file_path, result in results.items():
    if result["success"]:
        print(f"{file_path}: {len(result['text'])} characters")
    else:
        print(f"{file_path}: {result['error']}")
```

## Usage Examples

### Command Line Usage

```
# Process a single file
python3 file_processor.py document.pdf

# View supported file types
python3 file_processor.py
```

### Python Script Usage

```
#!/usr/bin/env python3
from file_processor import extract_text_from_file

def main():
    # Process different types of files
    files = [
        "pdf/example.pdf",
        "Doc/demo.pdf",
        "Pic/demo.png"  # Corrected file extension for consistency
    ]
    
    for file_path in files:
        print(f"\nProcessing file: {file_path}")
        result = extract_text_from_file(file_path)
        
        if result["success"]:
            print(f"File Type: {result['file_type']}")
            print(f"Text Length: {len(result['text'])} characters")
            print("Text Preview:")
            print(result["text"][:300] + "...")
        else:
            print(f"Processing failed: {result['error']}")

if __name__ == "__main__":
    main()
```

### Integration in Code

```
# Add tool path
import sys
sys.path.append('tools')

from file_processor import extract_text_from_file

# Process file
result = extract_text_from_file('your_file.pdf')
if result['success']:
    print(result['text'])
```

### Crawler Knowledge Base Demo

[crawler_demo.py](http://crawler_demo.py) is a complete web crawler example that can automatically search, download, and process online document materials to generate a knowledge base.

**Features**:

- Automatically search for relevant materials (PDF, DOC, DOCX, PPT, PPTX, HTML, etc.) using the DuckDuckGo search engine

- Automatically download found files to local

- Use Webis UnifiedFileProcessor to automatically process downloaded files

- Generate structured knowledge base JSON file

**Usage**:

```
# Basic usage: Search for keywords and process the first 5 results
python examples/crawler_demo.py "Python tutorial" --limit 5

# Search for more results
python examples/crawler_demo.py "machine learning" --limit 10

# Specify file type in search (include filetype: in keywords)
python examples/crawler_demo.py "deep learning filetype:pdf" --limit 3
```

**Output Results**:

- Downloaded files are saved in the examples/outputs/downloaded_materials/ directory

- Knowledge base file is saved in examples/outputs/knowledge_base.json

- The knowledge base includes processing results, extracted text content, file types, etc., for each file

**Knowledge Base Format**:

```
[
  {
    "source_file": "example.pdf",
    "file_type": "pdf",
    "processed_time": "2025-11-27 14:00:00",
    "content": "Extracted text content...",
    "status": "success",
    "error": ""
  }
]
```

**Notes**:

- Requires configuring the DEEPSEEK_API_KEY environment variable. Please obtain the API key from [SiliconFlow](https://www.siliconflow.com/) (used for HTML processing optimization)

- The search function relies on network connectivity; some websites may be inaccessible

- Downloaded files are saved in the examples/outputs/downloaded_materials/ directory

- It is recommended to use the --limit parameter to restrict the number of results to avoid downloading too many files

## Supported File Types

| Type     | Extensions                     | Processing Tool | Description                                                  |
| -------- | ------------------------------ | --------------- | ------------------------------------------------------------ |
| Document | .txt, .md, .docx               | LangChain       | Direct text extraction                                       |
| PDF      | .pdf                           | PyPDF           | Page-by-page extraction with page number retention           |
| Image    | .png, .jpg, .jpeg, .bmp, .tiff | EasyOCR         | Optical Character Recognition (OCR)                          |
| HTML     | .html                          | Webis_HTML      | Extract and clean web page data using a self-designed fine-tuned model |

## Features

- **Automatic File Type Recognition**: Automatically select the appropriate processing tool based on file extension

- **Unified Interface**: Provide a consistent API to process different types of files

- **Batch Processing**: Support batch processing of multiple files

- **Error Handling**: Comprehensive error handling and logging

- **Chinese Support**: Full support for Chinese documents and OCR

- **Extensibility**: Easy to add support for new file types

- **Modular Design**: Independent processors for easy maintenance and extension

- **Structured Output**: All processors return results in a unified format

### Result Format

All processors return results in a unified format:

```
{
    "success": bool,        # Whether processing was successful
    "text": str,           # Extracted text content
    "error": str,          # Error message (if failed)
    "file_type": str       # File type (only for unified interface)
}
```

## Development and Extension

### How to Add a New File Processing Type

1. Create a new processor class (inheriting BaseFileProcessor) in tools/processors/

1. Import and register the new processor in tools/processors/[__init__.py](http://__init__.py)

1. Register the new type in UnifiedFileProcessor in tools/[file_processor.py](http://file_processor.py)

1. Update the list of supported extensions and documentation

### Performance Optimization Suggestions

1. **Batch Processing**: Use batch_extract_text() to process multiple files

1. **Lazy Loading**: The image processor uses lazy loading to avoid unnecessary model initialization

1. **Result Caching**: Cache results for files that need to be processed repeatedly

1. **Parallel Processing**: Consider multi-process parallel processing for large numbers of files

## Frequently Asked Questions

### Q: Errors occur when installing dependencies?

A: Ensure you are using the correct Python version (3.8+). You may need to use pip3 instead of pip.

### Q: EasyOCR runs very slowly the first time?

A: EasyOCR downloads the model file on first use. Please be patient.

### Q: Image recognition accuracy is low?

A: You can try:

- Increasing image resolution

- Ensuring text clarity

- Adjusting the confidence threshold (confidence > 0.5 in code)

### Q: Unable to extract text from PDF?

A: It may be a scanned PDF. We recommend converting it to an image first and then using OCR for processing.

## License and Contribution

### License

This project is licensed under an open-source license. For specific license information, please refer to the LICENSE file in the project root directory.

### Contribution

Contributions are welcome! Please submit issues or pull requests on GitHub. For support, please contact us via GitHub Issues.