"""
Validation Agent for Webis.

Intelligent agent that validates data quality and relevance,
making decisions about which documents to keep or reject.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from webis.core.llm.base import LLMRouter, get_default_router
from webis.core.schema import WebisDocument

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """State tracking for the validation agent."""
    
    query: str
    intent: Dict[str, Any]
    required_count: int
    current_docs: List[WebisDocument] = field(default_factory=list)
    rejected_docs: List[WebisDocument] = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 5
    failed_tools: List[str] = field(default_factory=list)
    
    def should_continue(self) -> bool:
        """Check if agent should continue crawling."""
        return (
            len(self.current_docs) < self.required_count and
            self.attempts < self.max_attempts
        )
    
    def add_decision(self, doc: WebisDocument, verdict: str, reason: str) -> None:
        """Record a decision about a document."""
        if verdict == "ACCEPT":
            self.current_docs.append(doc)
            url = doc.meta.url if doc.meta else doc.id
            logger.info(f"✓ ACCEPTED: {url} - {reason}")
        else:
            self.rejected_docs.append(doc)
            url = doc.meta.url if doc.meta else doc.id
            logger.info(f"✗ REJECTED: {url} - {reason}")


class ValidationAgent:
    """
    Intelligent agent that validates data quality and relevance.
    
    Capabilities:
    - Check if documents are relevant to user query
    - Assess data quality
    - Make decisions (accept/reject)
    - Track state across validation cycles
    
    Example:
        >>> agent = ValidationAgent()
        >>> is_valid, score, reason = agent.check_relevance(doc, "Python 3.12 features", {...})
    """
    
    def __init__(self, router: Optional[LLMRouter] = None):
        self.router = router or get_default_router()
    
    def check_quantity(
        self, 
        documents: List[WebisDocument], 
        required_count: int
    ) -> Tuple[bool, int]:
        """
        Check if we have enough documents.
        
        Args:
            documents: Current document list
            required_count: Required number of documents
            
        Returns:
            (is_sufficient, shortage_count)
        """
        current = len(documents)
        is_sufficient = current >= required_count
        shortage = max(0, required_count - current)
        
        logger.info(f"Quantity check: {current}/{required_count} documents")
        return is_sufficient, shortage
    
    def check_relevance(
        self,
        document: WebisDocument,
        query: str,
        intent: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float, str]:
        """
        Check if a document is relevant to the user's query.
        
        Args:
            document: Document to validate
            query: Original user query
            intent: Parsed user intent (optional)
            
        Returns:
            (is_relevant, confidence_score, reason)
        """
        # Get document content
        content = document.clean_content or document.content or ""
        if not content:
            return False, 0.0, "Empty content"
        
        # Build prompt
        system, user = self._build_relevance_prompt(
            content[:2000],  # Limit to first 2000 chars
            query,
            intent or {}
        )
        
        try:
            # Call LLM
            response = self.router.chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.0,
                max_tokens=500
            )
            
            # Parse response
            result = self._parse_validation_response(response.content)
            
            is_relevant = result.get("is_relevant", False)
            confidence = result.get("confidence", 0.0)
            reason = result.get("reason", "No reason provided")
            
            print(f"Relevance check: {confidence:.2f} - {reason}")
            return is_relevant, confidence, reason
            
        except Exception as e:
            logger.error(f"Relevance check failed: {e}")
            # Default to accepting if check fails to avoid losing valid data
            return True, 0.5, f"Validation error: {str(e)}"
    
    def _build_relevance_prompt(
        self,
        doc_content: str,
        query: str,
        intent: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Build LLM prompt for relevance checking."""
        
        system = (
            "You are a data quality validator. Your job is to determine if a document "
            "is relevant and useful for the user's query and intent."
        )
        
        intent_str = json.dumps(intent, ensure_ascii=False) if intent else "Not specified"
        
        user = f'''User Query: "{query}"
User Intent: {intent_str}

Document Content (first 2000 chars):
{doc_content}

Analyze if this document is relevant and useful for the user's query.

Respond with STRICT JSON:
{{
    "is_relevant": true or false,
    "confidence": 0.0 to 1.0,
    "reason": "brief explanation",
    "verdict": "ACCEPT" or "REJECT"
}}

Examples of REJECT:
- Query: "Python 3.12 new features" but document is about Python syntax basics
- Query: "Latest AI news" but document is a tutorial from 2020
- Query: "React hooks" but document is about Angular
- Document is navigation menu, ads, or repeated template text

Examples of ACCEPT:
- Document directly addresses the query topic
- Document provides relevant and up-to-date information
- Document contains substantive content (not just links or snippets)
'''
        
        return system, user
    
    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM validation response."""
        try:
            # Try to extract JSON from response
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
                result = json.loads(json_str)
                
                # Ensure required fields
                if "is_relevant" not in result:
                    result["is_relevant"] = result.get("verdict") == "ACCEPT"
                if "confidence" not in result:
                    result["confidence"] = 0.8 if result["is_relevant"] else 0.2
                if "reason" not in result:
                    result["reason"] = "No reason provided"
                    
                return result
                
        except Exception as e:
            logger.warning(f"Failed to parse validation response: {e}")
        
        # Fallback: conservative acceptance
        return {
            "is_relevant": True,
            "confidence": 0.5,
            "reason": "Could not parse validation response",
            "verdict": "ACCEPT"
        }
    
    def validate_batch(
        self,
        documents: List[WebisDocument],
        query: str,
        intent: Optional[Dict[str, Any]] = None,
        threshold: float = 0.7
    ) -> Tuple[List[WebisDocument], List[WebisDocument]]:
        """
        Validate a batch of documents.
        
        Args:
            documents: Documents to validate
            query: User query
            intent: User intent
            threshold: Minimum confidence score to accept
            
        Returns:
            (accepted_documents, rejected_documents)
        """
        accepted = []
        rejected = []
        
        for doc in documents:
            is_relevant, confidence, reason = self.check_relevance(doc, query, intent)
            
            if is_relevant and confidence >= threshold:
                accepted.append(doc)
                url = doc.meta.url if doc.meta else doc.id
                logger.info(f"✓ ACCEPT ({confidence:.2f}): {url}")
            else:
                rejected.append(doc)
                url = doc.meta.url if doc.meta else doc.id
                logger.info(f"✗ REJECT ({confidence:.2f}): {url} - {reason}")
        
        logger.info(f"Batch validation: {len(accepted)} accepted, {len(rejected)} rejected")
        return accepted, rejected
