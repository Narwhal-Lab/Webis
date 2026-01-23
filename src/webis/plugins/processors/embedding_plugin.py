"""
Embedding Processor Module.

Generates embeddings for text chunks using various embedding models.
Supports local models (Gemma, BERT) and API-based models.
"""

from typing import List, Optional, Union
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Base class for embedding models."""
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        raise NotImplementedError
    
    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts."""
        return [self.embed_text(text) for text in texts]
    
    def get_embedding_dim(self) -> int:
        """Get the dimension of the embedding vector."""
        raise NotImplementedError


class GemmaEmbedding(EmbeddingModel):
    """Gemma embedding using sentence-transformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", device: str = "cpu"):
        """
        Initialize Gemma embedding model.
        
        Args:
            model_name: Model identifier from HuggingFace
            device: Device to use ('cpu' or 'cuda')
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self.embedding_dim = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            
            # Get embedding dimension by encoding a dummy text
            dummy_embedding = self.model.encode("test", convert_to_numpy=True)
            self.embedding_dim = len(dummy_embedding)
            
            logger.info(f"✓ Embedding model loaded. Dimension: {self.embedding_dim}")
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return None
        
        try:
            if self.model is None:
                self._initialize_model()
            
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return None
    
    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts (batch processing)."""
        if not texts:
            return []
        
        try:
            if self.model is None:
                self._initialize_model()
            
            # Filter out empty texts
            valid_texts = [t for t in texts if t and t.strip()]
            if not valid_texts:
                return [None] * len(texts)
            
            embeddings = self.model.encode(valid_texts, convert_to_numpy=True)
            result = []
            idx = 0
            
            for text in texts:
                if text and text.strip():
                    result.append(embeddings[idx].tolist())
                    idx += 1
                else:
                    result.append(None)
            
            return result
        except Exception as e:
            logger.warning(f"Failed to generate batch embeddings: {e}")
            return [None] * len(texts)
    
    def get_embedding_dim(self) -> int:
        """Get the dimension of the embedding vector."""
        if self.embedding_dim is None:
            if self.model is None:
                self._initialize_model()
            dummy_embedding = self.model.encode("test", convert_to_numpy=True)
            self.embedding_dim = len(dummy_embedding)
        return self.embedding_dim


class OpenAIEmbedding(EmbeddingModel):
    """OpenAI embedding API."""
    
    def __init__(self, api_key: str = None, model_name: str = "text-embedding-3-small"):
        """
        Initialize OpenAI embedding.
        
        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model_name: OpenAI model name
        """
        self.api_key = api_key or self._get_api_key()
        self.model_name = model_name
        self.client = None
        self.embedding_dim = None
        self._initialize_client()
    
    def _get_api_key(self) -> str:
        """Get API key from environment."""
        import os
        return os.getenv("OPENAI_API_KEY", "")
    
    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            
            if not self.api_key:
                raise ValueError("OpenAI API key not found")
            
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"✓ OpenAI client initialized for model: {self.model_name}")
        except ImportError:
            logger.error("openai not installed. Install with: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return None
        
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model_name
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding from OpenAI: {e}")
            return None
    
    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        try:
            valid_texts = [t for t in texts if t and t.strip()]
            if not valid_texts:
                return [None] * len(texts)
            
            response = self.client.embeddings.create(
                input=valid_texts,
                model=self.model_name
            )
            
            embeddings_dict = {item.index: item.embedding for item in response.data}
            result = []
            idx = 0
            
            for text in texts:
                if text and text.strip():
                    result.append(embeddings_dict.get(idx, None))
                    idx += 1
                else:
                    result.append(None)
            
            return result
        except Exception as e:
            logger.warning(f"Failed to generate batch embeddings from OpenAI: {e}")
            return [None] * len(texts)
    
    def get_embedding_dim(self) -> int:
        """Get the dimension of the embedding vector."""
        if self.embedding_dim is None:
            embedding = self.embed_text("test")
            if embedding:
                self.embedding_dim = len(embedding)
        return self.embedding_dim or 1536  # Default for text-embedding-3-small


class BGEEmbedding(EmbeddingModel):
    """BGE (BAAI General Embedding) embedding model."""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = "cpu"):
        """
        Initialize BGE embedding model.
        
        Args:
            model_name: BGE model identifier from HuggingFace
            device: Device to use ('cpu' or 'cuda')
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self.tokenizer = None
        self.embedding_dim = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the BGE model."""
        try:
            from transformers import AutoModel, AutoTokenizer
            
            logger.info(f"Loading BGE model: {self.model_name}")
            self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Get embedding dimension
            dummy_embedding = self._encode_single("test")
            if dummy_embedding is not None:
                self.embedding_dim = len(dummy_embedding)
            
            logger.info(f"✓ BGE model loaded. Dimension: {self.embedding_dim}")
        except ImportError:
            logger.error("transformers not installed. Install with: pip install transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize BGE model: {e}")
            raise
    
    def _encode_single(self, text: str) -> Optional[List[float]]:
        """Encode a single text using BGE model."""
        try:
            import torch
            
            inputs = self.tokenizer(
                text,
                max_length=512,
                padding=True,
                truncation=True,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state[:, 0]  # Use [CLS] token
                embedding = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
            return embedding[0].cpu().numpy().tolist()
        except Exception as e:
            logger.warning(f"Failed to encode text with BGE: {e}")
            return None
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return None
        
        return self._encode_single(text)
    
    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        try:
            import torch
            
            valid_texts = [t for t in texts if t and t.strip()]
            if not valid_texts:
                return [None] * len(texts)
            
            inputs = self.tokenizer(
                valid_texts,
                max_length=512,
                padding=True,
                truncation=True,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state[:, 0]
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
            result = []
            idx = 0
            for text in texts:
                if text and text.strip():
                    result.append(embeddings[idx].cpu().numpy().tolist())
                    idx += 1
                else:
                    result.append(None)
            
            return result
        except Exception as e:
            logger.warning(f"Failed to generate batch embeddings with BGE: {e}")
            return [None] * len(texts)
    
    def get_embedding_dim(self) -> int:
        """Get the dimension of the embedding vector."""
        if self.embedding_dim is None:
            embedding = self.embed_text("test")
            if embedding:
                self.embedding_dim = len(embedding)
        return self.embedding_dim or 384


class EmbeddingGemmaPlugin:
    """
    Embedding processor plugin that provides a unified interface for embedding generation.
    Defaults to sentence-transformers but can be configured for other models.
    """
    
    def __init__(
        self,
        model_type: str = "gemma",
        model_name: str = None,
        device: str = "cpu",
        cache_embeddings: bool = True,
    ):
        """
        Initialize EmbeddingGemmaPlugin.
        
        Args:
            model_type: Type of model ('gemma', 'openai', 'bge')
            model_name: Specific model name. If None, uses default for model_type
            device: Device to use ('cpu' or 'cuda')
            cache_embeddings: Whether to cache embeddings for repeated texts
        """
        self.model_type = model_type.lower()
        self.device = device
        self.cache_embeddings = cache_embeddings
        self.embedding_cache = {} if cache_embeddings else None
        self.model = self._initialize_model(model_name)
    
    def _initialize_model(self, model_name: str = None) -> EmbeddingModel:
        """Initialize the appropriate embedding model."""
        try:
            if self.model_type == "gemma":
                model_name = model_name or "sentence-transformers/all-MiniLM-L6-v2"
                logger.info(f"Initializing Gemma embedding with model: {model_name}")
                return GemmaEmbedding(model_name=model_name, device=self.device)
            
            elif self.model_type == "openai":
                logger.info("Initializing OpenAI embedding")
                return OpenAIEmbedding(model_name=model_name or "text-embedding-3-small")
            
            elif self.model_type == "bge":
                model_name = model_name or "BAAI/bge-small-en-v1.5"
                logger.info(f"Initializing BGE embedding with model: {model_name}")
                return BGEEmbedding(model_name=model_name, device=self.device)
            
            else:
                logger.warning(f"Unknown model type: {self.model_type}, using Gemma")
                return GemmaEmbedding(device=self.device)
        
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector or None if failed
        """
        if not text or not text.strip():
            return None
        
        # Check cache first
        if self.cache_embeddings and text in self.embedding_cache:
            return self.embedding_cache[text]
        
        # Generate embedding
        embedding = self.model.embed_text(text)
        
        # Cache result
        if self.cache_embeddings and embedding is not None:
            self.embedding_cache[text] = embedding
        
        return embedding
    
    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Check cache and separate uncached texts
        results = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            if self.cache_embeddings and text in self.embedding_cache:
                results.append(self.embedding_cache[text])
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            embeddings = self.model.embed_texts(uncached_texts)
            
            for idx, embedding in zip(uncached_indices, embeddings):
                results[idx] = embedding
                
                # Cache result
                if self.cache_embeddings and embedding is not None:
                    self.embedding_cache[uncached_texts[uncached_indices.index(idx)]] = embedding
        
        return results
    
    def get_embedding_dim(self) -> int:
        """Get the dimension of embedding vectors."""
        return self.model.get_embedding_dim()
    
    def clear_cache(self):
        """Clear the embedding cache."""
        if self.cache_embeddings:
            self.embedding_cache.clear()
            logger.info("Embedding cache cleared")


def create_embedding_processor(
    model_type: str = "gemma",
    model_name: str = None,
    device: str = "cpu",
) -> EmbeddingGemmaPlugin:
    """
    Factory function to create an embedding processor.
    
    Args:
        model_type: Type of model ('gemma', 'openai', 'bge')
        model_name: Specific model name
        device: Device to use ('cpu' or 'cuda')
        
    Returns:
        EmbeddingGemmaPlugin instance
    """
    return EmbeddingGemmaPlugin(
        model_type=model_type,
        model_name=model_name,
        device=device,
    )
