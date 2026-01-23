"""
RAG Pipeline Module - Core RAG Processing Pipeline

Handles:
- Document fetching from webis pipeline
- Document chunking
- Embedding generation
- Document storage and retrieval
- Returns structured retrieval results for downstream tasks
"""

from typing import Any, Dict, List, Optional
import logging
from pathlib import Path
import json
from datetime import datetime
import numpy as np

from chunker import ChunkingPipeline, Chunk
from embedding_processor import EmbeddingGemmaPlugin
from rag_tools import RAGManager

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Independent RAG Pipeline Module
    
    Responsibilities:
    - Fetch documents using webis pipeline
    - Chunk documents into manageable pieces
    - Generate embeddings for chunks
    - Store documents in vector database
    - Retrieve relevant documents for queries
    
    Output: Structured retrieval results that can be used by downstream tasks
    """
    
    def __init__(
        self,
        rag_store_path: str = "./data/rag_store.json",
        chunk_strategy: str = "sliding_window",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        embedding_model_type: str = "gemma",
        top_k: int = 3,
        min_doc_threshold: int = 1,
        min_score_threshold: float = 0.4,
    ):
        """
        Initialize RAG Pipeline.
        
        Args:
            rag_store_path: Path to RAG storage
            chunk_strategy: Chunking strategy
            chunk_size: Chunk size in characters
            chunk_overlap: Overlap between chunks
            embedding_model_type: Type of embedding model
            top_k: Default number of documents to retrieve
            min_doc_threshold: Minimum number of documents required before fetching from webis
            min_score_threshold: Minimum relevance score threshold for documents
        """
        self.rag_store_path = rag_store_path
        self.top_k = top_k
        self.min_doc_threshold = min_doc_threshold
        self.min_score_threshold = min_score_threshold
        
        # Initialize embedding processor
        try:
            self.embedding_processor = EmbeddingGemmaPlugin(
                model_type=embedding_model_type,
                device="cpu"
            )
            logger.info(f"✓ Initialized {embedding_model_type} embedding processor")
        except Exception as e:
            self.embedding_processor = None
            logger.warning(f"Failed to initialize embedding processor: {e}")
        
        # Initialize chunking pipeline
        self.chunking_pipeline = ChunkingPipeline(
            strategy=chunk_strategy,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            separator="\n\n",
        )
        
        # Initialize RAG manager with embedding processor
        self.rag_manager = RAGManager(
            rag_store_path=rag_store_path,
            embedding_processor=self.embedding_processor
        )
    
    def process_and_store_documents(
        self,
        documents: List[Dict[str, Any]],
        query: str = None,
    ) -> Dict[str, Any]:
        """
        Process documents through pipeline: chunk -> embed -> store.
        
        Args:
            documents: List of documents from webis pipeline, each containing:
                - content: str
                - source: str
                - structured_data: dict (optional)
                - metadata: dict (optional)
            query: Optional query for context (for logging)
            
        Returns:
            {
                "processed_count": int,
                "chunk_count": int,
                "doc_ids": [str],
                "embedding_count": int,
                "documents": [{processed doc info}]
            }
        """
        if not documents:
            logger.warning("No documents to process")
            return {
                "processed_count": 0,
                "chunk_count": 0,
                "doc_ids": [],
                "embedding_count": 0,
                "documents": []
            }
        
        processed_docs = []
        total_chunks = 0
        total_embeddings = 0
        
        for doc in documents:
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            
            if not content or not content.strip():
                logger.debug(f"Skipping empty document from {source}")
                continue
            
            # ===== CHUNKING =====
            chunk_metadata = {
                "source": source,
                "title": doc.get("title", ""),
            }
            chunks = self.chunking_pipeline.process_single(content, metadata=chunk_metadata)
            
            if not chunks:
                logger.debug(f"Document {source} produced no chunks")
                continue
            
            total_chunks += len(chunks)
            logger.info(f"✓ Document {source} chunked into {len(chunks)} chunks")
            
            # ===== EMBEDDING =====
            embeddings = []
            if self.embedding_processor:
                try:
                    chunk_texts = [chunk.content for chunk in chunks]
                    embedding_vectors = self.embedding_processor.embed_texts(chunk_texts)
                    
                    for i, chunk in enumerate(chunks):
                        if embedding_vectors[i] is not None:
                            chunk.embedding = embedding_vectors[i]
                            embeddings.append(embedding_vectors[i])
                    
                    total_embeddings += len(embeddings)
                    logger.info(f"✓ Generated {len(embeddings)} embeddings for {source}")
                except Exception as e:
                    logger.warning(f"Failed to generate embeddings: {e}")
            
            processed_docs.append({
                "content": content,
                "source": source,
                "structured_data": doc.get("structured_data"),
                "embeddings": embeddings,
                "chunks": chunks,
                "metadata": doc.get("metadata", {}),
            })
        
        # ===== STORE =====
        doc_ids = []
        if processed_docs:
            doc_ids = self.rag_manager.add_crawled_documents(processed_docs)
            try:
                self.rag_manager.build_and_save()
                logger.info(f"✓ Stored {len(doc_ids)} documents to RAG")
            except Exception as e:
                logger.warning(f"Failed to build/save RAG: {e}")
        
        return {
            "processed_count": len(processed_docs),
            "chunk_count": total_chunks,
            "doc_ids": doc_ids,
            "embedding_count": total_embeddings,
            "documents": processed_docs,
        }
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve documents relevant to query.
        
        Note: This method only retrieves from existing RAG, without auto-fetching.
        Use get_retrieval_context() with auto_fetch_webis=True for auto-fetching functionality.
        
        Args:
            query: Query text
            top_k: Number of documents to retrieve (uses default if None)
            
        Returns:
            {
                "query": str,
                "top_k": int,
                "documents": [{doc info}],
                "context": str,
                "scores": [float],
                "total_retrieved": int
            }
        """
        if top_k is None:
            top_k = self.top_k
        
        result = self.rag_manager.retrieve_for_query(
            query=query,
            top_k=top_k,
            include_scores=True
        )
        
        return {
            "query": query,
            "top_k": top_k,
            "documents": result.get("documents", []),
            "context": result.get("context", ""),
            "scores": result.get("scores", []),
            "total_retrieved": len(result.get("documents", [])),
        }
    
    def _fetch_from_webis(self, query: str) -> bool:
        """
        Fetch documents from webis pipeline using IntelligentPipeline when retrieval results are insufficient.
        Updated to support newer webis plugin APIs while remaining backward compatible.
        """
        print(f"\n⚠️  Insufficient documents in RAG")
        print(f"📡 Fetching from webis for query: '{query}'...\n")

        # default requirements/context
        requirements = {
            "min_count": 5,
            "relevance_threshold": 0.6,
            "max_iterations": 2,
        }

        try:
            import importlib

            result = None

            # 优先尝试直接导入 internal IntelligentPipeline（如果包存在）
            try:
                ip_mod = importlib.import_module("webis.core.intelligent_pipeline")
                schema_mod = importlib.import_module("webis.core.schema")
                IntelligentPipeline = getattr(ip_mod, "IntelligentPipeline")
                PipelineContext = getattr(schema_mod, "PipelineContext", None)

                pipeline = IntelligentPipeline()
                context = PipelineContext(task=query) if PipelineContext else None
                try:
                    result = pipeline.run(query=query, requirements=requirements, context=context)
                except TypeError:
                    result = pipeline.run(query, requirements, context)
            except (ImportError, ModuleNotFoundError):
                # 如果没有 webis 包，优雅退出（不打印 traceback）
                try:
                    webis_mod = importlib.import_module("webis")
                except (ImportError, ModuleNotFoundError):
                    logger.warning("Webis not available in environment; skipping web fetch")
                    return False

                # try to build a context if available on module
                try:
                    PipelineContext = getattr(webis_mod, "PipelineContext", None)
                    context = PipelineContext(task=query) if PipelineContext else None
                except Exception:
                    context = None

                result = None

                # Try module/class-level IntelligentPipeline
                PipelineCls = None
                if hasattr(webis_mod, "IntelligentPipeline"):
                    PipelineCls = getattr(webis_mod, "IntelligentPipeline")
                elif hasattr(webis_mod, "pipeline") and hasattr(webis_mod.pipeline, "IntelligentPipeline"):
                    PipelineCls = getattr(webis_mod.pipeline, "IntelligentPipeline")

                if PipelineCls:
                    pipeline = PipelineCls()
                    try:
                        result = pipeline.run(query=query, requirements=requirements, context=context)
                    except TypeError:
                        result = pipeline.run(query, requirements, context)
                else:
                    # Try client-style APIs or module-level fetchers
                    client = None
                    if hasattr(webis_mod, "Client"):
                        client = getattr(webis_mod, "Client")()
                    elif hasattr(webis_mod, "WebisClient"):
                        client = getattr(webis_mod, "WebisClient")()

                    if client:
                        if hasattr(client, "fetch_documents"):
                            result = client.fetch_documents(query=query, min_count=requirements["min_count"], relevance_threshold=requirements["relevance_threshold"])
                        elif hasattr(client, "search"):
                            try:
                                result = client.search(query=query, limit=requirements["min_count"])
                            except TypeError:
                                result = client.search(query)
                        elif hasattr(client, "crawl"):
                            result = client.crawl(query=query, max_iterations=requirements["max_iterations"])
                        else:
                            logger.warning("Unsupported webis Client API")
                            return False
                    else:
                        if hasattr(webis_mod, "fetch_documents"):
                            result = webis_mod.fetch_documents(query=query, **requirements)
                        elif hasattr(webis_mod, "search"):
                            try:
                                result = webis_mod.search(query=query, limit=requirements["min_count"])
                            except TypeError:
                                result = webis_mod.search(query)
                        else:
                            logger.warning("No supported webis API found in module")
                            return False

            # Normalize result -> documents (list) and stats (dict)
            documents = []
            stats = {}
            if isinstance(result, dict):
                documents = result.get("documents") or result.get("docs") or result.get("results") or []
                stats = result.get("stats", {})
            elif isinstance(result, list):
                documents = result
                stats = {}
            else:
                documents = getattr(result, "documents", None) or getattr(result, "docs", None) or []
                stats = getattr(result, "stats", {}) or {}

            if not documents:
                logger.warning("Webis returned no documents")
                return False

            print(f"\n✓ Webis fetched {len(documents)} documents")
            if stats:
                print(f"   Stats: {stats}\n")

            # Normalize documents into RAG format
            rag_documents = []
            for doc in documents:
                if isinstance(doc, dict):
                    clean_content = doc.get("clean_content") or doc.get("content", "")
                    meta = doc.get("meta") or doc.get("metadata") or {}
                    validation_score = doc.get("validation_score", doc.get("score", 0.0))
                else:
                    clean_content = getattr(doc, "clean_content", None) or getattr(doc, "content", "")
                    meta = getattr(doc, "meta", None) or getattr(doc, "metadata", None) or {}
                    validation_score = getattr(doc, "validation_score", getattr(doc, "score", 0.0))

                if not clean_content or not str(clean_content).strip():
                    logger.debug("Skipping document with empty content")
                    continue

                if isinstance(meta, dict):
                    source = meta.get("url") or meta.get("source") or meta.get("title") or "unknown"
                    title = meta.get("title", "")
                    source_plugin = meta.get("source_plugin") or meta.get("plugin") or "unknown"
                else:
                    source = getattr(meta, "url", None) or getattr(meta, "source", None) or getattr(meta, "title", "unknown")
                    title = getattr(meta, "title", "")
                    source_plugin = getattr(meta, "source_plugin", None) or getattr(meta, "plugin", None) or "unknown"

                rag_documents.append({
                    "content": clean_content,
                    "source": source,
                    "title": title,
                    "structured_data": None,
                    "metadata": {
                        "from_webis": True,
                        "webis_validation_score": validation_score or 0.0,
                        "source_plugin": source_plugin,
                        "webis_stats": stats,
                        "timestamp": datetime.now().isoformat(),
                    }
                })

            if rag_documents:
                print(f"Processing and storing {len(rag_documents)} documents to RAG...\n")
                store_result = self.process_and_store_documents(rag_documents, query=query)
                print(f"✓ Stored {store_result['processed_count']} documents")
                print(f"✓ Generated {store_result['chunk_count']} chunks")
                print(f"✓ Generated {store_result['embedding_count']} embeddings\n")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to fetch from webis: {e}", exc_info=True)
            return False
    
    def _should_fetch_webis(self, retrieval_result: Dict[str, Any]) -> bool:
        """
        Determine if we should fetch from webis based on retrieval results.
        
        Args:
            retrieval_result: Result from retrieve() method
            
        Returns:
            True if should fetch, False otherwise
        """
        doc_count = len(retrieval_result.get("documents", []))
        scores = retrieval_result.get("scores", [])
        
        # Check if document count is below threshold
        if doc_count < self.min_doc_threshold:
            return True
        
        # Check if top score is below threshold
        if scores and min(scores) < self.min_score_threshold:
            return True
        
        return False
    
    def get_retrieval_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        auto_fetch_webis: bool = True,
    ) -> Dict[str, Any]:
        """
        Get comprehensive context for downstream tasks.
        
        Automatically fetches from webis if retrieval results are insufficient.
        
        Args:
            query: Query text
            top_k: Number of documents to retrieve
            auto_fetch_webis: Automatically fetch from webis if results insufficient
            
        Returns:
            {
                "query": str,
                "retrieved_documents": [...],
                "context_text": str,
                "structured_data": {...},
                "metadata": {...},
                "webis_fetched": bool
            }
        """
        retrieval_result = self.retrieve(query, top_k)
        
        # Check if we need to fetch from webis
        webis_fetched = False
        if auto_fetch_webis and self._should_fetch_webis(retrieval_result):
            webis_fetched = self._fetch_from_webis(query)
            
            # Re-retrieve after fetching
            if webis_fetched:
                retrieval_result = self.retrieve(query, top_k)
        
        # Get full RAG context for better formatting
        context_data = self.rag_manager.rag.retrieve_context(
            query=query,
            top_k=top_k or self.top_k
        )
        
        return {
            "query": query,
            "retrieved_documents": retrieval_result["documents"],
            "context_text": context_data["context"],
            "structured_data": context_data["structured_data"],
            "scores": retrieval_result["scores"],
            "metadata": {
                "retrieval_count": len(retrieval_result["documents"]),
                "top_k": retrieval_result["top_k"],
                "webis_fetched": webis_fetched,
            }
        }
    
    def save(self):
        """Save RAG state to disk"""
        try:
            self.rag_manager.build_and_save()
            logger.info(f"✓ RAG Pipeline saved to {self.rag_store_path}")
        except Exception as e:
            logger.warning(f"Failed to save RAG: {e}")
    
    def load(self):
        """Load RAG state from disk"""
        try:
            self.rag_manager._try_load()
            logger.info(f"✓ RAG Pipeline loaded from {self.rag_store_path}")
        except Exception as e:
            logger.warning(f"Failed to load RAG: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG pipeline statistics"""
        return self.rag_manager.get_stats()
    
    def display_stats(self):
        """Display RAG pipeline statistics"""
        self.rag_manager.display_stats()
