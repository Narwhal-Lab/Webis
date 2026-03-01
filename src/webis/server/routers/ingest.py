"""
Ingestion API router.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from webis.core.worker import run_pipeline_task

router = APIRouter()

class IngestRequest(BaseModel):
    query: str
    sources: List[str] = ["tavily_search"]
    max_results: int = 10
    pipeline_preset: Optional[str] = "default"
    config_overrides: Optional[Dict[str, Any]] = None

@router.post("/")
async def trigger_ingest(request: IngestRequest):
    """
    Trigger a new ingestion task.
    """
    pipeline_config = {
        "sources": request.sources,
        "max_results": request.max_results,
        "preset": request.pipeline_preset,
        **(request.config_overrides or {})
    }
    
    task = run_pipeline_task.delay(request.query, pipeline_config)
    
    return {"task_id": task.id, "status": "queued"}
