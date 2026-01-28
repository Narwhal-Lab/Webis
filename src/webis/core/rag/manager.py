"""
RAG toolset - Tool functions provided for crawlers and pipelines.

Used for quick integration of RAG into existing webis_pipeline.
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from webis.core.rag.component import RAGComponent, SimpleVectorStore

logger = logging.getLogger(__name__)


class RAGManager:
    """RAG Manager - Simplify the use and management of RAG"""

    def __init__(
        self,
        rag_store_path: str = "./RAG/rag_store.json",
        auto_load: bool = True,
        use_external_embeddings: bool = True,
        embedding_processor=None,
    ):
        """
        Args:
            rag_store_path: Vector storage path
            auto_load: Whether to automatically load existing storage
            use_external_embeddings: Whether to use embeddings from processor (default) or TF-IDF
            embedding_processor: Optional EmbeddingGemmaPlugin instance for generating embeddings
        """
        vector_store = SimpleVectorStore(
            use_external_embeddings=use_external_embeddings,
            embedding_processor=embedding_processor
        )
        self.rag = RAGComponent(vector_store=vector_store, store_path=rag_store_path)
        self.rag_store_path = rag_store_path
        self.embedding_processor = embedding_processor

        if auto_load:
            self._try_load()

    def _try_load(self):
        """Try to load existing RAG storage"""
        store_path = Path(self.rag_store_path)
        if store_path.exists():
            try:
                self.rag.load()
                logger.info(f"✓ Loaded existing RAG store from {self.rag_store_path}")
            except Exception as e:
                logger.warning(f"Failed to load RAG store: {e}")

    def add_crawled_documents(
        self,
        documents: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Batch add crawled documents to RAG.
        
        Args:
            documents: Document list, each document contains:
                - content: str - Cleaned text
                - source: str - Source (URL or filename)
                - structured_data: dict (optional) - Structured data
                - embeddings: list (optional) - Pre-computed embeddings from processor
                - chunks: list (optional) - Chunk contents
                - metadata: dict (optional) - Additional metadata
                
        Returns:
            Document ID list
        """
        doc_ids = []
        for doc in documents:
            # Handle embeddings: use first embedding or generate using processor
            embedding = None
            
            # 1. First try to use pre-computed embeddings
            if doc.get("embeddings") and len(doc["embeddings"]) > 0:
                embeddings_list = doc["embeddings"]
                # Use average of all chunk embeddings or first embedding
                if isinstance(embeddings_list[0], (list, tuple)):
                    embedding = np.mean(embeddings_list, axis=0) if len(embeddings_list) > 0 else None
                else:
                    embedding = embeddings_list[0] if embeddings_list else None
                
                if embedding is not None:
                    embedding = np.array(embedding, dtype=np.float32)
            
            # 2. If no pre-computed embeddings and processor available, generate them
            if embedding is None and self.embedding_processor is not None:
                try:
                    content = doc.get("content", "")
                    if content and content.strip():
                        embedding_vec = self.embedding_processor.embed_text(content)
                        if embedding_vec is not None:
                            embedding = np.array(embedding_vec, dtype=np.float32)
                except Exception as e:
                    logger.debug(f"Failed to generate embedding for document: {e}")
            
            doc_id = self.rag.add_from_pipeline(
                clean_text=doc.get("content", ""),
                source=doc.get("source", "unknown"),
                structured_data=doc.get("structured_data"),
                metadata=doc.get("metadata", {}),
                embedding=embedding,
            )
            doc_ids.append(doc_id)

        logger.info(f"Added {len(doc_ids)} documents to RAG")
        return doc_ids

    def retrieve_for_query(
        self,
        query: str,
        top_k: int = 3,
        include_scores: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant documents for the query.
        
        Args:
            query: Query text
            top_k: Number of documents to return
            include_scores: Whether to include similarity scores
            
        Returns:
            {
                "query": "...",
                "documents": [...],
                "context": "...",
                "scores": [...] (if include_scores=True)
            }
        """
        context_data = self.rag.retrieve_context(query, top_k=top_k)

        result = {
            "query": query,
            "documents": [
                {
                    "source": doc.source,
                    "content": doc.content,  # 返回完整内容，不截断
                    "structured_data": doc.structured_data,
                }
                for doc in context_data["documents"]
            ],
            "context": context_data["context"],
        }

        # Optional: Calculate similarity scores
        if include_scores:
            retrieved = self.rag.vector_store.retrieve(query, top_k=top_k)
            result["scores"] = [score for _, score in retrieved]

        return result

    def enhance_agent_prompt(
        self,
        base_prompt: str,
        user_query: str,
        rag_top_k: int = 3,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Add RAG context to Agent prompt.
        
        Args:
            base_prompt: Original prompt
            user_query: User query
            rag_top_k: Retrieve top-k documents
            
        Returns:
            (Enhanced prompt, context data)
        """
        enhanced_prompt, context_data = self.rag.format_prompt_with_context(
            user_query=user_query,
            original_prompt=base_prompt,
            context_top_k=rag_top_k,
        )
        return enhanced_prompt, context_data

    def build_and_save(self):
        """Build index and save RAG storage"""
        self.rag.build_index()
        self.rag.save()
        logger.info(f"✓ RAG index built and saved to {self.rag_store_path}")

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG statistics"""
        return self.rag.stats()

    def display_stats(self):
        """Print RAG statistics"""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print("RAG Component Statistics")
        print("=" * 60)
        print(f"Total documents: {stats['total_documents']}")
        print(f"Indexed: {stats['indexed']}")
        print(f"Store path: {stats['store_path']}")

        if stats["documents"]:
            print("\nDocument list:")
            for doc in stats["documents"]:
                has_data = "✓" if doc["has_structured_data"] else "✗"
                print(
                    f"  - {doc['source']:<40} "
                    f"(ID: {doc['doc_id']}, Length: {doc['content_length']}, Structured: {has_data})"
                )


def create_rag_from_pipeline_output(
    extraction_results: List[Dict[str, Any]],
    rag_store_path: str = "./data/rag_store.json",
) -> RAGManager:
    """
    Create RAG from pipeline extraction results.
    
    Args:
        extraction_results: Pipeline extraction result list, each containing:
            - clean_text: str
            - source: str
            - structured_data: dict
            - metadata: dict (optional)
        rag_store_path: RAG storage path
        
    Returns:
        Initialized RAGManager
    """
    manager = RAGManager(rag_store_path=rag_store_path, auto_load=False)

    documents = [
        {
            "content": result.get("clean_text", ""),
            "source": result.get("source", "unknown"),
            "structured_data": result.get("structured_data"),
            "metadata": result.get("metadata", {}),
        }
        for result in extraction_results
    ]

    manager.add_crawled_documents(documents)
    manager.build_and_save()

    return manager


# ============================================================================
# Helper functions for integration into webis_pipeline
# ============================================================================


def integrate_rag_to_pipeline(
    pipeline_output_dir: str,
    rag_store_path: str = "./data/rag_store.json",
) -> RAGManager:
    """
    Integrate RAG from webis_pipeline output.
    
    Assume pipeline output structure as follows:
    output_dir/
      ├── extracted_texts/
      │   ├── source1_clean.txt
      │   ├── source2_clean.txt
      │   └── ...
      └── structured_data/
          ├── source1_structured.json
          ├── source2_structured.json
          └── ...
    
    Args:
        pipeline_output_dir: Pipeline output directory
        rag_store_path: RAG storage path
        
    Returns:
        Initialized RAGManager
    """
    output_dir = Path(pipeline_output_dir)
    manager = RAGManager(rag_store_path=rag_store_path, auto_load=False)

    # Read clean text
    text_dir = output_dir / "extracted_texts"
    struct_dir = output_dir / "structured_data"

    documents = []

    if text_dir.exists():
        for text_file in sorted(text_dir.glob("*_clean.txt")):
            source_name = text_file.stem.replace("_clean", "")

            # 读取文本
            with open(text_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 尝试读取对应的结构化数据
            struct_file = struct_dir / f"{source_name}_structured.json"
            structured_data = None

            if struct_file.exists():
                try:
                    with open(struct_file, "r", encoding="utf-8") as f:
                        structured_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load structured data from {struct_file}: {e}")

            documents.append(
                {
                    "content": content,
                    "source": source_name,
                    "structured_data": structured_data,
                    "metadata": {"file": str(text_file)},
                }
            )

    # Add to RAG
    if documents:
        manager.add_crawled_documents(documents)
        manager.build_and_save()
        logger.info(f"✓ Integrated {len(documents)} documents from pipeline output")
    else:
        logger.warning("No documents found in pipeline output")

    return manager


if __name__ == "__main__":
    # Simple test
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        print("Testing RAGManager...")

        manager = RAGManager(rag_store_path=f"{tmpdir}/test_rag.json")

        # Add sample documents
        sample_docs = [
            {
                "content": "Deep learning has made breakthrough progress in the field of computer vision.",
                "source": "ai_tech_1.txt",
                "structured_data": {"field": "AI", "topic": "Deep Learning"},
            },
            {
                "content": "Quantum computing technology is developing rapidly, IBM has released a new quantum chip.",
                "source": "quantum_1.txt",
                "structured_data": {"field": "Quantum Computing", "company": "IBM"},
            },
        ]

        manager.add_crawled_documents(sample_docs)
        manager.build_and_save()

        # Test retrieval
        result = manager.retrieve_for_query("deep learning and computer vision")
        print(f"\nRetrieval results: Found {len(result['documents'])} documents")

        # Display statistics
        manager.display_stats()
