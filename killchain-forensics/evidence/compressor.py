#!/usr/bin/env python3
"""
RansomEye KillChain & Forensics - Evidence Compressor
AUTHORITATIVE: Deterministic compression of evidence artifacts
"""

import gzip
from pathlib import Path


class CompressionError(Exception):
    """Base exception for compression errors."""
    pass


class Compressor:
    """
    Deterministic compression of evidence artifacts.
    
    All compression is deterministic (no randomness).
    Same inputs always produce same outputs.
    """
    
    @staticmethod
    def compress_gzip(input_path: Path, output_path: Path) -> None:
        """
        Compress file using gzip.
        
        Args:
            input_path: Path to input file
            output_path: Path to output compressed file
        
        Raises:
            CompressionError: If compression fails
        """
        if not input_path.exists():
            raise CompressionError(f"Input file not found: {input_path}")
        
        try:
            with open(input_path, 'rb') as f_in:
                with gzip.open(output_path, 'wb') as f_out:
                    f_out.writelines(f_in)
        except Exception as e:
            raise CompressionError(f"Failed to compress {input_path}: {e}") from e
    
    @staticmethod
    def decompress_gzip(input_path: Path, output_path: Path) -> None:
        """
        Decompress gzip file.
        
        Args:
            input_path: Path to input compressed file
            output_path: Path to output decompressed file
        
        Raises:
            CompressionError: If decompression fails
        """
        if not input_path.exists():
            raise CompressionError(f"Input file not found: {input_path}")
        
        try:
            with gzip.open(input_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    f_out.writelines(f_in)
        except Exception as e:
            raise CompressionError(f"Failed to decompress {input_path}: {e}") from e
