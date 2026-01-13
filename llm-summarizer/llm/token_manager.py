#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Token Manager
AUTHORITATIVE: Real token counting using model tokenizer
"""

from typing import Optional, Any


class TokenManagerError(Exception):
    """Base exception for token manager errors."""
    pass


class TokenLimitExceededError(TokenManagerError):
    """Raised when token limit is exceeded."""
    pass


class TokenManager:
    """
    Token counting and limit manager using actual model tokenizer.
    
    Properties:
    - Accurate: Uses actual tokenizer from model
    - Deterministic: Same text always produces same token count
    - Fail-closed: Exceeds limits cause rejection
    """
    
    def __init__(
        self,
        model_instance: Optional[Any] = None,
        max_input_tokens: int = 2048,
        max_output_tokens: int = 1024
    ):
        """
        Initialize token manager.
        
        Args:
            model_instance: Optional model instance (for tokenizer access)
            max_input_tokens: Maximum input tokens allowed
            max_output_tokens: Maximum output tokens allowed
        """
        self.model_instance = model_instance
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using model tokenizer.
        
        Args:
            text: Text to count tokens in
        
        Returns:
            Token count
        
        Raises:
            TokenManagerError: If tokenization fails
        """
        if not isinstance(text, str):
            raise TokenManagerError(f"Text must be string, got {type(text)}")
        
        if self.model_instance is None:
            # Fallback to character-based approximation if no model
            char_count = len(text)
            return (char_count + 3) // 4  # ~4 chars per token approximation
        
        try:
            # Use model's tokenizer to encode text
            # llama-cpp-python provides tokenize() method
            if hasattr(self.model_instance, 'tokenize'):
                tokens = self.model_instance.tokenize(text.encode('utf-8'))
                return len(tokens)
            elif hasattr(self.model_instance, 'tokenizer'):
                # If model has separate tokenizer
                tokens = self.model_instance.tokenizer.encode(text)
                return len(tokens)
            else:
                # Fallback to character-based approximation
                char_count = len(text)
                return (char_count + 3) // 4
        except Exception as e:
            raise TokenManagerError(f"Tokenization failed: {e}") from e
    
    def validate_input_tokens(self, text: str) -> None:
        """
        Validate input token count.
        
        Args:
            text: Input text to validate
        
        Raises:
            TokenLimitExceededError: If token limit exceeded
        """
        token_count = self.count_tokens(text)
        if token_count > self.max_input_tokens:
            raise TokenLimitExceededError(
                f"Input token limit exceeded: {token_count} > {self.max_input_tokens}"
            )
    
    def validate_output_tokens(self, text: str) -> None:
        """
        Validate output token count.
        
        Args:
            text: Output text to validate
        
        Raises:
            TokenLimitExceededError: If token limit exceeded
        """
        token_count = self.count_tokens(text)
        if token_count > self.max_output_tokens:
            raise TokenLimitExceededError(
                f"Output token limit exceeded: {token_count} > {self.max_output_tokens}"
            )
    
    def set_model(self, model_instance: Any) -> None:
        """
        Set model instance for tokenization.
        
        Args:
            model_instance: Model instance with tokenizer
        """
        self.model_instance = model_instance
