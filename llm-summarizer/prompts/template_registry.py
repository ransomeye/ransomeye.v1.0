#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Template Registry
AUTHORITATIVE: Immutable prompt template registration and retrieval
"""

import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

from .prompt_hasher import PromptHasher, PromptHasherError


class TemplateRegistryError(Exception):
    """Base exception for template registry errors."""
    pass


class TemplateNotFoundError(TemplateRegistryError):
    """Raised when template is not found."""
    pass


class TemplateHashMismatchError(TemplateRegistryError):
    """Raised when template hash does not match."""
    pass


class TemplateRegistry:
    """
    Immutable prompt template registry.
    
    Properties:
    - Immutable: Templates cannot be modified after registration
    - Versioned: Templates are versioned (semver)
    - Hash-verified: Template hashes are verified on retrieval
    - Fail-closed: Hash mismatches cause rejection
    """
    
    def __init__(self, registry_store_path: Path):
        """
        Initialize template registry.
        
        Args:
            registry_store_path: Path to registry store file (JSONL)
        """
        self.registry_store_path = Path(registry_store_path)
        self.registry_store_path.parent.mkdir(parents=True, exist_ok=True)
        self._templates = {}  # template_id -> template record
    
    def register_template(
        self,
        template_content: str,
        template_version: str,
        narrative_type: str,
        registered_by: str
    ) -> Dict[str, Any]:
        """
        Register a new prompt template.
        
        Process:
        1. Validate template version (semver)
        2. Calculate template hash
        3. Create template record
        4. Store template (append-only)
        5. Return template record
        
        Args:
            template_content: Jinja2 template content
            template_version: Template version (semver)
            narrative_type: Narrative type (SOC_NARRATIVE | EXECUTIVE_SUMMARY | LEGAL_NARRATIVE)
            registered_by: Entity registering template
        
        Returns:
            Template record dictionary
        
        Raises:
            TemplateRegistryError: If registration fails
        """
        # Validate narrative type
        valid_narrative_types = ['SOC_NARRATIVE', 'EXECUTIVE_SUMMARY', 'LEGAL_NARRATIVE']
        if narrative_type not in valid_narrative_types:
            raise TemplateRegistryError(f"Invalid narrative type: {narrative_type}")
        
        # Validate semver
        import re
        semver_pattern = re.compile(r'^\d+\.\d+\.\d+$')
        if not semver_pattern.match(template_version):
            raise TemplateRegistryError(f"Invalid template version: {template_version}. Must be semver (e.g., 1.0.0)")
        
        # Calculate template hash
        template_hash = PromptHasher.hash_template(template_content)
        
        # Create template record
        template_id = str(uuid.uuid4())
        registered_at = datetime.now(timezone.utc).isoformat()
        
        template_record = {
            'template_id': template_id,
            'template_version': template_version,
            'narrative_type': narrative_type,
            'template_content': template_content,
            'template_hash': template_hash,
            'registered_at': registered_at,
            'registered_by': registered_by
        }
        
        # Store template (append-only)
        self._store_template(template_record)
        
        # Cache in memory
        self._templates[template_id] = template_record
        
        return template_record
    
    def get_template(
        self,
        template_id: str,
        template_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get template by ID and version.
        
        Process:
        1. Load template from store if not cached
        2. Verify template hash matches stored hash
        3. Return template record
        
        Args:
            template_id: Template identifier
            template_version: Optional template version (if None, get latest)
        
        Returns:
            Template record dictionary
        
        Raises:
            TemplateNotFoundError: If template not found
            TemplateHashMismatchError: If template hash mismatch
        """
        # Load from store if not cached
        if template_id not in self._templates:
            self._load_templates()
        
        # Find template
        if template_id not in self._templates:
            raise TemplateNotFoundError(f"Template not found: {template_id}")
        
        template_record = self._templates[template_id]
        
        # Version check
        if template_version and template_record['template_version'] != template_version:
            raise TemplateNotFoundError(
                f"Template version mismatch: requested {template_version}, "
                f"found {template_record['template_version']}"
            )
        
        # Verify template hash
        stored_hash = template_record.get('template_hash')
        calculated_hash = PromptHasher.hash_template(template_record['template_content'])
        
        if stored_hash != calculated_hash:
            raise TemplateHashMismatchError(
                f"Template hash mismatch for {template_id}: "
                f"stored={stored_hash}, calculated={calculated_hash}"
            )
        
        return template_record
    
    def find_template_by_narrative_type(
        self,
        narrative_type: str,
        template_version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find template by narrative type.
        
        Args:
            narrative_type: Narrative type
            template_version: Optional template version
        
        Returns:
            Template record dictionary or None if not found
        """
        # Load from store if not cached
        if not self._templates:
            self._load_templates()
        
        # Find matching template
        for template_id, template_record in self._templates.items():
            if template_record['narrative_type'] == narrative_type:
                if template_version is None or template_record['template_version'] == template_version:
                    return template_record
        
        return None
    
    def _store_template(self, template_record: Dict[str, Any]) -> None:
        """Store template record (append-only)."""
        with open(self.registry_store_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(template_record, separators=(',', ':')) + '\n')
    
    def _load_templates(self) -> None:
        """Load templates from store."""
        if not self.registry_store_path.exists():
            return
        
        self._templates = {}
        with open(self.registry_store_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                template_record = json.loads(line)
                template_id = template_record['template_id']
                self._templates[template_id] = template_record
