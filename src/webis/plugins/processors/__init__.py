from .html_cleaner_plugin import HTMLCleanerPlugin
from .html_fetcher_plugin import HtmlFetcherPlugin
from .video_plugin import VideoPlugin
from .pdf_plugin_v2 import PDFPluginV2
from .document_parse_plugin import DocumentParsePlugin

__all__ = [
    "HtmlCleanerPlugin",
    "HtmlFetcherPlugin",
    "VideoPlugin",
    "PDFPlugin",
    "DocumentParsePlugin",
]

# Auto-register plugins
from webis.core.plugin import get_default_registry

registry = get_default_registry()
registry.register(HTMLCleanerPlugin())
registry.register(HtmlFetcherPlugin())
registry.register(VideoPlugin())
registry.register(PDFPluginV2())
registry.register(DocumentParsePlugin())
