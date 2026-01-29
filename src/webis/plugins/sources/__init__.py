from .managed_search_plugin import TavilySearchPlugin, BochaSearchPlugin
from .duckduckgo_plugin import DuckDuckGoPlugin
from .github_plugin import GitHubSearchPlugin
from .gnews_plugin import GNewsPlugin
from .hackernews_plugin import HackerNewsPlugin
from .semantic_scholar_plugin import SemanticScholarPlugin
from .serpapi_plugin import SerpApiPlugin
from .bright_data_plugin import BrightDataPlugin

__all__ = [
    "TavilySearchPlugin",
    "BochaSearchPlugin",
    "DuckDuckGoPlugin",
    "GitHubSearchPlugin",
    "GNewsPlugin",
    "HackerNewsPlugin",
    "SemanticScholarPlugin",
    "SerpApiPlugin",
]

# Auto-register plugins
from webis.core.plugin import get_default_registry

registry = get_default_registry()
registry.register(TavilySearchPlugin())
registry.register(BochaSearchPlugin())
registry.register(DuckDuckGoPlugin())
registry.register(GitHubSearchPlugin())
registry.register(GNewsPlugin())
registry.register(HackerNewsPlugin())
registry.register(SemanticScholarPlugin())
registry.register(SerpApiPlugin())
registry.register(BrightDataPlugin())
