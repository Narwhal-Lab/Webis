"""
Webis RAG Applications

Contains RAG-related application logic including report generation tasks.
"""

from webis.apps.rag.tasks import TaskPipeline, ReportGenerationTask

__all__ = [
    "TaskPipeline",
    "ReportGenerationTask",
]
