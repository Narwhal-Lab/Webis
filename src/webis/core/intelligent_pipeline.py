"""
Intelligent Pipeline for Webis.

Orchestrates crawling, cleaning, and validation with automatic re-crawling
based on data quality and relevance checks.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from webis.core.agent.crawler_agent import CrawlerAgent
from webis.core.agent.validation_agent import ValidationAgent, AgentState
from webis.core.schema import WebisDocument, PipelineContext
from webis.plugins.processors.html_cleaner_plugin import HTMLCleanerPlugin

logger = logging.getLogger(__name__)


class IntelligentPipeline:
    """
    Intelligent pipeline with agent-based validation and auto-correction.
    
    Features:
    - Automatic crawling with quantity checks
    - LLM-based content cleaning
    - Relevance validation with re-crawling
    - Adaptive decision-making
    
    Example:
        >>> pipeline = IntelligentPipeline()
        >>> results = pipeline.run(
        ...     query="Python 3.12 new features",
        ...     requirements={'min_count': 10, 'relevance_threshold': 0.7}
        ... )
    """
    
    def __init__(
        self,
        crawler_agent: Optional[CrawlerAgent] = None,
        validation_agent: Optional[ValidationAgent] = None
    ):
        self.crawler_agent = crawler_agent or CrawlerAgent()
        self.validation_agent = validation_agent or ValidationAgent()
        self.html_cleaner = HTMLCleanerPlugin()
        
    def run(
        self,
        query: str,
        requirements: Optional[Dict[str, Any]] = None,
        context: Optional[PipelineContext] = None
    ) -> Dict[str, Any]:
        """
        Execute intelligent pipeline with validation loop.
        
        Args:
            query: User query
            requirements: Requirements dict with:
                - min_count: Minimum documents required (default: 10)
                - relevance_threshold: Minimum relevance score (default: 0.7)
                - max_iterations: Maximum crawl attempts (default: 3)
            context: Pipeline context
            
        Returns:
            Dict with:
                - documents: List of validated documents
                - stats: Statistics about the run
                - rejected: List of rejected documents
        """
        # Parse requirements
        requirements = requirements or {}
        min_count = requirements.get('min_count', 10)
        relevance_threshold = requirements.get('relevance_threshold', 0.7)
        max_iterations = requirements.get('max_iterations', 3)
        
        # Parse intent from query
        intent = self._parse_intent(query)
        
        # Initialize state
        state = AgentState(
            query=query,
            intent=intent,
            required_count=min_count,
            max_attempts=max_iterations
        )
        
        print(f"🚀 Starting intelligent pipeline for query: '{query}' \n")
        print(f"   Requirements: {min_count} docs, threshold={relevance_threshold} \n")
        
        # Main validation loop
        for iteration in range(max_iterations):
            state.attempts = iteration + 1
            print(f"\n{'='*60} \n")
            print(f"Iteration {iteration + 1}/{max_iterations}")
            print(f"{'='*60}")
            
            # Step 1: Check if we need more documents
            is_sufficient, shortage = self.validation_agent.check_quantity(
                state.current_docs,
                state.required_count
            )
            
            if is_sufficient:
                print(f"✓ Sufficient documents collected ({len(state.current_docs)}/{min_count})")
                break
            
            # Step 2: Crawl more documents
            crawl_limit = shortage + 5  # Get a few extra to account for rejections
            print(f"📥 Crawling {crawl_limit} documents...")
            
            # Identify tools that failed in previous iterations (fetched 0 docs)
            # We track this in a simple way for now
            excluded_tools = state.failed_tools
            if excluded_tools:
                print(f"   Excluding failed tools: {excluded_tools}")

            raw_docs = self.crawler_agent.run(
                task=query,
                limit=crawl_limit,
                context=context,
                excluded_tools=excluded_tools
            )
            
            # Update failed tools tracking
            # This is tricky because we don't know exactly which tool produced which doc easily
            # without inspecting metadata.
            # Simple heuristic: If raw_docs is empty, ALL tools tried in this run failed.
            # But CrawlerAgent tries multiple tools.
            # BETTER APPROACH: CrawlerAgent should return metadata about which tools failed.
            # For now, let's look at the docs we got.
            successful_tools = set()
            for doc in raw_docs:
                if doc.meta and doc.meta.source_plugin:
                    successful_tools.add(doc.meta.source_plugin)
            
            if not raw_docs:
                print(f"❌ No documents fetched in iteration {iteration + 1}")
                # Mark strategy as failed
                failed = self.crawler_agent.last_used_tools
                if failed:
                    print(f"   Marking tools as failed for next iteration: {failed}")
                    state.failed_tools.extend(failed)
                    # Deduplicate
                    state.failed_tools = list(set(state.failed_tools))
            else:
                 print(f"   Fetched {len(raw_docs)} raw documents from: {successful_tools}")
            
            # Step 3: Clean documents
            print(f"🧹 Cleaning {len(raw_docs)} documents...")
            cleaned_docs = self._clean_documents(raw_docs, context)
            print(f"   Cleaned {len(cleaned_docs)} documents")
            
            # Step 4: Validate relevance
            print(f"🔍 Validating relevance...")
            for doc in cleaned_docs:
                # Skip if already validated
                if doc in state.current_docs or doc in state.rejected_docs:
                    continue
                
                is_relevant, score, reason = self.validation_agent.check_relevance(
                    doc, query, intent
                )
                
                # Make decision
                if is_relevant and score >= relevance_threshold:
                    state.add_decision(doc, "ACCEPT", f"Score: {score:.2f} - {reason}")
                else:
                    state.add_decision(doc, "REJECT", f"Score: {score:.2f} - {reason}")
            
            # Status update
            print(f"\n📊 Status: {len(state.current_docs)}/{min_count} validated documents")
            
        # Final results
        print(f"\n{'='*60}")
        print(f"Pipeline completed")
        print(f"{'='*60}")
        print(f"✓ Accepted: {len(state.current_docs)} documents")
        print(f"✗ Rejected: {len(state.rejected_docs)} documents")
        print(f"🔄 Iterations: {state.attempts}/{max_iterations}")
        
        return {
            "documents": state.current_docs,
            "rejected": state.rejected_docs,
            "stats": {
                "accepted_count": len(state.current_docs),
                "rejected_count": len(state.rejected_docs),
                "iterations": state.attempts,
                "success": len(state.current_docs) >= min_count,
            }
        }
    
    def _parse_intent(self, query: str) -> Dict[str, Any]:
        """
        Parse user intent from query.
        
        Could be enhanced with LLM, but for now returns basic structure.
        """
        return {
            "query": query,
            "keywords": query.split(),
            "timestamp": "now"  # Could parse temporal intent
        }
    
    def _clean_documents(
        self,
        documents: List[WebisDocument],
        context: Optional[PipelineContext] = None
    ) -> List[WebisDocument]:
        """Clean documents using HTML cleaner plugin."""
        cleaned = []
        
        for doc in documents:
            try:
                cleaned_doc = self.html_cleaner.process(doc, context)
                if cleaned_doc and cleaned_doc.clean_content:
                    cleaned.append(cleaned_doc)
                else:
                    url = doc.meta.url if doc.meta else doc.id
                    print(f"⚠️  Failed to clean: {url}")
            except Exception as e:
                url = doc.meta.url if doc.meta else doc.id
                print(f"❌ Cleaning error for {url}: {e}")
                continue
        
        return cleaned
