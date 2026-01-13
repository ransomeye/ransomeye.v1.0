#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Blast Radius Control
AUTHORITATIVE: Blast radius declaration and enforcement (NO ASSUMPTIONS)
Python 3.10+ only
"""

import os
import sys
from typing import Dict, Any, Optional, List
from enum import Enum
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _common_available = True
    _logger = setup_logging('tre-blast-radius')
except ImportError:
    _common_available = False
    _logger = None


class BlastScope(Enum):
    """Blast scope enumeration (FROZEN)."""
    HOST = 'HOST'
    GROUP = 'GROUP'
    NETWORK = 'NETWORK'
    GLOBAL = 'GLOBAL'


class ExpectedImpact(Enum):
    """Expected impact enumeration (FROZEN)."""
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


class BlastRadiusError(Exception):
    """Exception raised when blast radius validation fails."""
    pass


class BlastRadiusResolver:
    """
    Resolves blast radius from action and target.
    
    CRITICAL: Target count must match resolved targets.
    Mismatch = REJECT.
    """
    
    def resolve_targets(
        self,
        action_type: str,
        target: Dict[str, Any],
        blast_scope: BlastScope
    ) -> List[str]:
        """
        Resolve target list from action and target.
        
        Args:
            action_type: Action type
            target: Target object
            blast_scope: Blast scope
        
        Returns:
            List of resolved target identifiers
        """
        if blast_scope == BlastScope.HOST:
            # Single host target
            machine_id = target.get('machine_id')
            if not machine_id:
                raise BlastRadiusError("Missing machine_id for HOST scope")
            return [machine_id]
        
        elif blast_scope == BlastScope.GROUP:
            # Group targets
            group_id = target.get('group_id')
            if not group_id:
                raise BlastRadiusError("Missing group_id for GROUP scope")
            # Resolve group members (placeholder - actual implementation depends on group management)
            return self._resolve_group_members(group_id)
        
        elif blast_scope == BlastScope.NETWORK:
            # Network targets
            network_cidr = target.get('network_cidr')
            if not network_cidr:
                raise BlastRadiusError("Missing network_cidr for NETWORK scope")
            # Resolve network hosts (placeholder - actual implementation depends on network scanning)
            return self._resolve_network_hosts(network_cidr)
        
        elif blast_scope == BlastScope.GLOBAL:
            # Global scope (all hosts)
            # This should rarely be used and requires special approval
            return self._resolve_all_hosts()
        
        else:
            raise BlastRadiusError(f"Unknown blast scope: {blast_scope}")
    
    def _resolve_group_members(self, group_id: str) -> List[str]:
        """Resolve group members (placeholder)."""
        # Placeholder - actual implementation depends on group management
        return []
    
    def _resolve_network_hosts(self, network_cidr: str) -> List[str]:
        """Resolve network hosts (placeholder)."""
        # Placeholder - actual implementation depends on network scanning
        return []
    
    def _resolve_all_hosts(self) -> List[str]:
        """Resolve all hosts (placeholder)."""
        # Placeholder - actual implementation depends on host inventory
        return []


class BlastRadiusValidator:
    """
    Validates blast radius declaration.
    
    CRITICAL: GROUP / NETWORK / GLOBAL scopes require approval.
    Target count must match resolved targets. Mismatch = REJECT.
    """
    
    def __init__(self, resolver: BlastRadiusResolver):
        """
        Initialize blast radius validator.
        
        Args:
            resolver: Blast radius resolver
        """
        self.resolver = resolver
    
    def validate_blast_radius(
        self,
        action_type: str,
        target: Dict[str, Any],
        blast_scope: str,
        target_count: int,
        expected_impact: str,
        has_approval: bool = False
    ) -> Dict[str, Any]:
        """
        Validate blast radius declaration.
        
        Args:
            action_type: Action type
            target: Target object
            blast_scope: Blast scope (HOST, GROUP, NETWORK, GLOBAL)
            target_count: Expected target count
            expected_impact: Expected impact (LOW, MEDIUM, HIGH)
            has_approval: Whether action has HAF approval
        
        Returns:
            Validation result dictionary
        
        Raises:
            BlastRadiusError: If validation fails
        """
        # Validate blast scope
        try:
            scope = BlastScope(blast_scope)
        except ValueError:
            raise BlastRadiusError(f"Invalid blast scope: {blast_scope}")
        
        # Validate expected impact
        try:
            impact = ExpectedImpact(expected_impact)
        except ValueError:
            raise BlastRadiusError(f"Invalid expected impact: {expected_impact}")
        
        # GROUP / NETWORK / GLOBAL scopes require approval
        if scope in (BlastScope.GROUP, BlastScope.NETWORK, BlastScope.GLOBAL):
            if not has_approval:
                raise BlastRadiusError(
                    f"Blast scope {blast_scope} requires HAF approval"
                )
        
        # Resolve targets
        resolved_targets = self.resolver.resolve_targets(action_type, target, scope)
        resolved_count = len(resolved_targets)
        
        # Target count must match resolved targets
        if resolved_count != target_count:
            raise BlastRadiusError(
                f"Target count mismatch: declared {target_count}, resolved {resolved_count}"
            )
        
        return {
            'valid': True,
            'blast_scope': blast_scope,
            'target_count': target_count,
            'resolved_targets': resolved_targets,
            'expected_impact': expected_impact,
            'requires_approval': scope in (BlastScope.GROUP, BlastScope.NETWORK, BlastScope.GLOBAL)
        }
