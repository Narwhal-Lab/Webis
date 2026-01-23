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


def process_webis_documents(
    documents: List[Dict[str, Any]],
    rag_store_path: str = "./data/rag_store.json",
    chunk_strategy: str = "sliding_window",
    chunk_size: int = 512,
    embedding_model_type: str = "gemma",
) -> Dict[str, Any]:
    """
    Process documents from webis pipeline and store in RAG.
    
    Args:
        documents: List of documents from webis pipeline
        rag_store_path: Path to RAG storage
        chunk_strategy: Chunking strategy
        chunk_size: Chunk size
        embedding_model_type: Embedding model type
        
    Returns:
        Processing result with document IDs and statistics
    """
    from webis.core.rag.pipeline import RAGPipeline
    
    if not documents:
        logger.warning("No documents to process")
        return {
            "success": False,
            "document_count": 0,
            "message": "No documents provided"
        }
    
    try:
        # Initialize RAG pipeline
        rag_pipeline = RAGPipeline(
            rag_store_path=rag_store_path,
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            embedding_model_type=embedding_model_type,
        )
        
        # Process and store documents
        result = rag_pipeline.process_and_store_documents(documents, query="")
        
        logger.info(f"Successfully processed {len(documents)} documents")
        
        return {
            "success": True,
            "document_count": len(documents),
            "result": result,
            "message": "Documents processed and stored successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to process webis documents: {e}")
        return {
            "success": False,
            "document_count": len(documents),
            "error": str(e),
            "message": "Failed to process documents"
        }


class WebisRAGAgent:
    """
    DEPRECATED: Use RAGPipeline + TaskPipeline directly instead.
    
    This class is maintained for backward compatibility only.
    For new code, directly use:
    - RAGPipeline: For document retrieval
    - RAGTask subclasses: For downstream processing
    - TaskPipeline: For orchestrating tasks
    
    Example:
        from webis.core.rag.pipeline import RAGPipeline
        from webis.apps.rag.tasks import TaskPipeline, PromptEnhancementTask
        
        rag = RAGPipeline()
        tasks = TaskPipeline()
        tasks.add_task(PromptEnhancementTask(llm_agent=llm))
        
        context = rag.get_retrieval_context(query)
        results = tasks.execute(context)
    """

    def __init__(self, llm=None, **kwargs):
        """
        DEPRECATED: Use RAGPipeline + TaskPipeline instead.
        
        This is provided for backward compatibility with old code.
        """
        logger.warning(
            "WebisRAGAgent is deprecated. Use RAGPipeline + TaskPipeline directly:\n"
            "  from webis.core.rag.pipeline import RAGPipeline\n"
            "  from webis.apps.rag.tasks import TaskPipeline, PromptEnhancementTask\n"
            "  rag = RAGPipeline()\n"
            "  tasks = TaskPipeline()\n"
            "  tasks.add_task(PromptEnhancementTask(llm_agent=llm))"
        )
        self.llm = llm
        self._kwargs = kwargs

    def handle_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        DEPRECATED: Use RAGPipeline.retrieve() + TaskPipeline.execute() instead.
        """
        from webis.core.rag.pipeline import RAGPipeline
        from webis.apps.rag.tasks import TaskPipeline, PromptEnhancementTask
        
        logger.warning("handle_query() is deprecated. Use RAGPipeline + TaskPipeline directly")
        
        # Initialize pipeline
        rag_pipeline = RAGPipeline(**self._kwargs)
        tasks = TaskPipeline()
        tasks.add_task(PromptEnhancementTask(llm_agent=self.llm))
        
        # Execute workflow
        rag_context = rag_pipeline.get_retrieval_context(query)
        task_result = tasks.execute(rag_context)
        
        return {
            "query": query,
            "rag_result": rag_context,
            "task_results": task_result["task_results"],
        }




def example_usage():
    """
    Example: Using RAGPipeline + TaskPipeline (recommended approach)
    
    This replaces the old WebisRAGAgent.handle_query() method.
    Saves all results to JSON files for inspection.
    """
    from webis.core.rag.pipeline import RAGPipeline
    from webis.apps.rag.tasks import TaskPipeline, PromptEnhancementTask
    from datetime import datetime
    
    # Initialize components
    rag_pipeline = RAGPipeline(
        rag_store_path="./data/rag_store.json",
        embedding_model_type="gemma",
        top_k=3,
    )
    
    task_pipeline = TaskPipeline()
    task_pipeline.add_task(PromptEnhancementTask(llm_agent=None))
    
    # Query workflow
    query = "tell me the recent news of china economy"
    
    print("=" * 70)
    print("RAG EXAMPLE USAGE")
    print("=" * 70)
    print(f"\n📌 Query: {query}\n")
    
    # Step 1: Get RAG context
    print("Step 1: Retrieving context from RAG...")
    rag_context = rag_pipeline.get_retrieval_context(query, top_k=3)
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
    output_dir = Path(__file__).resolve().parent.parent / "data"
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
        if task_result['task_name'] == 'prompt_enhancement' and task_result.get('enhanced_prompt'):
            enhanced_prompt_path = output_dir / f"example_usage_enhanced_prompt_{timestamp}.txt"
            with open(enhanced_prompt_path, 'w', encoding='utf-8') as f:
                f.write(task_result['enhanced_prompt'])
            print(f"✓ Enhanced prompt saved: {enhanced_prompt_path}")
    
    print("\n" + "=" * 70)
    print("✓ EXAMPLE USAGE COMPLETED")
    print("=" * 70)
    print(f"\n📁 Output directory: {output_dir}")
    print(f"\n✨ All results have been saved to JSON files")


if __name__ == "__main__":
    example_usage()
