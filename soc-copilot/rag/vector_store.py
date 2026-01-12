#!/usr/bin/env python3
"""
RansomEye SOC Copilot - Vector Store (FAISS)
AUTHORITATIVE: FAISS-backed vector store for document embeddings
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np


class VectorStoreError(Exception):
    """Base exception for vector store errors."""
    pass


class VectorStore:
    """
    FAISS-backed vector store for document embeddings.
    
    Properties:
    - Offline: No internet access required
    - Deterministic: Same documents always produce same embeddings
    - Immutable: Documents cannot be modified after indexing
    """
    
    def __init__(self, store_path: Path, embedding_dim: int = 384):
        """
        Initialize vector store.
        
        Args:
            store_path: Path to FAISS index file
            embedding_dim: Dimension of embeddings (default: 384 for sentence-transformers)
        """
        self.store_path = Path(store_path)
        self.embedding_dim = embedding_dim
        self.index = None
        self.documents = []
        self._load_or_create_index()
    
    def _load_or_create_index(self) -> None:
        """Load existing FAISS index or create new one."""
        try:
            import faiss
            
            if self.store_path.exists():
                # Load existing index
                self.index = faiss.read_index(str(self.store_path))
                # Load document metadata
                metadata_path = self.store_path.parent / f"{self.store_path.stem}_metadata.jsonl"
                if metadata_path.exists():
                    import json
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                self.documents.append(json.loads(line))
            else:
                # Create new index
                self.index = faiss.IndexFlatL2(self.embedding_dim)
        except ImportError:
            # FAISS not available, use in-memory fallback
            self.index = None
            self.documents = []
    
    def add_documents(self, documents: List[Dict[str, Any]], embeddings: np.ndarray) -> None:
        """
        Add documents to vector store.
        
        Args:
            documents: List of document dictionaries
            embeddings: NumPy array of embeddings (shape: [num_docs, embedding_dim])
        """
        if self.index is None:
            # Fallback: store documents only (no vector search)
            self.documents.extend(documents)
            return
        
        try:
            import faiss
            
            # Ensure embeddings are float32
            embeddings = embeddings.astype('float32')
            
            # Add to FAISS index
            self.index.add(embeddings)
            
            # Store document metadata
            self.documents.extend(documents)
            
            # Save index
            self._save_index()
        except Exception as e:
            raise VectorStoreError(f"Failed to add documents: {e}") from e
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
        
        Returns:
            List of document dictionaries with similarity scores
        """
        if self.index is None or len(self.documents) == 0:
            return []
        
        try:
            import faiss
            
            # Ensure query embedding is float32
            query_embedding = query_embedding.astype('float32').reshape(1, -1)
            
            # Search FAISS index
            distances, indices = self.index.search(query_embedding, min(k, len(self.documents)))
            
            # Build results
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx].copy()
                    doc['similarity_score'] = float(1.0 / (1.0 + distances[0][i]))  # Convert distance to similarity
                    results.append(doc)
            
            return results
        except Exception as e:
            raise VectorStoreError(f"Failed to search: {e}") from e
    
    def _save_index(self) -> None:
        """Save FAISS index to disk."""
        if self.index is None:
            return
        
        try:
            import faiss
            import json
            
            # Save FAISS index
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self.store_path))
            
            # Save document metadata
            metadata_path = self.store_path.parent / f"{self.store_path.stem}_metadata.jsonl"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                for doc in self.documents:
                    f.write(json.dumps(doc, sort_keys=True, ensure_ascii=False))
                    f.write('\n')
        except Exception as e:
            raise VectorStoreError(f"Failed to save index: {e}") from e
