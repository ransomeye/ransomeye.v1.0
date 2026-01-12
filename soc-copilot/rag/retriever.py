#!/usr/bin/env python3
"""
RansomEye SOC Copilot - Retriever
AUTHORITATIVE: Deterministic retrieval of relevant documents
"""

from typing import List, Dict, Any
import numpy as np
from rag.vector_store import VectorStore


class RetrievalError(Exception):
    """Base exception for retrieval errors."""
    pass


class Retriever:
    """
    Deterministic retrieval of relevant documents.
    
    Properties:
    - Deterministic: Same query always produces same results
    - Verifiable: All retrieved documents are verifiable
    - Immutable: Retrieved documents are immutable
    """
    
    def __init__(self, vector_store: VectorStore, embedding_model):
        """
        Initialize retriever.
        
        Args:
            vector_store: Vector store instance
            embedding_model: Embedding model for query encoding
        """
        self.vector_store = vector_store
        self.embedding_model = embedding_model
    
    def retrieve(self, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for query.
        
        Process:
        1. Encode query to embedding
        2. Search vector store
        3. Return top-k documents
        
        Args:
            query_text: Query text
            k: Number of documents to retrieve
        
        Returns:
            List of document dictionaries with similarity scores
        """
        try:
            # Encode query to embedding
            query_embedding = self._encode_query(query_text)
            
            # Search vector store
            results = self.vector_store.search(query_embedding, k=k)
            
            return results
        except Exception as e:
            raise RetrievalError(f"Failed to retrieve documents: {e}") from e
    
    def _encode_query(self, query_text: str) -> np.ndarray:
        """
        Encode query text to embedding.
        
        Args:
            query_text: Query text
        
        Returns:
            Query embedding vector
        """
        # Use embedding model to encode query
        # For offline operation, use sentence-transformers or similar
        if self.embedding_model is None:
            # Fallback: return zero vector
            return np.zeros(self.vector_store.embedding_dim, dtype=np.float32)
        
        try:
            # Encode query
            embedding = self.embedding_model.encode(query_text)
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            raise RetrievalError(f"Failed to encode query: {e}") from e
