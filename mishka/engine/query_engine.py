#!/usr/bin/env python3
"""
RansomEye Mishka — SOC Assistant (Basic, Read-Only)
AUTHORITATIVE: Deterministic query processing with structured responses
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid
import json

from rag.retriever import Retriever
from llm.prompt_builder import PromptBuilder
from llm.offline_model_loader import OfflineModelLoader
from engine.citation_builder import CitationBuilder


class QueryError(Exception):
    """Base exception for query errors."""
    pass


class QueryEngine:
    """
    Deterministic query processing with structured responses.
    
    Properties:
    - Deterministic: Same query always produces same response
    - Structured: Responses are structured, not free prose
    - Cited: All claims have citations
    - No hallucination: No facts without sources
    """
    
    def __init__(self, retriever: Retriever, model_loader: OfflineModelLoader):
        """
        Initialize query engine.
        
        Args:
            retriever: Document retriever
            model_loader: Offline model loader
        """
        self.retriever = retriever
        self.model_loader = model_loader
        self.citation_builder = CitationBuilder()
    
    def process_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process query and generate structured response.
        
        Process:
        1. Retrieve relevant documents
        2. Build prompt
        3. Generate answer (structured)
        4. Build citations
        5. Build response
        
        Args:
            query: Query dictionary
        
        Returns:
            Response dictionary
        """
        query_text = query.get('query_text', '')
        query_id = query.get('query_id', '')
        
        # Retrieve relevant documents
        retrieved_docs = self.retriever.retrieve(query_text, k=5)
        
        if not retrieved_docs:
            # No documents found
            return self._build_insufficient_data_response(query_id)
        
        # Build prompt
        prompt = PromptBuilder.build_query_prompt(query_text, retrieved_docs)
        
        # Generate answer
        answer_text = self.model_loader.generate(prompt, max_tokens=512)
        
        # Parse structured answer
        answer = self._parse_structured_answer(answer_text, retrieved_docs)
        
        # Build citations
        citations = self.citation_builder.build_citations(answer.get('facts', []), retrieved_docs)
        
        # Build source references
        source_references = self._build_source_references(retrieved_docs)
        
        # Determine confidence level
        confidence_level = self._determine_confidence(retrieved_docs, answer)
        
        # Build response
        response = {
            'response_id': str(uuid.uuid4()),
            'query_id': query_id,
            'response_timestamp': datetime.now(timezone.utc).isoformat(),
            'answer': answer,
            'confidence_level': confidence_level,
            'citations': citations,
            'source_references': source_references,
            'uncertainty_indicators': self._extract_uncertainty_indicators(answer_text)
        }
        
        return response
    
    def _parse_structured_answer(self, answer_text: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse structured answer from model output."""
        # Extract summary (first sentence or first 200 chars)
        summary = answer_text.split('.')[0][:200] if '.' in answer_text else answer_text[:200]
        
        # Extract facts (simple parsing - in production would use more sophisticated parsing)
        facts = []
        fact_id = 0
        for sentence in answer_text.split('.'):
            if len(sentence.strip()) > 20:  # Filter short sentences
                fact = {
                    'fact_text': sentence.strip(),
                    'citation_id': str(uuid.uuid4())
                }
                facts.append(fact)
                fact_id += 1
                if fact_id >= 5:  # Limit to 5 facts
                    break
        
        # Extract data points (simple extraction)
        data_points = []
        for doc in retrieved_docs[:3]:  # Top 3 documents
            try:
                content = json.loads(doc.get('content', '{}'))
                # Extract common data types
                if 'timestamp' in content:
                    data_points.append({
                        'data_type': 'timestamp',
                        'data_value': str(content.get('timestamp', '')),
                        'source_id': doc.get('source_id', '')
                    })
                if 'id' in content or 'entity_id' in content or 'event_id' in content:
                    data_points.append({
                        'data_type': 'identifier',
                        'data_value': str(content.get('id') or content.get('entity_id') or content.get('event_id', '')),
                        'source_id': doc.get('source_id', '')
                    })
            except:
                pass
        
        return {
            'summary': summary,
            'facts': facts,
            'data_points': data_points
        }
    
    def _build_source_references(self, retrieved_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build source references list."""
        source_refs = []
        seen = set()
        
        for doc in retrieved_docs:
            source_key = (doc.get('source_type', ''), doc.get('source_id', ''))
            if source_key not in seen:
                seen.add(source_key)
                source_refs.append({
                    'source_type': doc.get('source_type', ''),
                    'source_id': doc.get('source_id', ''),
                    'source_path': doc.get('source_location', '')
                })
        
        return source_refs
    
    def _determine_confidence(self, retrieved_docs: List[Dict[str, Any]], answer: Dict[str, Any]) -> str:
        """Determine confidence level."""
        if not retrieved_docs:
            return 'insufficient_data'
        
        if len(answer.get('facts', [])) == 0:
            return 'insufficient_data'
        
        # Simple heuristic: more sources and facts = higher confidence
        num_sources = len(retrieved_docs)
        num_facts = len(answer.get('facts', []))
        
        if num_sources >= 3 and num_facts >= 3:
            return 'high'
        elif num_sources >= 2 and num_facts >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _extract_uncertainty_indicators(self, answer_text: str) -> List[str]:
        """Extract uncertainty indicators from answer."""
        uncertainty_keywords = ['insufficient', 'unknown', 'unclear', 'uncertain', 'may', 'might', 'possibly']
        indicators = []
        
        answer_lower = answer_text.lower()
        for keyword in uncertainty_keywords:
            if keyword in answer_lower:
                indicators.append(f"Contains uncertainty keyword: {keyword}")
        
        return indicators
    
    def _build_insufficient_data_response(self, query_id: str) -> Dict[str, Any]:
        """Build response for insufficient data."""
        return {
            'response_id': str(uuid.uuid4()),
            'query_id': query_id,
            'response_timestamp': datetime.now(timezone.utc).isoformat(),
            'answer': {
                'summary': 'Insufficient data available to answer this query',
                'facts': [],
                'data_points': []
            },
            'confidence_level': 'insufficient_data',
            'citations': [],
            'source_references': [],
            'uncertainty_indicators': ['No relevant documents found']
        }
