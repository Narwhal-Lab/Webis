#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webis Crawler Demo
Input a keyword, crawl related materials (PDF, HTML, DOC, etc.) from the web,
process them using Webis UnifiedFileProcessor, and generate a knowledge base.
"""

import os
import sys
import time
import argparse
import requests
import json
import logging
import re
from typing import List, Dict, Optional
from urllib.parse import urlparse, unquote
from ddgs import DDGS

# Domains that commonly block scraping or require auth; skip early.
BLOCKED_DOMAINS = {"zhihu.com", "baidu.com", "tieba.baidu.com", "facebook.com"}
# File extensions we want to prefer to improve hit rate on downloadable materials.
PREFERRED_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx"}
# Trusted suffixes (common university/government/Chinese domains) - allow attempts even without extension
TRUSTED_SUFFIXES = (".edu.cn", ".gov.cn", ".org.cn", ".com.cn", ".cn")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebisCrawler")

# Add tools directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
tools_path = os.path.join(project_root, 'tools')
sys.path.insert(0, tools_path)

try:
    from file_processor import UnifiedFileProcessor
except ImportError:
    logger.error("Could not import Webis tools. Please ensure you are in the Webis project root.")
    sys.exit(1)

class WebisCrawler:
    def __init__(self, download_dir: str = "downloaded_materials", output_file: str = "knowledge_base.json"):
        # Base output root under examples/outputs
        self.base_output_root = os.path.join(current_dir, "outputs")
        os.makedirs(self.base_output_root, exist_ok=True)
        # Will be set per run to keep outputs isolated
        self.download_dir = None
        self.output_file = None
        self.processor = UnifiedFileProcessor()

    def _prepare_run_dirs(self, keyword: str):
        """Create a per-run output folder to avoid name collisions across runs."""
        safe_keyword = re.sub(r"[^a-zA-Z0-9_-]+", "_", keyword.strip()) or "run"
        run_id = f"{safe_keyword}_{int(time.time())}"
        run_root = os.path.join(self.base_output_root, run_id)
        downloads = os.path.join(run_root, "downloads")
        output_file = os.path.join(run_root, "knowledge_base.json")
        os.makedirs(downloads, exist_ok=True)
        return run_root, downloads, output_file

    def _is_blocked(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower()
        return any(blocked in domain for blocked in BLOCKED_DOMAINS)

    def _has_preferred_ext(self, url: str) -> bool:
        return os.path.splitext(urlparse(url).path)[1].lower() in PREFERRED_EXTS

    def _is_trusted_domain(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower()
        return domain.endswith(TRUSTED_SUFFIXES)
            
    def search_urls(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """
        Search for materials using DuckDuckGo
        Targeting PDF, DOC, DOCX, PPT, and PPTX
        """
        results = []
        # If user has specified filetype, use it directly; otherwise auto-append common types and add original keyword as fallback
        if "filetype:" in keyword:
            queries = [keyword.strip()]
        else:
            queries = [
                f"{keyword} filetype:pdf",
                f"{keyword} filetype:docx",
                f"{keyword} filetype:doc",
                f"{keyword} filetype:ppt",
                f"{keyword} filetype:pptx",
                keyword.strip(),  # Fallback: without filetype
                f"{keyword} site:edu.cn filetype:pdf",
                f"{keyword} site:gov.cn filetype:pdf",
            ]
        # Remove duplicates while preserving order
        seen = set()
        queries = [q for q in queries if not (q in seen or seen.add(q))]
        
        total_found = 0
        with DDGS() as ddgs:
            for query in queries:
                if total_found >= max_results:
                    break
                
                logger.info(f"Searching for: {query}")
                try:
                    # search_results is a generator
                    search_gen = ddgs.text(
                        query,
                        max_results=max_results // len(queries) + 2,
                        safesearch="moderate",
                    )
                    total_found = self._collect_results(search_gen, results, total_found, max_results)
                    time.sleep(1) # Be polite
                except Exception as e:
                    logger.error(f"Error searching for {query}: {e}")
        
        return results[:max_results]

    def _collect_results(self, iterable, results: List[Dict], total_found: int, max_results: int) -> int:
        """Collect search results with filtering."""
        for r in iterable:
            url = r.get('href') if isinstance(r, dict) else r.get("href") if hasattr(r, "get") else None
            title = r.get('title') if isinstance(r, dict) else r.get("title") if hasattr(r, "get") else ""
            if not url:
                continue
            if self._is_blocked(url):
                logger.info(f"Skip blocked domain: {url}")
                continue
            # Prefer target extensions or trusted domains, otherwise accept to avoid no results
            if url not in [x['url'] for x in results]:
                results.append({'url': url, 'title': title})
                total_found += 1
            if total_found >= max_results:
                break
        return total_found

    def download_file(self, url: str) -> Optional[str]:
        """Download file from URL to download_dir"""
        try:
            logger.info(f"Downloading: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            response.raise_for_status()
            
            # Determine filename
            parsed_url = urlparse(url)
            filename = os.path.basename(unquote(parsed_url.path))
            
            # If no filename or empty, use a default one based on content type or timestamp
            if not filename or filename == '/':
                content_type = response.headers.get('content-type', '').lower()
                ext = ".html"
                if 'pdf' in content_type:
                    ext = ".pdf"
                elif 'word' in content_type:
                    ext = ".docx"
                filename = f"downloaded_{int(time.time())}{ext}"
            
            # Ensure extension is present for UnifiedFileProcessor
            name, ext = os.path.splitext(filename)
            if not ext:
                 content_type = response.headers.get('content-type', '').lower()
                 if 'pdf' in content_type:
                     ext = ".pdf"
                 elif 'html' in content_type:
                     ext = ".html"
                 else:
                     ext = ".html" # Default to html
                 filename = name + ext

            # Limit filename length
            if len(filename) > 100:
                filename = filename[-100:]

            filepath = os.path.join(self.download_dir, filename)
            
            # Handle duplicate filenames
            counter = 1
            original_filepath = filepath
            while os.path.exists(filepath):
                filepath = f"{os.path.splitext(original_filepath)[0]}_{counter}{os.path.splitext(original_filepath)[1]}"
                counter += 1
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filepath
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None

    def process_materials(self, filepaths: List[str]) -> List[Dict]:
        """Process downloaded files using Webis UnifiedFileProcessor"""
        knowledge_base = []
        
        for filepath in filepaths:
            logger.info(f"Processing: {filepath}")
            try:
                result = self.processor.extract_text(filepath)
                
                kb_entry = {
                    "source_file": os.path.basename(filepath),
                    "file_type": result.get("file_type", "unknown"),
                    "processed_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "content": "",
                    "status": "success" if result.get("success") else "failed",
                    "error": result.get("error", "")
                }
                
                if result.get("success"):
                    kb_entry["content"] = result.get("text", "")
                
                knowledge_base.append(kb_entry)
                
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
                knowledge_base.append({
                    "source_file": os.path.basename(filepath),
                    "status": "error",
                    "error": str(e)
                })
                
        return knowledge_base

    def run(self, keyword: str, max_results: int = 5):
        # Prepare per-run paths
        run_root, downloads, output_file = self._prepare_run_dirs(keyword)
        self.download_dir = downloads
        self.output_file = output_file

        print(f"🚀 Starting Webis Crawler for keyword: '{keyword}'")
        print(f"   Downloads: {self.download_dir}")
        print(f"   Output   : {self.output_file}")
        
        # 1. Search
        urls_info = self.search_urls(keyword, max_results)
        print(f"Found {len(urls_info)} URLs.")
        
        # 2. Download
        filepaths = []
        for info in urls_info:
            path = self.download_file(info['url'])
            if path:
                filepaths.append(path)
        
        print(f"Downloaded {len(filepaths)} files.")
        
        # 3. Process
        kb = self.process_materials(filepaths)
        
        # 4. Save Knowledge Base
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(kb, f, ensure_ascii=False, indent=2)
            
        print(f"\n✅ Knowledge Base generated at: {self.output_file}")
        
        # Print summary
        print("\nSummary:")
        for entry in kb:
            status_icon = "✓" if entry['status'] == 'success' else "✗"
            content_len = len(entry.get('content', ''))
            print(f"{status_icon} {entry['source_file']} ({entry.get('file_type', 'unknown')}) - Extracted {content_len} chars")

def main():
    parser = argparse.ArgumentParser(description="Webis Crawler Demo")
    parser.add_argument("keyword", help="Keyword to search for")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of results")
    
    args = parser.parse_args()
    
    crawler = WebisCrawler()
    crawler.run(args.keyword, args.limit)

if __name__ == "__main__":
    main()
