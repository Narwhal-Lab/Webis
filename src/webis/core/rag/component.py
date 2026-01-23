"""
Small RAG Component: Provides retrieval-augmented generation of prior knowledge for Agents.

Features:
1. Store structured data and clean text in a lightweight vector database
2. Retrieve relevant documents based on query
3. Generate context prompts for Agents

Design Philosophy:
- Small number of files with high relevance, using lightweight solution (no heavy vector DB required)
- Use BM25 hybrid vector retrieval to balance speed and accuracy
- Support incremental updates and persistence
"""

from __future__ import annotations

import json
import logging
import os
import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RAGDocument:
    """Document entry in RAG"""

    doc_id: str  # Unique identifier
    content: str  # Original text content
    source: str  # Source (filename or URL)
    structured_data: Optional[Dict[str, Any]] = None  # Structured data (JSON extraction result)
    metadata: Dict[str, Any] = None  # Additional metadata
    embedding: Optional[np.ndarray] = None  # Vectorized representation
    timestamp: str = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class SimpleVectorStore:
    """
    Lightweight vector storage - using in-memory storage + local serialization.
    
    Supports embeddings from external embedding processor (preferred) or TF-IDF fallback.
    Suitable for small data volume (<10k documents) scenarios.
    """

    def __init__(self, use_external_embeddings: bool = True, embedding_processor=None):
        """
        Args:
            use_external_embeddings: If True, use embeddings from embedding processor.
                                    If False, fall back to TF-IDF.
            embedding_processor: Optional EmbeddingGemmaPlugin instance for on-demand embedding generation
        """
        self.documents: Dict[str, RAGDocument] = {}
        self.use_external_embeddings = use_external_embeddings
        self.embedding_processor = embedding_processor
        self._init_embedding_scheme()

    def _init_embedding_scheme(self):
        """Initialize embedding scheme - prefer external embeddings, fall back to TF-IDF"""
        self.vectorizer = None
        self._use_tfidf = False
        
        if self.use_external_embeddings:
            logger.info("Using external embedding processor (OpenAI embeddings) - TF-IDF vectorizer will be lazy-initialized if needed")
        # If not using external embeddings, TF-IDF will be initialized on demand in build_index()
    
    def _init_tfidf_vectorizer(self):
        """Lazy initialize TF-IDF vectorizer only when needed"""
        if self.vectorizer is not None:
            return  # Already initialized
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(max_features=100, ngram_range=(1, 2))
            self._use_tfidf = True
            logger.info("✓ Initialized TF-IDF embedding scheme on demand")
        except ImportError:
            logger.warning("sklearn not available, will use hash-based embedding for fallback")
            self._use_tfidf = False

    def add_document(
        self,
        content: str,
        source: str,
        doc_id: Optional[str] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[np.ndarray] = None,
    ) -> str:
        """Add document to vector storage
        
        Args:
            content: Document content
            source: Document source
            doc_id: Document ID (auto-generated if None)
            structured_data: Structured data from extraction
            metadata: Additional metadata
            embedding: Pre-computed embedding (from embedding processor)
        """
        if doc_id is None:
            doc_id = f"{source}_{len(self.documents)}"

        doc = RAGDocument(
            doc_id=doc_id,
            content=content,
            source=source,
            structured_data=structured_data,
            metadata=metadata or {},
            embedding=embedding,  # Use pre-computed embedding if provided
        )

        self.documents[doc_id] = doc
        print(f"Added document {doc_id} from {source} {'(with external embedding)' if embedding is not None else '(embedding pending)'}\n")
        return doc_id

    def build_index(self):
        """Build index (calculate vector representations for all documents)
        
        If documents already have embeddings from external processor, skip computation.
        Otherwise, lazily initialize TF-IDF or use hash-based scheme.
        """
        if not self.documents:
            logger.warning("No documents to index")
            return

        # Check if documents already have embeddings from external processor
        has_external_embeddings = all(
            doc.embedding is not None for doc in self.documents.values()
        )
        
        if has_external_embeddings:
            logger.info(f"✓ Using pre-computed embeddings from external processor for {len(self.documents)} documents")
            return
        
        # No external embeddings found - try to generate them using embedding processor
        if self.use_external_embeddings and self.embedding_processor is not None:
            try:
                logger.info(f"Generating embeddings using EmbeddingGemmaPlugin for {len(self.documents)} documents...")
                texts = [doc.content for doc in self.documents.values()]
                embeddings = self.embedding_processor.embed_texts(texts)
                
                for i, doc_id in enumerate(self.documents.keys()):
                    if embeddings[i] is not None:
                        self.documents[doc_id].embedding = np.array(embeddings[i], dtype=np.float32)
                
                logger.info(f"✓ Generated embeddings for {len(self.documents)} documents")
                return
            except Exception as e:
                logger.warning(f"Failed to generate embeddings with processor: {e}")
        
        # Fallback to TF-IDF if processor unavailable
        # Lazy initialize TF-IDF if using external embeddings mode (fallback scenario)
        if self.use_external_embeddings and self.vectorizer is None:
            self._init_tfidf_vectorizer()
        
        # Use TF-IDF if available
        if self._use_tfidf and self.vectorizer is not None:
            texts = [doc.content for doc in self.documents.values()]
            tfidf_matrix = self.vectorizer.fit_transform(texts)

            # Convert to dense vector storage
            for i, doc_id in enumerate(self.documents.keys()):
                self.documents[doc_id].embedding = tfidf_matrix[i].toarray().flatten()
            logger.info(f"✓ Built TF-IDF index for {len(self.documents)} documents")
        else:
            # Simple hash-based vector (fallback when TF-IDF not available)
            for doc in self.documents.values():
                doc.embedding = self._hash_embedding(doc.content)
            logger.info(f"✓ Built hash-based embeddings for {len(self.documents)} documents")

    def _hash_embedding(self, text: str, dim: int = 128) -> np.ndarray:
        """Simple hash-based vector (fallback when TF-IDF is not available)"""
        hash_val = hash(text)
        rng = np.random.RandomState(hash_val % (2**31))
        return rng.randn(dim).astype(np.float32)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Tuple[RAGDocument, float]]:
        """
        Retrieve documents most relevant to the query using embeddings.
        
        Uses embeddings from processor (preferred) or TF-IDF (fallback).
        
        Args:
            query: Query text
            top_k: Number of documents to return
            score_threshold: Score threshold (0-1)
            
        Returns:
            [(document, score), ...] Sorted list of documents with similarity scores
        """
        if not self.documents:
            return []

        if self._use_tfidf and not all(doc.embedding is not None for doc in self.documents.values()):
            # Need to compute embeddings using TF-IDF
            query_vec = self.vectorizer.transform([query]).toarray().flatten()
            scores = []

            for doc_id, doc in self.documents.items():
                if doc.embedding is None:
                    continue
                # Cosine similarity
                sim = np.dot(query_vec, doc.embedding) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(doc.embedding) + 1e-8
                )
                scores.append((doc_id, float(sim)))
        else:
            # Use external embeddings or hash-based embeddings
            if all(doc.embedding is not None for doc in self.documents.values()):
                # All documents have embeddings - use them directly
                query_vec = None
                
                # Try embedding processor first
                if self.use_external_embeddings and self.embedding_processor is not None:
                    try:
                        query_vec = self.embedding_processor.embed_text(query)
                        if query_vec is not None:
                            query_vec = np.array(query_vec, dtype=np.float32).flatten()
                    except Exception as e:
                        logger.debug(f"Failed to embed query with processor: {e}")
                        query_vec = None
                
                # Fallback to TF-IDF
                if query_vec is None:
                    try:
                        if self.vectorizer:
                            query_vec = self.vectorizer.transform([query]).toarray().flatten()
                        else:
                            query_vec = self._hash_embedding(query)
                    except Exception:
                        query_vec = self._hash_embedding(query)
                
                scores = []
                for doc_id, doc in self.documents.items():
                    if doc.embedding is None:
                        continue
                    # Ensure vectors are same dimension
                    doc_emb = np.array(doc.embedding).flatten()
                    query_emb = np.array(query_vec).flatten()
                    
                    # Pad or trim to same dimension
                    min_dim = min(len(doc_emb), len(query_emb))
                    doc_emb = doc_emb[:min_dim]
                    query_emb = query_emb[:min_dim]
                    
                    # Cosine similarity
                    sim = np.dot(query_emb, doc_emb) / (
                        np.linalg.norm(query_emb) * np.linalg.norm(doc_emb) + 1e-8
                    )
                    scores.append((doc_id, float(sim)))
            else:
                # Fall back to simple text similarity
                scores = self._simple_text_similarity(query)

        # Sort and filter
        scores = sorted(scores, key=lambda x: x[1], reverse=True)
        scores = [(doc_id, score) for doc_id, score in scores if score > score_threshold]
        scores = scores[:top_k]

        results = [(self.documents[doc_id], score) for doc_id, score in scores]
        return results

    def _simple_text_similarity(self, query: str) -> List[Tuple[str, float]]:
        """Simple keyword-based similarity (fallback)"""
        query_words = set(query.lower().split())
        scores = []

        for doc_id, doc in self.documents.items():
            doc_words = set(doc.content.lower().split())
            # Jaccard相似度
            if not query_words and not doc_words:
                sim = 1.0
            else:
                sim = len(query_words & doc_words) / len(query_words | doc_words)
            scores.append((doc_id, sim))

        return scores

    def save(self, path: str):
        """Save vector storage to disk"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "documents": {
                doc_id: {
                    "doc_id": doc.doc_id,
                    "content": doc.content,
                    "source": doc.source,
                    "structured_data": doc.structured_data,
                    "metadata": doc.metadata,
                    "embedding": doc.embedding.tolist() if doc.embedding is not None else None,
                    "timestamp": doc.timestamp,
                }
                for doc_id, doc in self.documents.items()
            }
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 保存vectorizer
        if self._use_tfidf and self.vectorizer is not None:
            vectorizer_path = str(path).replace(".json", "_vectorizer.pkl")
            with open(vectorizer_path, "wb") as f:
                pickle.dump(self.vectorizer, f)

        logger.info(f"Saved vector store to {path}")

    def load(self, path: str):
        """Load vector storage from disk"""
        path = Path(path)
        if not path.exists():
            logger.warning(f"Vector store file {path} not found")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.documents = {}
        for doc_id, doc_data in data["documents"].items():
            embedding = doc_data["embedding"]
            if embedding is not None:
                embedding = np.array(embedding, dtype=np.float32)

            doc = RAGDocument(
                doc_id=doc_data["doc_id"],
                content=doc_data["content"],
                source=doc_data["source"],
                structured_data=doc_data["structured_data"],
                metadata=doc_data["metadata"],
                embedding=embedding,
                timestamp=doc_data["timestamp"],
            )
            self.documents[doc_id] = doc

        # 加载vectorizer
        vectorizer_path = str(path).replace(".json", "_vectorizer.pkl")
        if os.path.exists(vectorizer_path):
            with open(vectorizer_path, "rb") as f:
                self.vectorizer = pickle.load(f)
                self._use_tfidf = True

        logger.info(f"Loaded {len(self.documents)} documents from {path}")


class RAGComponent:
    """
    Agent-oriented RAG component - provides integrated interface.
    
    Responsibilities:
    1. Manage document addition/update/retrieval
    2. Generate context prompts for Agents
    3. Support hybrid retrieval of structured data and text
    """

    def __init__(
        self,
        vector_store: Optional[SimpleVectorStore] = None,
        store_path: Optional[str] = None,
    ):
        """
        Args:
            vector_store: Vector storage instance (create new if None)
            store_path: Persistence path for vector storage
        """
        self.vector_store = vector_store or SimpleVectorStore()
        self.store_path = store_path or "./rag_store.json"

    def add_from_pipeline(
        self,
        clean_text: str,
        source: str,
        structured_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[np.ndarray] = None,
    ) -> str:
        """
        Add processed documents from data pipeline.
        
        Args:
            clean_text: Cleaned text
            source: Document source
            structured_data: Structured extraction result (JSON)
            metadata: Additional metadata (e.g., crawl time, URL, etc.)
            embedding: Pre-computed embedding from embedding processor
            
        Returns:
            Document ID
        """
        return self.vector_store.add_document(
            content=clean_text,
            source=source,
            structured_data=structured_data,
            metadata=metadata,
            embedding=embedding,
        )

    def build_index(self):
        """Build vector index - call after adding all documents"""
        self.vector_store.build_index()

    def retrieve_context(
        self,
        query: str,
        top_k: int = 3,
        include_structured: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieve context related to the query.
        
        Args:
            query: User query
            top_k: Number of documents to return
            include_structured: Whether to include structured data
            
        Returns:
            {
                "context": "...",  # Formatted context text
                "documents": [...],  # Original document list
                "structured_data": {...}  # Structured data (optional)
            }
        """
        retrieved = self.vector_store.retrieve(query, top_k=top_k)

        if not retrieved:
            return {
                "context": "",
                "documents": [],
                "structured_data": {},
            }

        context_parts = []
        structured_all = {}

        for doc, score in retrieved:
            # Add text context
            context_parts.append(f"[Source: {doc.source}] (Relevance: {score:.2f})\n{doc.content}\n")

            # Collect structured data
            if include_structured and doc.structured_data:
                key = f"{doc.source}_{doc.doc_id}"
                structured_all[key] = doc.structured_data

        context = "\n".join(context_parts)

        return {
            "context": context,
            "documents": [doc for doc, _ in retrieved],
            "structured_data": structured_all,
        }

    def format_prompt_with_context(
        self,
        user_query: str,
        original_prompt: str,
        context_top_k: int = 3,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate prompt with retrieved context for Agent.
        
        Args:
            user_query: Original user query
            original_prompt: Original extraction/inference prompt
            context_top_k: Retrieve top-k documents
            
        Returns:
            (Enhanced prompt, retrieved context data)
        """
        context_data = self.retrieve_context(user_query, top_k=context_top_k)
        # print(context_data)
        # print("\n")
        
        # Format structured data into readable text
        structured_text = ""
        if context_data["structured_data"]:
            structured_parts = []
            for key, data in context_data["structured_data"].items():
                if isinstance(data, dict):
                    formatted_data = "\n".join(f"  - {k}: {v}" for k, v in data.items())
                    structured_parts.append(f"**{key}**:\n{formatted_data}")
                else:
                    structured_parts.append(f"**{key}**: {data}")
            structured_text = "\n\n".join(structured_parts)
        
        if context_data["context"] or structured_text:
            enhanced_prompt = f"""## Reference Information (Prior Knowledge from Data Pipeline)

You have access to the following retrieved documents and structured insights from our knowledge base. Use this information to provide accurate, well-informed responses.

### Retrieved Documents:
{context_data['context'] or "No relevant documents found."}

### Structured Data Insights:
{structured_text or "No structured data available."}

---

## User Query and Task

{original_prompt}

### Instructions for Response:
- Reference the provided documents and structured data when relevant.
- Provide detailed, evidence-based answers using the prior knowledge above.
- Maintain consistency with the retrieved information."""
        else:
            enhanced_prompt = original_prompt

        return enhanced_prompt, context_data

    def save(self):
        """Save RAG component to disk"""
        self.vector_store.save(self.store_path)
        print(f"RAG component saved to {self.store_path} \n")

    def load(self):
        """Load RAG component from disk"""
        self.vector_store.load(self.store_path)
        logger.info(f"RAG component loaded from {self.store_path}")

    def stats(self) -> Dict[str, Any]:
        """Get RAG component statistics"""
        return {
            "total_documents": len(self.vector_store.documents),
            "indexed": all(doc.embedding is not None for doc in self.vector_store.documents.values()),
            "store_path": self.store_path,
            "documents": [
                {
                    "doc_id": doc.doc_id,
                    "source": doc.source,
                    "content_length": len(doc.content),
                    "has_structured_data": doc.structured_data is not None,
                }
                for doc in self.vector_store.documents.values()
            ],
        }
