"""
Crawler Agent for Webis v2.

Migrated from v1 LangChainDataSourceAgent.
Responsible for selecting the appropriate source plugin for a given task
and executing the search/crawl operation.
"""

from __future__ import annotations

import json
import re
import math
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
        
        - If it's about code, prioritize GitHub.
        - If it's about news, prioritize GNews.
        - Otherwise, consider all available search/crawl tools (exa_firecrawl_crawler, serper_search, tavily_search, bocha_search, bright_data) based on their specific strengths.
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
        #     # 2. Ask LLM to pick prioritized tools (if router available)
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
                
        #         # Filter out excluded tools from the plan
        #         plan = [step for step in plan if step.get("tool") not in excluded_tools]
                    
        #     if not plan:
        #         print("No plan found in JSON, falling back to default.")
                
        #     print(f"ℹ️ INFO: Agent plan: {[step['tool'] for step in plan]}")

        # except Exception as e:
        #     print(f"⚠️ WARNING: LLM planning failed: {e}. Using fallback strategy.")
        #     # Fallback strategy: Use available tools (Tavily, Bocha, BrightData)
        #     fallback_tools = ["tavily_search", "bocha_search", "bright_data"]
        #     plan = [{"tool": t, "query": task, "reason": "Fallback"} for t in fallback_tools if t in sources]
        #     print(f"ℹ️ INFO: Using fallback plan: {[step['tool'] for step in plan]}")

        # 4. Execute plan (Default if LLM disabled or returns empty)
        all_docs = []
        
        # Default plan if no plan generated by LLM
        if not plan:
            plan = [
                {"tool": "exa_firecrawl_crawler", "query": task},
                {"tool": "serper_search", "query": task},
                {"tool": "tavily_search", "query": task},
                {"tool": "bocha_search", "query": task},
                {"tool": "bright_data", "query": task}
            ]
            # Filter out excluded tools from default plan
            plan = [step for step in plan if step.get("tool") not in excluded_tools]
            if not plan:
                print("ℹ️ INFO: Exclusions emptied default plan. Retrying with full default tool list.")
                plan = [
                    {"tool": "exa_firecrawl_crawler", "query": task},
                    {"tool": "serper_search", "query": task},
                    {"tool": "tavily_search", "query": task},
                    {"tool": "bocha_search", "query": task},
                    {"tool": "bright_data", "query": task}
                ]

        self.last_used_tools = [step['tool'] for step in plan]

        for step in plan:
            if len(all_docs) >= limit:
                break
                
            tool_name = step.get("tool")
            query = step.get("query", task)
            
            # Balanced strategy: Split remaining limit among remaining active tools in plan
            # But we must respect the tool queue order.
            
            # Simple approach: Give each tool an equal share of the TOTAL limit, 
            # or try to fill the remaining gap.
            
            # Count how many tools are left to run (including this one)
            remaining_tools_count = len(plan) - self.last_used_tools.index(tool_name) 
            # Note: last_used_tools is not updated yet, this is tricky. 
            # Let's just use index in plan.
            
            idx = 0
            for i, p in enumerate(plan):
                if p['tool'] == tool_name and p['query'] == query:
                    idx = i
                    break
            
            remaining_tools_count = len(plan) - idx
            
            # Calculate target for this specific tool to ensure balance
            # e.g. Limit 10, 2 tools. Tool 1 gets 5. Tool 2 gets 5 (or remaining).
            target_per_tool = math.ceil(limit / len(plan))
            
            # But we also need to fill the gap if previous tools under-delivered
            remaining_global_need = limit - len(all_docs)
            
            # The limit for THIS tool should be at least target_per_tool, 
            # but capped at remaining_global_need
            tool_limit = min(target_per_tool, remaining_global_need)
            
            # If we are the LAST tool, we must try to fill everything
            if remaining_tools_count == 1:
                tool_limit = remaining_global_need
            
            # Don't fetch 0
            tool_limit = max(1, tool_limit)
            
            print(f"ℹ️ INFO: Executing {tool_name} (Goal: {tool_limit} docs, Global Need: {remaining_global_need})...")
            
            try:
                # Use the generic execution method via registry
                new_docs = self._execute_tool(tool_name, query, limit=tool_limit, context=context)
                print(f"  -> Fetched {len(new_docs)} docs")
                
                for doc in new_docs:
                    if len(all_docs) >= limit:
                        break
                    all_docs.append(doc)
            except Exception as e:
                print(f"❌ ERROR: Step {tool_name} failed: {e}")
                continue
        
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
