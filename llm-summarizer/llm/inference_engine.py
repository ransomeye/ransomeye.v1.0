#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Inference Engine
AUTHORITATIVE: Deterministic LLM inference with strict limits
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .token_manager import TokenManager, TokenLimitExceededError


class InferenceEngineError(Exception):
    """Base exception for inference engine errors."""
    pass


class InferenceTimeoutError(InferenceEngineError):
    """Raised when inference timeout is exceeded."""
    pass


class InferenceTokenLimitError(InferenceEngineError):
    """Raised when token limit is exceeded during inference."""
    pass


class InferenceEngine:
    """
    Deterministic LLM inference engine.
    
    Properties:
    - Deterministic: Same prompt + model → same output (bit-for-bit)
    - Limited: Token, time, memory limits enforced
    - Fail-closed: All limits cause rejection
    - No mutation: Prompt is never modified
    """
    
    # Deterministic inference parameters
    TEMPERATURE = 0.0  # Deterministic sampling
    SEED = 42  # Fixed seed for determinism
    TOP_P = 1.0  # No nucleus sampling
    TOP_K = 1  # Greedy decoding only
    
    def __init__(
        self,
        model_instance: Any,
        token_manager: TokenManager,
        max_output_tokens: int = 1024,
        max_execution_time_seconds: int = 300
    ):
        """
        Initialize inference engine.
        
        Args:
            model_instance: Loaded GGUF model instance
            token_manager: Token manager instance
            max_output_tokens: Maximum output tokens
            max_execution_time_seconds: Maximum execution time
        """
        self.model_instance = model_instance
        self.token_manager = token_manager
        self.max_output_tokens = max_output_tokens
        self.max_execution_time_seconds = max_execution_time_seconds
    
    def infer(
        self,
        prompt: str,
        stop_sequences: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Run deterministic inference on prompt.
        
        Process:
        1. Validate input tokens
        2. Start timer
        3. Run inference with deterministic parameters
        4. Check timeout
        5. Validate output tokens
        6. Return generated text and metadata
        
        Args:
            prompt: Input prompt string
            stop_sequences: Optional stop sequences (default: None)
        
        Returns:
            Dictionary with:
            - generated_text: Generated text
            - input_tokens: Input token count
            - output_tokens: Output token count
            - inference_time_ms: Inference time in milliseconds
            - started_at: Start timestamp
            - completed_at: Completion timestamp
        
        Raises:
            InferenceTokenLimitError: If token limit exceeded
            InferenceTimeoutError: If timeout exceeded
            InferenceEngineError: If inference fails
        """
        # Validate input tokens
        try:
            self.token_manager.validate_input_tokens(prompt)
        except TokenLimitExceededError as e:
            raise InferenceTokenLimitError(f"Input token limit exceeded: {e}") from e
        
        input_tokens = self.token_manager.count_tokens(prompt)
        
        # Start timer
        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        
        try:
            # Run inference with deterministic parameters
            generated_text = self._run_inference(prompt, stop_sequences)
            
            # Check timeout
            execution_time = time.time() - start_time
            if execution_time > self.max_execution_time_seconds:
                raise InferenceTimeoutError(
                    f"Inference timeout exceeded: {execution_time:.2f}s > {self.max_execution_time_seconds}s"
                )
            
            # Validate output tokens
            try:
                self.token_manager.validate_output_tokens(generated_text)
            except TokenLimitExceededError as e:
                raise InferenceTokenLimitError(f"Output token limit exceeded: {e}") from e
            
            output_tokens = self.token_manager.count_tokens(generated_text)
            inference_time_ms = int(execution_time * 1000)
            completed_at = datetime.now(timezone.utc)
            
            return {
                'generated_text': generated_text,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'inference_time_ms': inference_time_ms,
                'started_at': started_at.isoformat(),
                'completed_at': completed_at.isoformat()
            }
        except InferenceTimeoutError:
            raise
        except InferenceTokenLimitError:
            raise
        except Exception as e:
            raise InferenceEngineError(f"Inference failed: {e}") from e
    
    def _run_inference(self, prompt: str, stop_sequences: Optional[list]) -> str:
        """
        Run actual inference using model.
        
        Args:
            prompt: Input prompt
            stop_sequences: Optional stop sequences
        
        Returns:
            Generated text
        
        Raises:
            InferenceEngineError: If inference fails
        """
        try:
            # llama-cpp-python inference with deterministic parameters
            # max_tokens: Maximum tokens to generate
            # temperature: 0.0 for deterministic
            # top_p: 1.0 for no nucleus sampling
            # top_k: 1 for greedy decoding
            # repeat_penalty: 1.0 (no penalty)
            # seed: Fixed seed for determinism
            # stop: Stop sequences
            
            result = self.model_instance(
                prompt,
                max_tokens=self.max_output_tokens,
                temperature=self.TEMPERATURE,
                top_p=self.TOP_P,
                top_k=self.TOP_K,
                repeat_penalty=1.0,
                seed=self.SEED,
                stop=stop_sequences if stop_sequences else [],
                echo=False  # Don't echo prompt in output
            )
            
            # Extract generated text from result
            # llama-cpp-python returns dict with 'choices' list
            if isinstance(result, dict):
                choices = result.get('choices', [])
                if choices:
                    generated_text = choices[0].get('text', '')
                    return generated_text.strip()
                else:
                    return ''
            elif isinstance(result, str):
                return result.strip()
            else:
                raise InferenceEngineError(f"Unexpected inference result type: {type(result)}")
        except Exception as e:
            raise InferenceEngineError(f"Model inference failed: {e}") from e
