"""
Webis Pipeline Integration Module

Provides utilities for integrating webis pipeline results into the RAG system.
This module handles document fetching, processing, and storage into RAG.

For end-to-end workflows:
1. Use RAGPipeline for document retrieval
2. Use RAGTask subclasses for downstream processing:
   - PromptEnhancementTask: Generate enhanced prompts
   - DocumentExtractionTask: Extract structured data
   - SummaryTask: Summarize documents
3. Use TaskPipeline to orchestrate task execution

See example usage at the bottom of the module.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import tempfile
from pathlib import Path
import json

logger = logging.getLogger(__name__)

def example_usage():
    """
    Example: Using RAGPipeline + TaskPipeline (recommended approach)
    
    This replaces the old WebisRAGAgent.handle_query() method.
    Saves all results to JSON files for inspection.
    """
    from webis.core.rag.pipeline import RAGPipeline
    from webis.apps.rag.tasks import TaskPipeline, ReportGenerationTask
    from datetime import datetime
    
    # Initialize components
    rag_pipeline = RAGPipeline(
        rag_store_path="./data/rag_store.json",
        embedding_model_type="gemma",
        top_k=5,
    )
    
    task_pipeline = TaskPipeline()
    task_pipeline.add_task(ReportGenerationTask(include_raw_data=True))
    
    # Query workflow
    query = "Summarize the latest news about Artificial Intelligence advancements"
    
    print("=" * 70)
    print("RAG EXAMPLE USAGE")
    print("=" * 70)
    print(f"\n📌 Query: {query}\n")
    
    # Step 1: Get RAG context
    print("Step 1: Retrieving context from RAG...")
    rag_context = rag_pipeline.get_retrieval_context(query, top_k=5)
    print(rag_context)
    print(f"✓ Retrieved {rag_context['metadata']['retrieval_count']} documents")
    
    # Step 2: Execute tasks
    print("\nStep 2: Executing task pipeline...")
    result = task_pipeline.execute(rag_context)
    print(f"✓ Executed {len(result['task_results'])} tasks")
    
    # Display task results
    print("\nStep 3: Task Results\n")
    for task_result in result['task_results']:
        task_name = task_result['task_name']
        success = task_result['success']
        status = "✓" if success else "✗"
        print(f"  {status} Task: {task_name}")
        if success:
            print(f"    Status: Success")
        else:
            print(f"    Error: {task_result.get('error')}")
    
    # Build comprehensive result object
    full_result = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "rag_context": {
            "query": rag_context.get('query'),
            "metadata": rag_context.get('metadata'),
            "context_text_length": len(rag_context.get('context_text', '')),
            "documents_count": len(rag_context.get('documents', [])),
            "scores": rag_context.get('scores'),
        },
        "documents": rag_context.get('documents', []),
        "task_results": result['task_results'],
    }
    
    # Save results to JSON files
    print("\nStep 4: Saving results...\n")
    
    # Create output directory
    output_dir = Path(__file__).resolve().parent.parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full result
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_result_path = output_dir / f"example_usage_full_result_{timestamp}.json"
    with open(full_result_path, 'w', encoding='utf-8') as f:
        json.dump(full_result, f, ensure_ascii=False, indent=2, default=str)
    print(f"✓ Full result saved: {full_result_path}")
    
    # Save RAG context separately
    rag_context_path = output_dir / f"example_usage_rag_context_{timestamp}.json"
    with open(rag_context_path, 'w', encoding='utf-8') as f:
        json.dump(rag_context, f, ensure_ascii=False, indent=2, default=str)
    print(f"✓ RAG context saved: {rag_context_path}")
    
    # # Save task results separately
    # task_results_path = output_dir / f"example_usage_task_results_{timestamp}.json"
    # with open(task_results_path, 'w', encoding='utf-8') as f:
    #     json.dump(result['task_results'], f, ensure_ascii=False, indent=2, default=str)
    # print(f"✓ Task results saved: {task_results_path}")
    
    # Save enhanced prompt if available
    for task_result in result['task_results']:
        if task_result['task_name'] == 'report_generation' and task_result.get('report_content'):
            report_path = output_dir / f"example_usage_report_{timestamp}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(task_result['report_content'])
            print(f"✓ Report saved: {report_path}")
            print(f"  Report stats: {task_result.get('stats', {})}")
    
    print("\n" + "=" * 70)
    print("✓ EXAMPLE USAGE COMPLETED")
    print("=" * 70)
    print(f"\n📁 Output directory: {output_dir}")
    print(f"\n✨ All results have been saved to JSON files")


if __name__ == "__main__":
    example_usage()
