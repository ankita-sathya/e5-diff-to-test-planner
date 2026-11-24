"""Sentence embedding module with E5 multilingual support and fast mock mode."""

from typing import Optional, List
import hashlib
import numpy as np
from abc import ABC, abstractmethod


class EmbedderBase(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def embed_passage(self, text: str) -> np.ndarray:
        """Embed a passage (e.g., test case description)."""
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray:
        """Embed a query (e.g., diff summary)."""
        pass


class MockEmbedder(EmbedderBase):
    """
    Fast deterministic embedder using TF-IDF-inspired hash-based features.
    Suitable for testing and fast CI without downloading model weights.
    """
    
    EMBEDDING_DIM = 384
    
    def __init__(self):
        self.vocab: dict[str, int] = {}
        self.vocab_counter = 0
    
    def _get_vocab_index(self, term: str) -> int:
        """Get or create vocabulary index for a term."""
        if term not in self.vocab:
            self.vocab[term] = self.vocab_counter
            self.vocab_counter += 1
        return self.vocab[term]
    
    def _hash_embed(self, text: str) -> np.ndarray:
        """Generate deterministic embedding from text using hash-based features."""
        embedding = np.zeros(self.EMBEDDING_DIM, dtype=np.float32)
        
        # Extract tokens/words
        tokens = text.lower().split()
        
        for token in tokens:
            # Create hash-based indices for this token
            hash_val = int(hashlib.md5(token.encode()).hexdigest(), 16)
            
            # Distribute hash across embedding dimensions
            for i in range(5):
                idx = (hash_val + i * 12345) % self.EMBEDDING_DIM
                embedding[idx] += 1.0 / (i + 1)
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm
        
        return embedding
    
    def embed_passage(self, text: str) -> np.ndarray:
        """Embed passage text."""
        return self._hash_embed(text)
    
    def embed_query(self, text: str) -> np.ndarray:
        """Embed query text."""
        return self._hash_embed(text)


class E5Embedder(EmbedderBase):
    """
    Production E5 multilingual embedder using sentence-transformers.
    Requires transformers, sentence-transformers, and torch.
    """
    
    def __init__(self, model_name: str = "intfloat/multilingual-e5-base"):
        """
        Initialize E5 embedder.
        
        Args:
            model_name: HuggingFace model identifier
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            raise ImportError(
                "sentence-transformers required for E5Embedder. "
                "Install with: pip install sentence-transformers torch"
            )
    
    def embed_passage(self, text: str) -> np.ndarray:
        """
        Embed a passage using E5 model with required 'passage: ' prefix.
        
        Args:
            text: Passage text to embed
            
        Returns:
            Embedding vector (numpy array)
        """
        prefixed_text = f"passage: {text}"
        embedding = self.model.encode(prefixed_text, convert_to_numpy=True)
        return embedding / (np.linalg.norm(embedding) + 1e-8)
    
    def embed_query(self, text: str) -> np.ndarray:
        """
        Embed a query using E5 model with required 'query: ' prefix.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector (numpy array)
        """
        prefixed_text = f"query: {text}"
        embedding = self.model.encode(prefixed_text, convert_to_numpy=True)
        return embedding / (np.linalg.norm(embedding) + 1e-8)


def create_embedder(mock: bool = False, model_name: Optional[str] = None) -> EmbedderBase:
    """
    Factory function to create appropriate embedder.
    
    Args:
        mock: If True, use fast MockEmbedder. If False, use E5Embedder.
        model_name: Optional model name for E5Embedder
        
    Returns:
        EmbedderBase instance
    """
    if mock:
        return MockEmbedder()
    return E5Embedder(model_name or "intfloat/multilingual-e5-base")
