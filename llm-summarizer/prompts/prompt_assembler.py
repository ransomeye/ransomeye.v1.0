#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Prompt Assembler
AUTHORITATIVE: Deterministic prompt assembly from templates and facts
"""

from typing import Dict, Any
from jinja2 import Template, TemplateError

from .template_registry import TemplateRegistry, TemplateRegistryError
from .prompt_hasher import PromptHasher


class PromptAssemblerError(Exception):
    """Base exception for prompt assembler errors."""
    pass


class PromptAssembler:
    """
    Deterministic prompt assembler.
    
    Properties:
    - Deterministic: Same template + facts = same prompt
    - Template-based: Uses Jinja2 templates
    - Hash-logged: Prompt hash is calculated and logged
    """
    
    def __init__(self, template_registry: TemplateRegistry):
        """
        Initialize prompt assembler.
        
        Args:
            template_registry: Template registry instance
        """
        self.template_registry = template_registry
    
    def assemble_prompt(
        self,
        template_id: str,
        template_version: str,
        input_facts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assemble prompt from template and input facts.
        
        Process:
        1. Get template from registry
        2. Verify template hash
        3. Render template with input facts
        4. Calculate prompt hash
        5. Return assembled prompt and metadata
        
        Args:
            template_id: Template identifier
            template_version: Template version
            input_facts: Input facts dictionary (redacted)
        
        Returns:
            Dictionary with:
            - prompt: Assembled prompt string
            - prompt_hash: SHA256 hash of prompt
            - template_id: Template identifier
            - template_version: Template version
            - template_hash: Template hash
        
        Raises:
            PromptAssemblerError: If assembly fails
        """
        # Get template
        try:
            template_record = self.template_registry.get_template(template_id, template_version)
        except TemplateRegistryError as e:
            raise PromptAssemblerError(f"Failed to get template: {e}") from e
        
        # Render template
        try:
            jinja_template = Template(template_record['template_content'])
            prompt = jinja_template.render(**input_facts)
        except TemplateError as e:
            raise PromptAssemblerError(f"Template rendering failed: {e}") from e
        except Exception as e:
            raise PromptAssemblerError(f"Unexpected error during template rendering: {e}") from e
        
        # Calculate prompt hash
        prompt_hash = PromptHasher.hash_assembled_prompt(prompt)
        
        return {
            'prompt': prompt,
            'prompt_hash': prompt_hash,
            'template_id': template_record['template_id'],
            'template_version': template_record['template_version'],
            'template_hash': template_record['template_hash']
        }
