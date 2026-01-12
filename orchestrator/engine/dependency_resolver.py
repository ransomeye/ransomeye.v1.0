#!/usr/bin/env python3
"""
RansomEye Orchestrator - Dependency Resolver
AUTHORITATIVE: DAG validation and execution order resolution
"""

from typing import Dict, Any, List, Set
from collections import defaultdict, deque


class DependencyResolutionError(Exception):
    """Base exception for dependency resolution errors."""
    pass


class DependencyResolver:
    """
    Dependency resolver for workflow steps.
    
    Properties:
    - DAG validation: Validates workflow is a valid DAG
    - Deterministic ordering: Same workflow = same execution order
    - No cycles: Detects and rejects cyclic dependencies
    """
    
    def __init__(self):
        """Initialize dependency resolver."""
        pass
    
    def resolve_execution_order(self, workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Resolve execution order for workflow steps.
        
        Uses topological sort to determine execution order based on input_refs.
        
        Args:
            workflow: Workflow dictionary
        
        Returns:
            List of steps in execution order
        """
        steps = workflow.get('steps', [])
        
        if not steps:
            return []
        
        # Build dependency graph
        step_map = {step['step_id']: step for step in steps}
        dependencies = defaultdict(set)  # step_id -> set of step_ids it depends on
        dependents = defaultdict(set)  # step_id -> set of step_ids that depend on it
        
        for step in steps:
            step_id = step['step_id']
            input_refs = step.get('input_refs', [])
            
            # Find steps that produce these input_refs
            for input_ref in input_refs:
                for other_step in steps:
                    if other_step['step_id'] != step_id:
                        other_outputs = other_step.get('output_refs', [])
                        if input_ref in other_outputs:
                            dependencies[step_id].add(other_step['step_id'])
                            dependents[other_step['step_id']].add(step_id)
        
        # Topological sort
        execution_order = []
        in_degree = {step_id: len(dependencies[step_id]) for step_id in step_map.keys()}
        queue = deque([step_id for step_id, degree in in_degree.items() if degree == 0])
        
        while queue:
            step_id = queue.popleft()
            execution_order.append(step_map[step_id])
            
            for dependent_id in dependents[step_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)
        
        # Check for cycles
        if len(execution_order) != len(steps):
            raise DependencyResolutionError("Workflow contains cyclic dependencies")
        
        return execution_order
