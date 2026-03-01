"""Bright Data plugin — BrightData SDK based implementation.

This plugin implements the same interface and behavior as
`web_search_crawler.WebSearchCrawler` so it can be used interchangeably in
examples. It intentionally does NOT use MCP — it uses `brightdata.BrightDataClient`.

Key methods provided:
  - search_google
  - search_bing
  - scrape_url
  - search_and_scrape
  - save_results
  - fetch (synchronous-friendly iterator for CrawlerAgent)

The plugin does NOT auto-register itself; callers should instantiate and
register explicitly if desired.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Iterator
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentMetadata, DocumentType, PipelineContext

load_dotenv()

try:
    from brightdata import BrightDataClient
    BRIGHTDATA_AVAILABLE = True
except Exception:
    BRIGHTDATA_AVAILABLE = False


class BrightDataPlugin(SourcePlugin):
    """Bright Data plugin using BrightDataClient.

    This mirrors the behavior of `web_search_crawler.WebSearchCrawler` so
    existing example code can call the same-named methods.
    """

    name = "bright_data"

    def __init__(self, api_token: Optional[str] = None) -> None:
        super().__init__()
        if api_token:
            os.environ["BRIGHTDATA_API_TOKEN"] = api_token
        # instantiate client lazily
        self.client: Optional[Any] = None
        self.results_dir = Path("search_results")
        self.results_dir.mkdir(exist_ok=True)

    def initialize(self, context: Optional[PipelineContext] = None) -> None:
        print(f"ℹ️  [{self.name}] Plugin initialized (BrightData SDK)")

    async def _ensure_client(self) -> None:
        if self.client is not None:
            return
        if not BRIGHTDATA_AVAILABLE:
            raise RuntimeError("brightdata SDK not installed. Install with: pip install brightdata")
        self.client = BrightDataClient(token=os.getenv("BRIGHTDATA_API_TOKEN", None))

    async def search_google(
        self,
        query: str,
        num_results: int = 10,
        location: Optional[str] = None,
        language: str = "en",
        device: str = "desktop",
    ) -> Dict[str, Any]:
        await self._ensure_client()
        print(f"\n🔍 使用 Google 搜索: '{query}'")
        print(f"   参数: 结果数={num_results}, 位置={location}, 语言={language}, 设备={device}")

        async with self.client:
            result = await self.client.search.google(
                query=query,
                num_results=num_results,
                location=location,
                language=language,
                device=device,
            )

        out: Dict[str, Any] = {
            "query": query,
            "search_engine": "google",
            "location": location,
            "language": language,
            "device": device,
            "num_results": num_results,
            "timestamp": datetime.now().isoformat(),
            "results": [],
        }

        if hasattr(result, "data") and result.data:
            for item in result.data:
                out["results"].append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "rank": item.get("rank", ""),
                })

        return out

    async def search_bing(
        self,
        query: str,
        num_results: int = 10,
        location: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        await self._ensure_client()
        print(f"\n🔍 使用 Bing 搜索: '{query}'")
        print(f"   参数: 结果数={num_results}, 位置={location}, 语言={language}")

        async with self.client:
            result = await self.client.search.bing(
                query=query,
                num_results=num_results,
                location=location,
                language=language,
            )

        out: Dict[str, Any] = {
            "query": query,
            "search_engine": "bing",
            "location": location,
            "language": language,
            "num_results": num_results,
            "timestamp": datetime.now().isoformat(),
            "results": [],
        }

        if hasattr(result, "data") and result.data:
            for item in result.data:
                out["results"].append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "rank": item.get("rank", ""),
                })

        return out

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        await self._ensure_client()
        print(f"   📄 爬取页面: {url}")
        try:
            async with self.client:
                result = await self.client.scrape_url(url)

            scrape_data: Dict[str, Any] = {"url": url, "timestamp": datetime.now().isoformat(), "status": "success"}
            if hasattr(result, "data"):
                scrape_data["content"] = result.data
            else:
                scrape_data["content"] = result
            return scrape_data
        except Exception as e:
            print(f"   ❌ 爬取失败: {str(e)}")
            return {"url": url, "timestamp": datetime.now().isoformat(), "status": "failed", "error": str(e)}

    async def search_and_scrape(
        self,
        query: str,
        search_engine: str = "google",
        num_results: int = 10,
        scrape_urls: bool = False,
        scrape_limit: int = 3,
        location: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        if search_engine.lower() == "google":
            search_result = await self.search_google(query=query, num_results=num_results, location=location, language=language)
        elif search_engine.lower() == "bing":
            search_result = await self.search_bing(query=query, num_results=num_results, location=location, language=language)
        else:
            raise ValueError(f"Unsupported search engine: {search_engine}")

        if scrape_urls and search_result.get("results"):
            print(f"\n🕷️  开始爬取页面内容 (最多 {scrape_limit} 个)...")
            for idx, item in enumerate(search_result["results"][:scrape_limit]):
                url = item.get("url")
                if url:
                    scrape_data = await self.scrape_url(url)
                    item["scraped_content"] = scrape_data

        return search_result

    def save_results(self, data: Dict[str, Any], format: str = "json", filename: Optional[str] = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            query_slug = data.get("query", "search").replace(" ", "_")[:30]
            filename = f"{timestamp}_{query_slug}"

        if format == "json":
            file_path = self.results_dir / f"{filename}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            file_path = self.results_dir / f"{filename}.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"搜索关键词: {data.get('query', 'N/A')}\n")
                f.write(f"搜索引擎: {data.get('search_engine', 'N/A')}\n")
                f.write(f"位置: {data.get('location', 'N/A')}\n")
                f.write(f"语言: {data.get('language', 'N/A')}\n")
                f.write(f"时间: {data.get('timestamp', 'N/A')}\n")
                f.write(f"结果数: {len(data.get('results', []))}\n")

        print(f"✅ 结果已保存到: {file_path}")
        return str(file_path)

    def fetch(self, query: str, limit: int = 10, context: Optional[PipelineContext] = None) -> Iterator[WebisDocument]:
        """Synchronous-friendly fetch API for CrawlerAgent.
        
        Searches for query, then scrapes the actual content from each URL.
        Returns the scraped web page content, not search result descriptions.
        """
        # Run async search_and_scrape in sync context, with scraping enabled
        data = asyncio.run(self.search_and_scrape(
            query=query,
            search_engine="google",
            num_results=limit,
            scrape_urls=True,  # 爬取URL内容
            scrape_limit=limit
        ))
        results = data.get("results", [])

        for r in results[:limit]:
            # 优先使用爬取到的实际网页内容，而非搜索引擎的描述
            scraped = r.get("scraped_content", {})
            if isinstance(scraped, dict):
                content = scraped.get("content", "")
                status = scraped.get("status", "")
            else:
                content = scraped or ""
                status = "success"

            # 如果没有爬取到内容，跳过
            if not content or status == "failed":
                continue
                
            url = r.get("url") or f"brightdata://{query}"
            title = r.get("title") or url
            meta = DocumentMetadata(
                url=url,
                title=title,
                source_plugin=self.name,
                custom={"bright_data_result": True, "scraped": True}
            )
            yield WebisDocument(
                content=str(content),
                doc_type=DocumentType.TEXT,
                meta=meta
            )

    def cleanup(self) -> None:
        """Clean up resources (no-op for BrightData SDK)."""
        print(f"✓ [{self.name}] cleanup (BrightData SDK - no session to close)")
