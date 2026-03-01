from .managed_search_plugin import TavilySearchPlugin, BochaSearchPlugin
from .github_plugin import GitHubSearchPlugin
from .gnews_plugin import GNewsPlugin
from .hackernews_plugin import HackerNewsPlugin
from .semantic_scholar_plugin import SemanticScholarPlugin
from .serpapi_plugin import SerpApiPlugin
from .bright_data_plugin import BrightDataPlugin
from .serper_plugin import SerperSearchPlugin
from .exa_firecrawl_plugin import ExaFirecrawlCrawler

__all__ = [
    "TavilySearchPlugin",
    "BochaSearchPlugin",
    "GitHubSearchPlugin",
    "GNewsPlugin",
    "HackerNewsPlugin",
    "SemanticScholarPlugin",
    "SerpApiPlugin",
    "SerperSearchPlugin",
    "ExaFirecrawlCrawler",
]

# Auto-register plugins
from webis.core.plugin import get_default_registry

registry = get_default_registry()
registry.register(TavilySearchPlugin())
registry.register(BochaSearchPlugin())
registry.register(GitHubSearchPlugin())
registry.register(GNewsPlugin())
registry.register(HackerNewsPlugin())
registry.register(SemanticScholarPlugin())
registry.register(SerpApiPlugin())
registry.register(BrightDataPlugin())
registry.register(SerperSearchPlugin())
registry.register(ExaFirecrawlCrawler())
