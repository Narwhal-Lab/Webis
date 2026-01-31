"""
Webis Visualizer - Utility functions for the visualization interface
"""

import json
import pandas as pd
from typing import List, Dict, Any
from webis.core.schema import WebisDocument, StructuredResult

def format_document_preview(doc: WebisDocument, max_length: int = 500) -> str:
    """Format document preview for display"""
    content = doc.clean_content or doc.content or "No content available"
    return content[:max_length] + "..." if len(content) > max_length else content

def structured_data_to_dataframe(result: StructuredResult) -> pd.DataFrame:
    """Convert structured result to pandas DataFrame for tabular display"""
    try:
        # Handle both list and dict results
        if isinstance(result.data, list):
            return pd.DataFrame(result.data)
        elif isinstance(result.data, dict):
            return pd.DataFrame([result.data])
        else:
            return pd.DataFrame([{"result": str(result.data)}])
    except Exception as e:
        raise ValueError(f"Failed to convert to DataFrame: {str(e)}")

def extract_pipeline_stats(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and format pipeline statistics"""
    stats = result.get("stats", {})
    
    return {
        "accepted_count": stats.get("accepted_count", 0),
        "rejected_count": stats.get("rejected_count", 0),
        "iterations": stats.get("iterations", 0),
        "success": stats.get("success", False),
        "document_count": result.get("document_count", 0)
    }

def build_chat_context(result: StructuredResult) -> str:
    """Build context for AI chat interface"""
    context_parts = []
    
    # Add structured data summary
    context_parts.append("Structured Data Summary:")
    if isinstance(result.data, list):
        context_parts.append(f"- Found {len(result.data)} items")
        if result.data and isinstance(result.data[0], dict):
            context_parts.append(f"- Fields: {', '.join(result.data[0].keys())}")
    elif isinstance(result.data, dict):
        context_parts.append(f"- Found 1 item with fields: {', '.join(result.data.keys())}")
    
    # Add lineage information
    if result.lineage:
        context_parts.append("\nLineage Information:")
        context_parts.append(f"- Source document IDs: {', '.join(result.lineage.source_doc_ids)}")
        context_parts.append(f"- Model used: {result.lineage.model_name}")
    
    return "\n".join(context_parts)