#!/usr/bin/env python3
"""
RansomEye Alert Policy - Rule Evaluator
AUTHORITATIVE: Deterministic rule evaluation
"""

from typing import Dict, Any, List, Optional


class EvaluationError(Exception):
    """Base exception for evaluation errors."""
    pass


class RuleEvaluator:
    """
    Deterministic rule evaluation.
    
    Properties:
    - Deterministic: Same inputs always produce same evaluation result
    - Explicit: All conditions are explicit, no implicit defaults
    - No ambiguity: Rules are evaluated in priority order
    """
    
    def __init__(self):
        """Initialize rule evaluator."""
        pass
    
    def evaluate_rules(self, alert: Dict[str, Any], rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Evaluate rules against alert.
        
        Rules are evaluated in priority order (highest priority first).
        First matching rule is returned.
        
        Args:
            alert: Alert dictionary
            rules: List of policy rules (ordered by priority)
        
        Returns:
            Matching rule dictionary, or None if no match
        """
        # Sort rules by priority (descending, highest first)
        sorted_rules = sorted(rules, key=lambda r: r.get('priority', 0), reverse=True)
        
        for rule in sorted_rules:
            if self._rule_matches(alert, rule):
                return rule
        
        return None
    
    def _rule_matches(self, alert: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """
        Check if rule matches alert.
        
        Args:
            alert: Alert dictionary
            rule: Policy rule dictionary
        
        Returns:
            True if rule matches, False otherwise
        """
        # Check match conditions
        match_conditions = rule.get('match_conditions', {})
        condition_type = match_conditions.get('condition_type', 'all')
        conditions = match_conditions.get('conditions', [])
        
        if not conditions:
            return False
        
        # Evaluate conditions
        condition_results = []
        for condition in conditions:
            result = self._evaluate_condition(alert, condition)
            condition_results.append(result)
        
        # Apply logical operator
        if condition_type == 'all':
            return all(condition_results)
        elif condition_type == 'any':
            return any(condition_results)
        else:
            return False
    
    def _evaluate_condition(self, alert: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """
        Evaluate single condition.
        
        Args:
            alert: Alert dictionary
            condition: Condition dictionary
        
        Returns:
            True if condition matches, False otherwise
        """
        field = condition.get('field', '')
        operator = condition.get('operator', '')
        value = condition.get('value')
        
        # Get alert field value
        alert_value = self._get_alert_field(alert, field)
        
        if alert_value is None:
            return False
        
        # Evaluate operator
        if operator == 'equals':
            return alert_value == value
        elif operator == 'not_equals':
            return alert_value != value
        elif operator == 'greater_than':
            return alert_value > value
        elif operator == 'less_than':
            return alert_value < value
        elif operator == 'greater_than_or_equal':
            return alert_value >= value
        elif operator == 'less_than_or_equal':
            return alert_value <= value
        elif operator == 'in':
            return alert_value in (value if isinstance(value, list) else [value])
        elif operator == 'not_in':
            return alert_value not in (value if isinstance(value, list) else [value])
        else:
            return False
    
    def _get_alert_field(self, alert: Dict[str, Any], field: str) -> Any:
        """Get alert field value."""
        # Map field names to alert structure
        field_mapping = {
            'alert_type': alert.get('alert_type'),
            'severity': alert.get('severity'),
            'risk_score': alert.get('risk_score'),
            'source_component': alert.get('source_component'),
            'subject_type': alert.get('subject_type'),
            'mitre_technique_id': alert.get('mitre_technique_id'),
            'campaign_id': alert.get('campaign_id')
        }
        
        return field_mapping.get(field)
