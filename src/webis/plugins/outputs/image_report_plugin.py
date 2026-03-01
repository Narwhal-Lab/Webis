"""
Image Report Plugin — Multi-Agent Orchestrator

Generates a high-quality **image poster / infographic** purely from the
RAG knowledge base via a two-agent pipeline:

1. **RAG Retrieval Agent** (reused from HTML report pipeline)
   Loads & ranks RAG documents, produces a structured *analysis pack*.

2. **Content Planner Agent** (``content_planner_agent.py``)
   Designs the poster layout plan — sections, colours, metrics.

3. **Image Render Agent** (``image_render_agent.py``)
   Calls the Gemini ``gemini-3-pro-image-preview`` model to generate
   the poster as a single PNG image.

The plugin itself (``ImageReportPlugin``) is a thin ``OutputPlugin.save()``
entry-point, identical in shape to ``HtmlReportPlugin``.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from webis.core.plugin import OutputPlugin

from .rag_retrieval_agent import RAGRetrievalAgent
from .content_planner_agent import ContentPlannerAgent
from .image_render_agent import ImageRenderAgent

logger = logging.getLogger(__name__)


class ImageReportPlugin(OutputPlugin):
    """
    Generates a poster-style image report from the RAG knowledge base
    via a three-stage LLM + Gemini pipeline.

    Pipeline:  RAGRetrievalAgent  →  ContentPlannerAgent  →  ImageRenderAgent
                 (analysis pack)      (layout plan JSON)      (PNG image)
    """

    name = "image_report"
    description = (
        "Generates a poster / infographic image via a three-stage pipeline: "
        "RAG retrieval → content planning → Gemini image generation."
    )

    def __init__(self, config=None):
        super().__init__(config)
        self._rag_agent = RAGRetrievalAgent()
        self._planner = ContentPlannerAgent()
        self._renderer = ImageRenderAgent()

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
        """Generate an image report from the RAG knowledge base.

        Parameters
        ----------
        data:
            Ignored — kept for ``OutputPlugin`` interface compatibility.
        context:
            Optional ``PipelineContext``.
        output_dir:
            Directory where the image will be written.
        **kwargs:
            ``rag_store_path`` (str) — path to ``rag_store.json``.
            ``query`` (str) — optional focus query.
        """
        rag_store_path: str | None = kwargs.get("rag_store_path")
        query: str = (kwargs.get("query") or "").strip()

        # --- Locate rag_store.json ---
        if not rag_store_path or not os.path.exists(rag_store_path):
            if output_dir:
                auto = os.path.join(output_dir, "rag_store.json")
                if os.path.exists(auto):
                    rag_store_path = auto
            if not rag_store_path or not os.path.exists(rag_store_path):
                logger.error(
                    "rag_store.json not provided or not found — "
                    "cannot generate image report"
                )
                return False

        if not output_dir:
            output_dir = os.path.dirname(rag_store_path) or "."

        os.makedirs(output_dir, exist_ok=True)

        try:
            image_bytes, mime_type = self._run_pipeline(rag_store_path, query)
        except Exception as e:
            logger.exception("Image report pipeline failed: %s", e)
            return False

        # Determine file extension from MIME type
        _ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
        }
        ext = _ext_map.get(mime_type, ".png")

        # Write the image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"report_{timestamp}{ext}"
        image_path = os.path.join(output_dir, image_filename)

        with open(image_path, "wb") as f:
            f.write(image_bytes)

        logger.info("Image report saved to %s (%d bytes)", image_path, len(image_bytes))
        print(f"\n🖼️  Image report saved: {image_path}")
        return True

    # ------------------------------------------------------------------
    # Pipeline orchestration
    # ------------------------------------------------------------------

    def _run_pipeline(self, rag_store_path: str, query: str) -> tuple[bytes, str]:
        """Coordinate the three agents sequentially.

        Returns ``(image_bytes, mime_type)``.
        """
        logger.info("[Stage 1/3] RAG Retrieval Agent — start")
        analysis_pack = self._rag_agent.run(rag_store_path, query)
        logger.info("[Stage 1/3] RAG Retrieval Agent — done")

        logger.info("[Stage 2/3] Content Planner Agent — start")
        layout_plan = self._planner.run(analysis_pack, query)
        logger.info("[Stage 2/3] Content Planner Agent — done")

        logger.info("[Stage 3/3] Image Render Agent (Gemini) — start")
        image_bytes, mime_type = self._renderer.run(layout_plan, query)
        logger.info("[Stage 3/3] Image Render Agent (Gemini) — done")

        return image_bytes, mime_type
