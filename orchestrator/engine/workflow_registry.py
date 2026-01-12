#!/usr/bin/env python3
"""
RansomEye Orchestrator - Workflow Registry
AUTHORITATIVE: Immutable workflow storage and retrieval
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import uuid


class WorkflowRegistryError(Exception):
    """Base exception for workflow registry errors."""
    pass


class WorkflowRegistry:
    """
    Immutable workflow registry.
    
    Properties:
    - Immutable: Workflows cannot be modified after registration
    - Versioned: Workflows are versioned (semver)
    - Deterministic: Same workflow_id + version = same workflow
    """
    
    def __init__(self, workflows_store_path: Path):
        """
        Initialize workflow registry.
        
        Args:
            workflows_store_path: Path to workflows store
        """
        self.workflows_store_path = Path(workflows_store_path)
        self.workflows_store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def register_workflow(self, workflow: Dict[str, Any]) -> None:
        """
        Register workflow.
        
        Args:
            workflow: Workflow dictionary
        """
        # Validate workflow has all required fields
        required_fields = [
            'workflow_id', 'version', 'allowed_triggers', 'required_authority',
            'required_explanation_type', 'steps', 'failure_policy'
        ]
        for field in required_fields:
            if field not in workflow:
                raise WorkflowRegistryError(f"Missing required field: {field}")
        
        # Validate steps
        if not workflow.get('steps'):
            raise WorkflowRegistryError("Workflow must have at least one step")
        
        # Store workflow
        self._store_workflow(workflow)
    
    def get_workflow(self, workflow_id: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get workflow by ID and optional version.
        
        Args:
            workflow_id: Workflow identifier
            version: Optional version (if None, returns latest)
        
        Returns:
            Workflow dictionary, or None if not found
        """
        workflows = self._load_all_workflows()
        
        # Filter by workflow_id
        matching = [w for w in workflows if w.get('workflow_id') == workflow_id]
        
        if not matching:
            return None
        
        if version:
            # Return specific version
            for w in matching:
                if w.get('version') == version:
                    return w
            return None
        else:
            # Return latest version (highest semver)
            return self._get_latest_version(matching)
    
    def _get_latest_version(self, workflows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get latest version from workflows list."""
        if len(workflows) == 1:
            return workflows[0]
        
        # Sort by version (semver)
        def version_key(w):
            version = w.get('version', '0.0.0')
            parts = version.split('.')
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        
        return max(workflows, key=version_key)
    
    def _load_all_workflows(self) -> List[Dict[str, Any]]:
        """Load all workflows from store."""
        workflows = []
        
        if not self.workflows_store_path.exists():
            return workflows
        
        try:
            with open(self.workflows_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    workflows.append(json.loads(line))
        except Exception:
            pass
        
        return workflows
    
    def _store_workflow(self, workflow: Dict[str, Any]) -> None:
        """Store workflow to file-based store."""
        try:
            workflow_json = json.dumps(workflow, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.workflows_store_path, 'a', encoding='utf-8') as f:
                f.write(workflow_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise WorkflowRegistryError(f"Failed to store workflow: {e}") from e
