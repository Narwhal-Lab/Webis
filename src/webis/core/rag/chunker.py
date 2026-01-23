"""
Text Chunking Module.

Provides various chunking strategies for breaking long text into smaller chunks
suitable for embedding generation.
"""

from typing import List, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)


class Chunk:
    """Represents a single chunk of text."""
    
    def __init__(self, content: str, chunk_id: str = None, metadata: Dict = None):
        self.content = content
        self.chunk_id = chunk_id or self._generate_id()
        self.metadata = metadata or {}
        self.embedding = None
    
    def _generate_id(self) -> str:
        """Generate a unique chunk ID."""
        import hashlib
        return hashlib.md5(self.content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        """Convert chunk to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
        }


class TextChunker:
    """Text chunking with various strategies."""
    
    def __init__(
        self,
        strategy: str = "sliding_window",
        chunk_size: int = 512,
        overlap: int = 50,
        separator: str = "\n\n",
    ):
        """
        Initialize chunker.
        
        Args:
            strategy: Chunking strategy - 'fixed_size', 'sliding_window', 'sentence', 'paragraph'
            chunk_size: Target chunk size in characters
            overlap: Overlap size between consecutive chunks (for sliding_window)
            separator: Text separator for paragraph-based chunking
        """
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separator = separator
    
    def chunk(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """
        Chunk text based on selected strategy.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata for chunks
            
        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []
        
        if self.strategy == "fixed_size":
            return self._chunk_fixed_size(text, metadata)
        elif self.strategy == "sliding_window":
            return self._chunk_sliding_window(text, metadata)
        elif self.strategy == "sentence":
            return self._chunk_by_sentence(text, metadata)
        elif self.strategy == "paragraph":
            return self._chunk_by_paragraph(text, metadata)
        else:
            logger.warning(f"Unknown strategy: {self.strategy}, using sliding_window")
            return self._chunk_sliding_window(text, metadata)
    
    def _chunk_fixed_size(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """Split text into fixed-size chunks."""
        chunks = []
        for i in range(0, len(text), self.chunk_size):
            chunk_content = text[i : i + self.chunk_size]
            if chunk_content.strip():
                chunk = Chunk(
                    content=chunk_content,
                    metadata={
                        **(metadata or {}),
                        "strategy": "fixed_size",
                        "position": i,
                    },
                )
                chunks.append(chunk)
        return chunks
    
    def _chunk_sliding_window(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """Split text into overlapping chunks."""
        chunks = []
        step = max(1, self.chunk_size - self.overlap)
        
        for i in range(0, len(text), step):
            chunk_content = text[i : i + self.chunk_size]
            if chunk_content.strip():
                chunk = Chunk(
                    content=chunk_content,
                    metadata={
                        **(metadata or {}),
                        "strategy": "sliding_window",
                        "position": i,
                        "overlap": self.overlap,
                    },
                )
                chunks.append(chunk)
            
            # Stop if we've reached the end
            if i + self.chunk_size >= len(text):
                break
        
        return chunks
    
    def _chunk_by_sentence(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """Split text by sentences and group into chunks."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk.strip():
                    chunk = Chunk(
                        content=current_chunk,
                        metadata={
                            **(metadata or {}),
                            "strategy": "sentence",
                        },
                    )
                    chunks.append(chunk)
                current_chunk = sentence
        
        if current_chunk.strip():
            chunk = Chunk(
                content=current_chunk,
                metadata={
                    **(metadata or {}),
                    "strategy": "sentence",
                },
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_by_paragraph(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """Split text by paragraphs and group into chunks."""
        paragraphs = text.split(self.separator)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + len(self.separator) <= self.chunk_size:
                current_chunk += self.separator + para if current_chunk else para
            else:
                if current_chunk.strip():
                    chunk = Chunk(
                        content=current_chunk,
                        metadata={
                            **(metadata or {}),
                            "strategy": "paragraph",
                        },
                    )
                    chunks.append(chunk)
                current_chunk = para
        
        if current_chunk.strip():
            chunk = Chunk(
                content=current_chunk,
                metadata={
                    **(metadata or {}),
                    "strategy": "paragraph",
                },
            )
            chunks.append(chunk)
        
        return chunks


class ChunkingPipeline:
    """Pipeline for chunking documents with consistent configuration."""
    
    def __init__(
        self,
        strategy: str = "sliding_window",
        chunk_size: int = 512,
        overlap: int = 50,
        separator: str = "\n\n",
    ):
        self.chunker = TextChunker(
            strategy=strategy,
            chunk_size=chunk_size,
            overlap=overlap,
            separator=separator,
        )
    
    def process_documents(
        self,
        documents: List[Dict],
        content_key: str = "content",
    ) -> List[Dict]:
        """
        Process multiple documents and return chunked results.
        
        Args:
            documents: List of document dicts with 'content' field
            content_key: Key in document dict containing the text content
            
        Returns:
            List of document dicts with added 'chunks' field
        """
        processed = []
        
        for doc in documents:
            if content_key not in doc:
                logger.warning(f"Document missing '{content_key}' field")
                processed.append(doc)
                continue
            
            content = doc[content_key]
            metadata = {
                "source": doc.get("source", ""),
                "title": doc.get("title", ""),
            }
            
            chunks = self.chunker.chunk(content, metadata=metadata)
            
            doc_with_chunks = doc.copy()
            doc_with_chunks["chunks"] = chunks
            processed.append(doc_with_chunks)
        
        return processed
    
    def process_single(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """Process a single text string and return chunks."""
        return self.chunker.chunk(text, metadata=metadata)
