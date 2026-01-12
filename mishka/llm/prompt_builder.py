#!/usr/bin/env python3
"""
RansomEye Mishka — SOC Assistant (Basic, Read-Only)
AUTHORITATIVE: Build structured prompts for offline LLM
"""

from typing import List, Dict, Any


class PromptBuilder:
    """
    Build structured prompts for offline LLM.
    
    Properties:
    - Structured: Prompts are structured, not free-form
    - Deterministic: Same inputs always produce same prompt
    - No decision language: Prompts avoid decision-making language
    """
    
    @staticmethod
    def build_query_prompt(query_text: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Build prompt for query answering.
        
        Args:
            query_text: Query text
            retrieved_docs: Retrieved documents
        
        Returns:
            Structured prompt
        """
        # Build context from retrieved documents
        context_parts = []
        for i, doc in enumerate(retrieved_docs[:5], 1):  # Limit to top 5
            source_type = doc.get('source_type', 'unknown')
            content = doc.get('content', '')[:500]  # Truncate long content
            context_parts.append(f"Source {i} ({source_type}): {content}")
        
        context = "\n\n".join(context_parts)
        
        # Build structured prompt
        prompt = f"""You are a SOC analyst assistant. Answer the following query using ONLY the provided sources.

Query: {query_text}

Available Sources:
{context}

Instructions:
1. Answer using ONLY information from the provided sources
2. Cite every claim with source references
3. If information is insufficient, explicitly state "insufficient data"
4. Use structured format: summary, facts, data points
5. Do NOT make recommendations phrased as commands
6. Do NOT use decision-making language
7. Indicate confidence level: high, medium, low, or insufficient_data

Provide your answer in structured format."""
        
        return prompt
    
    @staticmethod
    def build_citation_prompt(fact: str, sources: List[Dict[str, Any]]) -> str:
        """
        Build prompt for citation extraction.
        
        Args:
            fact: Fact to cite
            sources: Available sources
        
        Returns:
            Structured prompt for citation
        """
        sources_text = "\n".join([
            f"Source {i+1} ({s.get('source_type', 'unknown')}): {s.get('source_id', '')}"
            for i, s in enumerate(sources)
        ])
        
        prompt = f"""Extract citation for the following fact from the available sources.

Fact: {fact}

Available Sources:
{sources_text}

Provide citation in format: source_type, source_id, source_location, excerpt"""
        
        return prompt
