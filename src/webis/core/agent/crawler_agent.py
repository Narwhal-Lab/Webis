"""
Crawler Agent for Webis v2.

Migrated from v1 LangChainDataSourceAgent.
Responsible for selecting the appropriate source plugin for a given task
and executing the search/crawl operation.
"""

from __future__ import annotations

import json
import re
from typing import List, Optional, Dict, Any

from webis.core.llm.base import LLMRouter, get_default_router
from webis.core.plugin import PluginRegistry, get_default_registry
from webis.core.schema import WebisDocument, PipelineContext
from webis.plugins.sources.bright_data_plugin import BrightDataPlugin


# 移除logger相关导入和配置
# import logging
# logger = logging.getLogger(__name__)


class CrawlerAgent:
    """
    Intelligent agent that selects and executes data source plugins.
    
    Example:
        >>> agent = CrawlerAgent()
        >>> docs = agent.run("Search for latest AI news", limit=5)
    """
    
    def __init__(
        self, 
        router: Optional[LLMRouter] = None,
        registry: Optional[PluginRegistry] = None
    ):
        self.router = router or get_default_router()
        self.registry = registry or get_default_registry()
        self.last_used_tools: List[str] = []
        
    def run(
        self, 
        task: str, 
        limit: int = 10, 
        context: Optional[PipelineContext] = None,
        excluded_tools: Optional[List[str]] = None
    ) -> List[WebisDocument]:
        """
        Execute the crawling task.
        
        Args:
            task: Natural language task description
            limit: Maximum items to fetch
            context: Pipeline context
            excluded_tools: List of tool names to avoid (e.g. failed previously)
            
        Returns:
            List of fetched documents
        """
        
        # 1. Get available tools
        # print("self processors: ", self.registry.list_processors())
        all_sources = self.registry.list_sources()
        if not all_sources:
            print("⚠️ WARNING: No source plugins registered!")  # 改为print
            return []
            
        # Filter excluded tools
        excluded_tools = excluded_tools or []
        sources = [s for s in all_sources if s not in excluded_tools]
        
        if not sources:
            print(f"⚠️ WARNING: All sources excluded or unavailable! (Excluded: {excluded_tools})")  # 改为print
            # If all excluded, reset and try all
            sources = all_sources
            print("ℹ️ INFO: Resetting exclusions to allow retry.")  # 改为print
            
        source_descriptions = []
        for name in sources:
            plugin = self.registry.get_source(name)
            if plugin:
                desc = plugin.description
                # Add capability hints if available
                # (For now assume description is enough)
                source_descriptions.append(f"- {name}: {desc}")
                
        tools_prompt = "\n".join(source_descriptions)
        
        # 2. Ask LLM to pick prioritized tools
        prompt = f"""
        You are an intelligent crawler agent. Your goal is to select the BEST tools to retrieve information for the user's task.
        
        Available Tools:
        {tools_prompt}
        
        Excluded Tools (do not use): {excluded_tools}
        
        User Task: "{task}"
        
        Analyze the task. Select up to 3 best tools in order of priority.
        - If it's about code, prioritize GitHub.
        - If it's about news, prioritize GNews.
        - If general, prioritize search engines (Google/DuckDuckGo).
        - IMPORTANT: Do NOT select any tool listed in "Excluded Tools".
        
        Return a JSON object with:
        - "plan": A list of tool execution steps. Each step has:
            - "tool": The exact name of the tool.
            - "query": A refined search query optimized for that tool.
            - "reason": Brief explanation.
        
        Example JSON:
        {{
            "plan": [
                {{ "tool": "github", "query": "DeepSeek-V3 benchmark", "reason": "Best for code/technical releases" }},
                {{ "tool": "duckduckgo", "query": "DeepSeek-V3 performance review", "reason": "General search fallback" }}
            ]
        }}
        """
        
        plan = []
        # try:
        #     response = self.router.chat(
        #         [{"role": "user", "content": prompt}],
        #         model=None, # Use primary
        #         temperature=0.0,
        #         supports_json_mode=True
        #     )
        #     content = response.content
            
        #     # 3. Parse selection
        #     match = re.search(r"\{.*\}", content, re.DOTALL)
        #     if match:
        #         data = json.loads(match.group(0))
        #         plan = data.get("plan", [])
                
        #         # Support legacy single-tool format fallback
        #         if not plan and "tool" in data:
        #             plan = [data]
                    
        #     if not plan:
        #         raise ValueError("No plan found in JSON")
                
        #     print(f"ℹ️ INFO: Agent plan: {[step['tool'] for step in plan]}")  # 改为print
            
        # except Exception as e:
        #     print(f"❌ ERROR: LLM planning failed: {e}")  # 改为print
        #     # Fallback strategy: Try all search engines
        #     fallback_tools = ["duckduckgo", "google_search", "baidu_search"]
        #     plan = [{"tool": t, "query": task, "reason": "Fallback"} for t in fallback_tools if t in sources]
        #     if not plan and sources: 
        #          plan = [{"tool": sources[0], "query": task, "reason": "Last resort"}]
        #     print(f"ℹ️ INFO: Using fallback plan: {[step['tool'] for step in plan]}")  # 改为print

        # 4. Execute plan until limit met
        all_docs = []
        self.last_used_tools = [step['tool'] for step in plan]

        tool_name = "bright_data"
        if len(all_docs) >= limit:
            return all_docs
        print(f"ℹ️ INFO: Executing {tool_name} (Goal: {limit} docs)...")  # 改为print
        try:
                # 直接实例化并调用 BrightDataPlugin
                plugin = BrightDataPlugin()
                plugin.initialize(context)
                new_docs = list(plugin.fetch(task, limit=limit, context=context))
                print(f"  -> Fetched {len(new_docs)} docs")  # 改为print
                
                # Add unique docs
                for doc in new_docs:
                    if len(all_docs) >= limit:
                        break
                    # Simple duplicate check by URL (if available) or content hash could go here
                    all_docs.append(doc)
                plugin.cleanup()
                    
        except Exception as e:
            print(f"❌ ERROR: Step {tool_name} failed: {e}")  # 改为print
        
        return all_docs
        
        # for step in plan:
        #     if len(all_docs) >= limit:
        #         break
                
        #     tool_name = step.get("tool")
        #     query = step.get("query", task)
            
        #     if tool_name not in sources:
        #         print(f"⚠️ WARNING: Skipping unknown tool: {tool_name}")  # 改为print
        #         continue
                
        #     remaining = limit - len(all_docs)
        #     print(f"ℹ️ INFO: Executing {tool_name} (Goal: {remaining} docs)...")  # 改为print
            
        #     try:
        #         # Fetch slightly more to ensure quality
        #         new_docs = self._execute_tool(tool_name, query, limit=remaining, context=context)
        #         print(f"  -> Fetched {len(new_docs)} docs")  # 改为print
                
        #         # Add unique docs
        #         for doc in new_docs:
        #             if len(all_docs) >= limit:
        #                 break
        #             # Simple duplicate check by URL (if available) or content hash could go here
        #             all_docs.append(doc)
                    
        #     except Exception as e:
        #         print(f"❌ ERROR: Step {tool_name} failed: {e}")  # 改为print
        #         continue
                
        # return all_docs

    def _execute_tool(
        self, 
        tool_name: str, 
        query: str, 
        limit: int, 
        context: Optional[PipelineContext]
    ) -> List[WebisDocument]:
        
        plugin = self.registry.get_source(tool_name)
        if not plugin:
            return []
            
        plugin.initialize(context)
        
        documents = []
        try:
            for doc in plugin.fetch(query, limit=limit, context=context):
                documents.append(doc)
                if len(documents) >= limit:
                    break
        except Exception as e:
            print(f"❌ ERROR: Tool execution failed ({tool_name}): {e}")  # 改为print
            
        return documents