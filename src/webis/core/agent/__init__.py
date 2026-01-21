"""
Agent module for Webis.

Intelligent agents for data acquisition and validation.
"""

from webis.core.agent.crawler_agent import CrawlerAgent
from webis.core.agent.validation_agent import ValidationAgent, AgentState

__all__ = [
    "CrawlerAgent",
    "ValidationAgent", 
    "AgentState",
]
