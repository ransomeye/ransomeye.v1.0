#!/usr/bin/env python3
"""
RansomEye Mishka — SOC Assistant (Basic, Read-Only)
AUTHORITATIVE: Single API for Mishka queries with feedback storage
"""

import sys
from pathlib import Path
from typing import Dict, Any
import uuid
from datetime import datetime, timezone
import json

# Add parent directory to path
_mishka_dir = Path(__file__).parent.parent
if str(_mishka_dir) not in sys.path:
    sys.path.insert(0, str(_mishka_dir))

from engine.query_engine import QueryEngine
from rag.retriever import Retriever
from rag.vector_store import VectorStore
from llm.offline_model_loader import OfflineModelLoader


class MishkaAPIError(Exception):
    """Base exception for Mishka API errors."""
    pass


class MishkaAPI:
    """
    Single API for Mishka queries.
    
    All operations:
    - Process queries (deterministic, structured)
    - Store feedback (does NOT alter models)
    - Bundle feedback for retraining
    """
    
    def __init__(
        self,
        vector_store_path: Path,
        model_path: Path,
        feedback_store_path: Path,
        embedding_model=None
    ):
        """
        Initialize Mishka API.
        
        Args:
            vector_store_path: Path to FAISS vector store
            model_path: Path to GGUF model file
            feedback_store_path: Path to feedback store
            embedding_model: Embedding model for retrieval (optional)
        """
        # Initialize vector store
        self.vector_store = VectorStore(vector_store_path, embedding_dim=384)
        
        # Initialize model loader
        self.model_loader = OfflineModelLoader(model_path)
        try:
            self.model_loader.load_model()
        except Exception:
            # Model loading failed, will use template responses
            pass
        
        # Initialize retriever
        self.retriever = Retriever(self.vector_store, embedding_model)
        
        # Initialize query engine
        self.query_engine = QueryEngine(self.retriever, self.model_loader)
        
        # Initialize feedback store
        self.feedback_store_path = Path(feedback_store_path)
        self.feedback_store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def ask(self, query_text: str, query_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process query and return structured response.
        
        Args:
            query_text: Query text
            query_context: Query context (incident ID, etc.)
        
        Returns:
            Response dictionary
        """
        # Build query
        query = {
            'query_id': str(uuid.uuid4()),
            'query_text': query_text,
            'query_timestamp': datetime.now(timezone.utc).isoformat(),
            'query_context': query_context or {}
        }
        
        # Process query
        response = self.query_engine.process_query(query)
        
        return response
    
    def store_feedback(
        self,
        response_id: str,
        query_id: str,
        analyst_identifier: str,
        feedback_type: str,
        feedback_content: str
    ) -> Dict[str, Any]:
        """
        Store analyst feedback.
        
        Feedback does NOT alter models, only bundled for later retraining.
        
        Args:
            response_id: Response identifier
            query_id: Query identifier
            analyst_identifier: Analyst identifier
            feedback_type: Type of feedback
            feedback_content: Feedback content
        
        Returns:
            Feedback dictionary
        """
        feedback = {
            'feedback_id': str(uuid.uuid4()),
            'response_id': response_id,
            'query_id': query_id,
            'feedback_timestamp': datetime.now(timezone.utc).isoformat(),
            'analyst_identifier': analyst_identifier,
            'feedback_type': feedback_type,
            'feedback_content': feedback_content,
            'bundled_for_retraining': True
        }
        
        # Store feedback
        try:
            feedback_json = json.dumps(feedback, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.feedback_store_path, 'a', encoding='utf-8') as f:
                f.write(feedback_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise MishkaAPIError(f"Failed to store feedback: {e}") from e
        
        return feedback
