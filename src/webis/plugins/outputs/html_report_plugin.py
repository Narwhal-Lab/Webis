"""
HTML Report Plugin — Multi-Agent Orchestrator

This plugin replaces the previous monolithic two-stage pipeline with a
**three-agent architecture**:

1. **RAG Retrieval Agent** (``rag_retrieval_agent.py``)
   Loads & ranks RAG documents, calls the LLM to produce a structured
   *analysis pack*.

2. **Template Design Agent** (``template_design_agent.py``)
   Consumes the analysis pack and uses the LLM to design a customised
   HTML + CSS template (*presentation pack* + CSS theme).

3. **Report Assembly Agent** (``report_assembly_agent.py``)
   Combines analysis + presentation + CSS and asks the LLM to output
   the final standalone HTML report, with deterministic fallback
   rendering and post-processing (sanitise / validate / repair).

Every agent uses ``get_default_router()`` which provides the shared
LLM Router with automatic primary → fallback model chain (router
fallback).  This mirrors the pattern used by the data-cleaning module.

The plugin itself (``HtmlReportPlugin``) remains a thin
``OutputPlugin.save()`` entry-point so the rest of the pipeline is
unchanged.
"""

from __future__ import annotations

import logging
import os

from webis.core.plugin import OutputPlugin
from webis.core.schema import PipelineContext

from .rag_retrieval_agent import RAGRetrievalAgent
from .template_design_agent import TemplateDesignAgent
from .report_assembly_agent import ReportAssemblyAgent

logger = logging.getLogger(__name__)


class HtmlReportPlugin(OutputPlugin):
    """
    Generates a beautiful HTML report **purely from the RAG knowledge
    base** via a three-agent LLM pipeline.

    No ``result.json`` or ``documents.json`` is required — the only
    mandatory input is ``rag_store.json``.
    """

    name = "html_report"
    description = (
        "Generates a standalone HTML report via a three-agent pipeline: "
        "RAG retrieval → template design → report assembly."
    )

    def __init__(self, config=None):
        super().__init__(config)
        self._rag_agent = RAGRetrievalAgent()
        self._template_agent = TemplateDesignAgent()
        self._assembly_agent = ReportAssemblyAgent()

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def save(
        self,
        data=None,
        context=None,
        output_dir: str | None = None,
        **kwargs,
    ) -> bool:
        """Generate an HTML report from the RAG knowledge base.

        Parameters
        ----------
        data:
            Ignored — kept only for ``OutputPlugin`` interface
            compatibility.
        context:
            Optional ``PipelineContext``.
        output_dir:
            Directory where ``report.html`` will be written.
        **kwargs:
            ``rag_store_path`` (str) — path to ``rag_store.json``.
            ``query`` (str) — optional focus query.
        """
        rag_store_path: str | None = kwargs.get("rag_store_path")
        query: str = (kwargs.get("query") or "").strip()

        if not rag_store_path or not os.path.exists(rag_store_path):
            # Try auto-detect in output_dir
            if output_dir:
                auto = os.path.join(output_dir, "rag_store.json")
                if os.path.exists(auto):
                    rag_store_path = auto
            if not rag_store_path or not os.path.exists(rag_store_path):
                logger.error("rag_store.json not provided or not found — cannot generate HTML report")
                return False

        if not output_dir:
            output_dir = os.path.dirname(rag_store_path) or "."

        try:
            html_content = self._run_multi_agent_pipeline(rag_store_path, query)
        except Exception as e:
            logger.exception("Multi-agent HTML pipeline failed: %s", e)
            return False

        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "report.html")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info("HTML report saved to %s", report_path)
        return True

    # ------------------------------------------------------------------
    # Multi-agent orchestration
    # ------------------------------------------------------------------

    def _run_multi_agent_pipeline(self, rag_store_path: str, query: str) -> str:
        """Coordinate the three agents sequentially."""
        logger.info("[Agent 1/3] RAG Retrieval Agent — start")
        analysis_pack = self._rag_agent.run(rag_store_path, query)
        logger.info("[Agent 1/3] RAG Retrieval Agent — done")

        logger.info("[Agent 2/3] Template Design Agent — start")
        presentation_pack = self._template_agent.run(analysis_pack, query)
        logger.info("[Agent 2/3] Template Design Agent — done")

        logger.info("[Agent 3/3] Report Assembly Agent — start")
        html = self._assembly_agent.run(analysis_pack, presentation_pack, query)
        logger.info("[Agent 3/3] Report Assembly Agent — done")

        return html
