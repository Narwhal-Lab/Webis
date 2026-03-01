from webis.core.plugin import get_default_registry
from .html_report_plugin import HtmlReportPlugin
from .image_report_plugin import ImageReportPlugin
from .rag_retrieval_agent import RAGRetrievalAgent
from .template_design_agent import TemplateDesignAgent
from .report_assembly_agent import ReportAssemblyAgent
from .content_planner_agent import ContentPlannerAgent
from .image_render_agent import ImageRenderAgent

__all__ = [
    "HtmlReportPlugin",
    "ImageReportPlugin",
    "RAGRetrievalAgent",
    "TemplateDesignAgent",
    "ReportAssemblyAgent",
    "ContentPlannerAgent",
    "ImageRenderAgent",
]

# Auto-register
get_default_registry().register(HtmlReportPlugin())
get_default_registry().register(ImageReportPlugin())
