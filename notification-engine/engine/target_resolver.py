#!/usr/bin/env python3
"""
RansomEye Notification Engine - Target Resolver
AUTHORITATIVE: Resolves delivery targets for alerts (policy-driven)
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json


class TargetResolutionError(Exception):
    """Base exception for target resolution errors."""
    pass


class TargetResolver:
    """
    Resolves delivery targets for alerts.
    
    Properties:
    - Policy-driven: Targets resolved based on policy/routing decisions
    - Deterministic: Same alert + same policy = same targets
    - Read-only: Only reads target configuration, never mutates
    """
    
    def __init__(self, targets_store_path: Path):
        """
        Initialize target resolver.
        
        Args:
            targets_store_path: Path to delivery targets store
        """
        self.targets_store_path = Path(targets_store_path)
        self.targets_store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def resolve_targets(
        self,
        alert: Dict[str, Any],
        routing_decision: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Resolve delivery targets for alert.
        
        Targets are resolved based on routing decision and alert properties.
        
        Args:
            alert: Alert dictionary
            routing_decision: Routing decision from policy engine
        
        Returns:
            List of target dictionaries
        """
        targets = []
        
        # Get all targets
        all_targets = self._load_all_targets()
        
        # Resolve targets based on routing action
        routing_action = routing_decision.get('routing_action', '')
        
        if routing_action == 'notify':
            # Notify action: resolve all targets matching alert severity
            severity = alert.get('severity', '')
            for target in all_targets:
                if self._target_matches_severity(target, severity):
                    targets.append(target)
        elif routing_action == 'escalate':
            # Escalate action: resolve escalation targets
            for target in all_targets:
                if target.get('target_type') in ['email', 'ticket']:
                    targets.append(target)
        elif routing_action == 'route':
            # Route action: resolve based on alert properties
            for target in all_targets:
                if self._target_matches_alert(target, alert):
                    targets.append(target)
        
        return targets
    
    def _load_all_targets(self) -> List[Dict[str, Any]]:
        """Load all delivery targets from store."""
        targets = []
        
        if not self.targets_store_path.exists():
            return targets
        
        try:
            with open(self.targets_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    targets.append(json.loads(line))
        except Exception:
            pass
        
        return targets
    
    def _target_matches_severity(self, target: Dict[str, Any], severity: str) -> bool:
        """Check if target matches severity."""
        # Simple matching: all targets match all severities by default
        # In production, targets might have severity filters
        return True
    
    def _target_matches_alert(self, target: Dict[str, Any], alert: Dict[str, Any]) -> bool:
        """Check if target matches alert properties."""
        # Simple matching: all targets match all alerts by default
        # In production, targets might have alert filters
        return True
