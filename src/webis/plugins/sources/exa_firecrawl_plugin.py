import logging
import os
import requests
import time
from typing import Any, Dict, Iterator, List, Optional, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from webis.core.plugin import SourcePlugin, PluginMetadata
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata

logger = logging.getLogger(__name__)

class ExaFirecrawlCrawler(SourcePlugin):
    """
    Crawler that uses Exa MCP for search and Firecrawl MCP for scraping.
    
    This plugin connects to external MCP servers (via HTTP JSON-RPC) or APIs to perform tasks.
    It orchestrates:
    1. Search via Exa.
    2. Deep scraping via Firecrawl.
    """
    
    name = "exa_firecrawl_crawler"
    description = "Intelligent crawler using Exa for neural search and Firecrawl for high-fidelity scraping."
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Default to None if not set, enabling auto-fallback logic
        self.exa_mcp_url = os.environ.get("EXA_MCP_URL") 
        self.firecrawl_mcp_url = os.environ.get("FIRECRAWL_MCP_URL")
        self.exa_token = os.environ.get("EXA_API_KEY")
        self.firecrawl_token = os.environ.get("FIRECRAWL_API_KEY")
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def fetch(self, query: str, limit: int = 10, context: Any = None, **kwargs) -> Iterator[WebisDocument]:
        """
        Execute search and crawl.
        """
        # 1. Search with Exa
        logger.info(f"[{self.name}] Searching Exa for: {query}")
        urls = self._exa_search(query, limit)
        
        if not urls:
            logger.warning(f"[{self.name}] Exa returned no URLs.")
            return

        # 2. Crawl with Firecrawl
        logger.info(f"[{self.name}] Crawling {len(urls)} URLs with Firecrawl...")
        for url in urls:
            try:
                content = self._firecrawl_scrape(url)
                if content:
                    yield WebisDocument(
                        content=str(content), # Ensure string
                        doc_type=DocumentType.TEXT, # Firecrawl usually returns markdown/text
                        meta=DocumentMetadata(
                            url=url, 
                            source_plugin=self.name,
                            custom={"source": "firecrawl", "original_query": query}
                        )
                    )
            except Exception as e:
                logger.error(f"[{self.name}] Failed to crawl {url}: {e}")

    def _exa_search(self, query: str, limit: int) -> List[str]:
        """
        Call Exa MCP `search` tool. 
        Note: If direct API use is preferred over MCP bridge, we could switch, 
        but request specified MCP integration. We assume an HTTP MCP bridge here.
        """
        tool_name = "search"
        args = {"query": query, "numResults": limit}
        
        try:
            # Fallback logic handles both MCP and Direct API
            result = self._call_mcp(self.exa_mcp_url, self.exa_token, tool_name, args)
            
            urls = []
            # Parse result variants
            if isinstance(result, dict):
                 items = result.get("results", [])
                 for item in items:
                     if isinstance(item, dict) and "url" in item:
                         urls.append(item["url"])
                     elif isinstance(item, str) and item.startswith("http"):
                         urls.append(item)
            return urls
            
        except Exception as e:
            logger.error(f"Exa search failed: {e}")
            return []

    def _firecrawl_scrape(self, url: str) -> Optional[str]:
        """
        Call Firecrawl MCP `scrape` tool.
        """
        tool_name = "scrape"
        args = {"url": url}
        
        try:
            result = self._call_mcp(self.firecrawl_mcp_url, self.firecrawl_token, tool_name, args)
            # Result might be complex object or string
            return str(result)
        except Exception as e:
            logger.error(f"Firecrawl scrape failed: {e}")
            return None

    def _call_mcp(self, url: Optional[str], token: Optional[str], tool_name: str, args: Dict) -> Any:
        """
        Generic call handler: Tries MCP first if URL set, else falls back to Direct Cloud API.
        """
        # Strategy:
        # 1. If MCP URL is explicitly set, use it.
        # 2. If no MCP URL, or connection fails, try Direct Cloud API if token exists.
        
        if url:
            try:
                return self._call_mcp_rpc(url, token, tool_name, args)
            except requests.exceptions.RequestException as exc:
                if not token:
                    raise
                logger.warning(f"[{self.name}] MCP call failed at {url} ({exc}). Falling back to Direct Cloud API.")
        
        if token:
            if tool_name == "search": # Exa
                return self._call_exa_api(token, args)
            elif tool_name == "scrape": # Firecrawl
                return self._call_firecrawl_api(token, args)
                
        raise RuntimeError("No MCP URL configured and no Cloud API token available.")

    def _call_mcp_rpc(self, url: str, token: Optional[str], tool_name: str, args: Dict) -> Any:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        payload = {
            "jsonrpc": "2.0", 
            "id": int(time.time() * 1000), 
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args}
        }
        resp = self.session.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"MCP Error: {data['error']}")
        
        # Consistent text extraction
        res = data.get("result", {})
        if isinstance(res, dict) and "content" in res:
             content_list = res["content"]
             if isinstance(content_list, list):
                 text_parts = [c.get("text", "") for c in content_list if c.get("type") == "text"]
                 return "\n".join(text_parts)
        return res

    def _call_exa_api(self, token: str, args: Dict) -> Any:
        """Direct call to Exa API"""
        url = "https://api.exa.ai/search"
        headers = {
            "x-api-key": token,
            "Content-Type": "application/json"
        }
        # Simplify args for API
        payload = {
            "query": args.get("query"),
            "numResults": args.get("numResults", 10),
            "useAutoprompt": True
        }
        resp = self.session.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _call_firecrawl_api(self, token: str, args: Dict) -> Any:
        """Direct call to Firecrawl API"""
        url = "https://api.firecrawl.dev/v1/scrape"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "url": args.get("url"),
            "formats": ["markdown"]
        }
        resp = self.session.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Firecrawl API Error: {data.get('error')}")
        return data.get("data", {}).get("markdown", "")
