#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Prompt Hasher
AUTHORITATIVE: Deterministic prompt hash calculation
"""

import hashlib
from typing import Dict, Any


class PromptHasherError(Exception):
    """Base exception for prompt hasher errors."""
    pass


class PromptHasher:
    """
    Deterministic prompt hash calculator.
    
    Properties:
    - Deterministic: Same prompt always produces same hash
    - SHA256: Uses SHA256 for hashing
    """
    
    @staticmethod
    def hash_template(template_content: str) -> str:
        """
        Calculate SHA256 hash of template content.
        
        Args:
            template_content: Template content string
        
        Returns:
            SHA256 hash (64 hex characters)
        
        Raises:
            PromptHasherError: If hashing fails
        """
        if not isinstance(template_content, str):
            raise PromptHasherError(f"Template content must be string, got {type(template_content)}")
        
        hash_obj = hashlib.sha256(template_content.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @staticmethod
    def hash_assembled_prompt(prompt: str) -> str:
        """
        Calculate SHA256 hash of assembled prompt.
        
        Args:
            prompt: Assembled prompt string
        
        Returns:
            SHA256 hash (64 hex characters)
        
        Raises:
            PromptHasherError: If hashing fails
        """
        if not isinstance(prompt, str):
            raise PromptHasherError(f"Prompt must be string, got {type(prompt)}")
        
        hash_obj = hashlib.sha256(prompt.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @staticmethod
    def hash_input_facts(input_facts: Dict[str, Any]) -> str:
        """
        Calculate SHA256 hash of input facts (for audit).
        
        Args:
            input_facts: Input facts dictionary
        
        Returns:
            SHA256 hash (64 hex characters)
        
        Raises:
            PromptHasherError: If hashing fails
        """
        import json
        if not isinstance(input_facts, dict):
            raise PromptHasherError(f"Input facts must be dict, got {type(input_facts)}")
        
        # Deterministic JSON serialization
        json_str = json.dumps(input_facts, sort_keys=True, separators=(',', ':'))
        hash_obj = hashlib.sha256(json_str.encode('utf-8'))
        return hash_obj.hexdigest()
