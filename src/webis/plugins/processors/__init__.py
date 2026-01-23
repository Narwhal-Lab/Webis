from .html_cleaner_plugin import HTMLCleanerPlugin
from .html_fetcher_plugin import HtmlFetcherPlugin
from .video_plugin import VideoPlugin
from .pdf_plugin import PDFPlugin
from .document_parse_plugin import DocumentParsePlugin
from .embedding_plugin import EmbeddingGemmaPlugin

__all__ = [
    "HTMLCleanerPlugin",
    "HtmlFetcherPlugin",
    "VideoPlugin",
    "PDFPlugin",
    "DocumentParsePlugin",
    "EmbeddingGemmaPlugin",
]

# Auto-register plugins
from webis.core.plugin import get_default_registry

registry = get_default_registry()
registry.register(HTMLCleanerPlugin())
registry.register(HtmlFetcherPlugin())
registry.register(VideoPlugin())
registry.register(PDFPlugin())
registry.register(DocumentParsePlugin())
# Note: EmbeddingGemmaPlugin not auto-registered as it requires sentence-transformers
# It's instantiated directly in RAG pipeline when needed
