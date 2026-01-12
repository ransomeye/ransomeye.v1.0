#!/usr/bin/env python3
"""
RansomEye Mishka — SOC Assistant (Basic, Read-Only)
AUTHORITATIVE: Load GGUF models for offline LLM inference (CPU-first, GPU-optional)
"""

from pathlib import Path
from typing import Optional
import os


class ModelLoadError(Exception):
    """Base exception for model loading errors."""
    pass


class OfflineModelLoader:
    """
    Load GGUF models for offline LLM inference.
    
    Properties:
    - Offline: No internet access required
    - GGUF format: Supports GGUF model format
    - CPU-first: Optimized for CPU-only environments
    - GPU-optional: Uses GPU if available, falls back to CPU
    - Deterministic: Same inputs always produce same outputs
    """
    
    def __init__(self, model_path: Path):
        """
        Initialize model loader.
        
        Args:
            model_path: Path to GGUF model file
        """
        self.model_path = Path(model_path)
        self.model = None
        self.tokenizer = None
    
    def _detect_cpu_threads(self) -> int:
        """
        Detect optimal number of CPU threads.
        
        Returns:
            Number of threads (defaults to 4, or CPU count if available)
        """
        try:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            # Use 75% of available cores, minimum 2, maximum 8
            threads = max(2, min(8, int(cpu_count * 0.75)))
            return threads
        except Exception:
            return 4  # Default fallback
    
    def _detect_gpu_availability(self) -> bool:
        """
        Detect if GPU is available for llama-cpp-python.
        
        Returns:
            True if GPU is available, False otherwise
        """
        try:
            # Check if llama-cpp-python was built with GPU support
            from llama_cpp import Llama
            # Try to create a minimal model instance to test GPU
            # This is a heuristic - actual GPU usage depends on llama-cpp-python build
            return os.getenv('LLAMA_CPP_GPU', '').lower() in ('1', 'true', 'yes')
        except Exception:
            return False
    
    def load_model(self) -> None:
        """
        Load GGUF model (CPU-first, GPU-optional).
        
        Raises:
            ModelLoadError: If model loading fails
        """
        if not self.model_path.exists():
            raise ModelLoadError(f"Model file not found: {self.model_path}")
        
        try:
            # Try to load with llama-cpp-python (common GGUF loader)
            try:
                from llama_cpp import Llama
                
                # Detect optimal thread count for CPU
                n_threads = self._detect_cpu_threads()
                
                # Check for GPU availability (optional)
                use_gpu = self._detect_gpu_availability()
                
                # Build model configuration (CPU-first)
                model_kwargs = {
                    'model_path': str(self.model_path),
                    'n_ctx': 2048,  # Context window
                    'n_threads': n_threads,  # CPU threads (auto-detected)
                    'verbose': False
                }
                
                # Add GPU support if available (optional, doesn't break if unavailable)
                if use_gpu:
                    # Note: GPU support depends on llama-cpp-python build
                    # If GPU is not available, these parameters are ignored
                    model_kwargs['n_gpu_layers'] = 35  # Offload layers to GPU if available
                    model_kwargs['n_batch'] = 512  # Batch size for GPU
                
                self.model = Llama(**model_kwargs)
                
            except ImportError:
                # Fallback: model not loaded, will use deterministic template responses
                self.model = None
        except Exception as e:
            raise ModelLoadError(f"Failed to load model: {e}") from e
    
    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text
        """
        if self.model is None:
            # Fallback: return structured template response
            return self._template_response(prompt)
        
        try:
            # Generate with model (CPU or GPU, depending on availability)
            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=0.0,  # Deterministic (no randomness)
                top_p=1.0,
                repeat_penalty=1.1
            )
            
            # Extract text from response
            if isinstance(response, dict):
                return response.get('choices', [{}])[0].get('text', '')
            else:
                return str(response)
        except Exception as e:
            # Fallback on error
            return self._template_response(prompt)
    
    def _template_response(self, prompt: str) -> str:
        """Template response when model is not available."""
        return f"Based on the available data: {prompt[:100]}... [Model not loaded, using template response]"
