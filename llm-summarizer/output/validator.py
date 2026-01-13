#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Output Validator
AUTHORITATIVE: Output schema validation
"""

import json
import jsonschema
from typing import Dict, Any
from pathlib import Path


class OutputValidatorError(Exception):
    """Base exception for output validator errors."""
    pass


class OutputValidationError(OutputValidatorError):
    """Raised when output validation fails."""
    pass


class OutputValidator:
    """
    Output schema validator.
    
    Properties:
    - Strict: Rejects invalid outputs
    - Schema-based: Uses JSON Schema validation
    - Fail-closed: Invalid outputs cause rejection
    """
    
    def __init__(self, schema_path: Path):
        """
        Initialize output validator.
        
        Args:
            schema_path: Path to summary-output.schema.json
        """
        self.schema_path = Path(schema_path)
        self._load_schema()
    
    def _load_schema(self) -> None:
        """Load JSON schema."""
        if not self.schema_path.exists():
            raise OutputValidatorError(f"Schema file not found: {self.schema_path}")
        
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)
    
    def validate(self, output: Dict[str, Any]) -> None:
        """
        Validate output against schema.
        
        Args:
            output: Output dictionary to validate
        
        Raises:
            OutputValidationError: If validation fails
        """
        try:
            jsonschema.validate(instance=output, schema=self.schema)
        except jsonschema.ValidationError as e:
            raise OutputValidationError(f"Output validation failed: {e.message}") from e
        except jsonschema.SchemaError as e:
            raise OutputValidatorError(f"Schema error: {e.message}") from e
        except Exception as e:
            raise OutputValidatorError(f"Unexpected validation error: {e}") from e
