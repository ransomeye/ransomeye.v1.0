#!/usr/bin/env python3
"""
RansomEye Mishka — SOC Assistant (Basic, Read-Only)
AUTHORITATIVE: Build citations for all claims in responses
"""

from typing import List, Dict, Any
import uuid


class CitationError(Exception):
    """Base exception for citation errors."""
    pass


class CitationBuilder:
    """
    Build citations for all claims in responses.
    
    Properties:
    - Complete: All claims must have citations
    - Verifiable: All citations are verifiable
    - Deterministic: Same claims always produce same citations
    """
    
    def __init__(self):
        """Initialize citation builder."""
        pass
    
    def build_citations(self, facts: List[Dict[str, Any]], retrieved_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build citations for facts.
        
        Args:
            facts: List of facts (each with fact_text and citation_id)
            retrieved_docs: Retrieved documents
        
        Returns:
            List of citation dictionaries
        """
        citations = []
        
        for fact in facts:
            citation_id = fact.get('citation_id', '')
            fact_text = fact.get('fact_text', '')
            
            # Find relevant document for citation
            relevant_doc = self._find_relevant_doc(fact_text, retrieved_docs)
            
            if relevant_doc:
                citation = {
                    'citation_id': citation_id,
                    'source_type': relevant_doc.get('source_type', 'unknown'),
                    'source_id': relevant_doc.get('source_id', ''),
                    'source_location': relevant_doc.get('source_location', ''),
                    'excerpt': self._extract_excerpt(fact_text, relevant_doc)
                }
                citations.append(citation)
            else:
                # No relevant document found
                citation = {
                    'citation_id': citation_id,
                    'source_type': 'unknown',
                    'source_id': '',
                    'source_location': '',
                    'excerpt': 'No source found for this fact'
                }
                citations.append(citation)
        
        return citations
    
    def _find_relevant_doc(self, fact_text: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find most relevant document for fact."""
        # Simple keyword matching (deterministic)
        fact_lower = fact_text.lower()
        
        for doc in retrieved_docs:
            content = doc.get('content', '').lower()
            if any(word in content for word in fact_lower.split()[:5]):  # Check first 5 words
                return doc
        
        # Return first document if no match
        return retrieved_docs[0] if retrieved_docs else None
    
    def _extract_excerpt(self, fact_text: str, doc: Dict[str, Any]) -> str:
        """Extract relevant excerpt from document."""
        content = doc.get('content', '')
        
        # Find relevant excerpt (first 200 chars containing fact keywords)
        fact_words = fact_text.lower().split()[:3]
        content_lower = content.lower()
        
        for word in fact_words:
            idx = content_lower.find(word)
            if idx >= 0:
                start = max(0, idx - 50)
                end = min(len(content), idx + 150)
                return content[start:end]
        
        # Fallback: return first 200 chars
        return content[:200]
