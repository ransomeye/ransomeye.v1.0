#!/usr/bin/env python3
"""
RansomEye Threat Correlation Graph - Campaign Inference
AUTHORITATIVE: Deterministic graph traversal for campaign inference
"""

from typing import List, Dict, Any, Set, Optional
from engine.graph_builder import GraphBuilder, EntityNotFoundError


class InferenceError(Exception):
    """Base exception for inference errors."""
    pass


class CampaignInference:
    """
    Deterministic campaign inference through graph traversal.
    
    Properties:
    - Deterministic: Same graph always produces same inferences
    - Explicit rules: All inference logic is explicit (no ML yet)
    - Explainable: All inferred paths are explainable
    """
    
    def __init__(self, graph: GraphBuilder):
        """
        Initialize campaign inference.
        
        Args:
            graph: Graph builder instance
        """
        self.graph = graph
    
    def find_campaign_paths(
        self,
        start_entity_id: str,
        target_entity_id: str,
        max_depth: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find all paths from start entity to target entity.
        
        Uses deterministic breadth-first search.
        
        Args:
            start_entity_id: Starting entity identifier
            target_entity_id: Target entity identifier
            max_depth: Maximum traversal depth
        
        Returns:
            List of path dictionaries (each path is explainable)
        """
        if start_entity_id not in self.graph.entities:
            raise EntityNotFoundError(f"Start entity not found: {start_entity_id}")
        if target_entity_id not in self.graph.entities:
            raise EntityNotFoundError(f"Target entity not found: {target_entity_id}")
        
        # Breadth-first search (deterministic)
        paths = []
        queue = [(start_entity_id, [start_entity_id], [])]  # (current_entity, entity_path, edge_path)
        visited = set()
        
        while queue:
            current_entity, entity_path, edge_path = queue.pop(0)
            
            # Check if we've reached target
            if current_entity == target_entity_id:
                paths.append({
                    'entity_path': entity_path,
                    'edge_path': edge_path,
                    'path_length': len(entity_path) - 1,
                    'explanation': self._explain_path(entity_path, edge_path)
                })
                continue
            
            # Check depth limit
            if len(entity_path) > max_depth:
                continue
            
            # Visit outgoing edges (deterministic order)
            outgoing_edges = self.graph.get_outgoing_edges(current_entity)
            for edge in sorted(outgoing_edges, key=lambda e: (e.get('timestamp', ''), e.get('edge_id', ''))):
                target = edge.get('target_entity_id')
                edge_id = edge.get('edge_id')
                
                # Avoid cycles (deterministic)
                if target not in entity_path:
                    queue.append((target, entity_path + [target], edge_path + [edge_id]))
        
        return paths
    
    def infer_campaign_entities(self, incident_entity_id: str) -> List[Dict[str, Any]]:
        """
        Infer all entities related to a campaign starting from an incident.
        
        Uses deterministic graph traversal with explicit rules.
        
        Args:
            incident_entity_id: Incident entity identifier
        
        Returns:
            List of related entity dictionaries with explanations
        """
        if incident_entity_id not in self.graph.entities:
            raise EntityNotFoundError(f"Incident entity not found: {incident_entity_id}")
        
        # Traverse graph from incident (deterministic breadth-first)
        related_entities = set([incident_entity_id])
        queue = [incident_entity_id]
        visited = set([incident_entity_id])
        
        # Traverse up to 3 hops (deterministic limit)
        max_hops = 3
        current_hop = 0
        
        while queue and current_hop < max_hops:
            current_hop += 1
            next_level = []
            
            for entity_id in queue:
                # Get outgoing edges
                outgoing_edges = self.graph.get_outgoing_edges(entity_id)
                for edge in outgoing_edges:
                    target = edge.get('target_entity_id')
                    if target not in visited:
                        visited.add(target)
                        related_entities.add(target)
                        next_level.append(target)
                
                # Get incoming edges (for bidirectional traversal)
                incoming_edges = self.graph.get_incoming_edges(entity_id)
                for edge in incoming_edges:
                    source = edge.get('source_entity_id')
                    if source not in visited:
                        visited.add(source)
                        related_entities.add(source)
                        next_level.append(source)
            
            queue = next_level
        
        # Build result with explanations
        result = []
        for entity_id in related_entities:
            entity = self.graph.get_entity(entity_id)
            if entity:
                # Find path from incident to this entity
                paths = self.find_campaign_paths(incident_entity_id, entity_id, max_depth=3)
                explanation = paths[0]['explanation'] if paths else "Directly related to incident"
                
                result.append({
                    'entity': entity,
                    'explanation': explanation,
                    'path_length': paths[0]['path_length'] if paths else 0
                })
        
        return result
    
    def infer_lateral_movement(self, host_entity_id: str) -> List[Dict[str, Any]]:
        """
        Infer lateral movement paths from a host.
        
        Uses deterministic graph traversal looking for LATERAL_MOVEMENT edges.
        
        Args:
            host_entity_id: Host entity identifier
        
        Returns:
            List of lateral movement path dictionaries
        """
        if host_entity_id not in self.graph.entities:
            raise EntityNotFoundError(f"Host entity not found: {host_entity_id}")
        
        lateral_paths = []
        visited_hosts = set([host_entity_id])
        queue = [(host_entity_id, [host_entity_id], [])]
        
        while queue:
            current_host, host_path, edge_path = queue.pop(0)
            
            # Find lateral movement edges
            outgoing_edges = self.graph.get_outgoing_edges(current_host)
            for edge in outgoing_edges:
                if edge.get('edge_type') == 'LATERAL_MOVEMENT':
                    target_host = edge.get('target_entity_id')
                    target_entity = self.graph.get_entity(target_host)
                    
                    # Check if target is a host
                    if target_entity and target_entity.get('entity_type') == 'Host':
                        if target_host not in visited_hosts:
                            visited_hosts.add(target_host)
                            lateral_paths.append({
                                'from_host': current_host,
                                'to_host': target_host,
                                'edge': edge,
                                'explanation': edge.get('inference_explanation', 'Lateral movement detected')
                            })
                            queue.append((target_host, host_path + [target_host], edge_path + [edge.get('edge_id')]))
        
        return lateral_paths
    
    def _explain_path(self, entity_path: List[str], edge_path: List[str]) -> str:
        """
        Generate explainable explanation for a path.
        
        Args:
            entity_path: List of entity IDs in path
            edge_path: List of edge IDs in path
        
        Returns:
            Human-readable explanation
        """
        if len(entity_path) < 2:
            return "Direct relationship"
        
        explanations = []
        for i, edge_id in enumerate(edge_path):
            edge = self.graph.get_edge(edge_id)
            if edge:
                source_entity = self.graph.get_entity(entity_path[i])
                target_entity = self.graph.get_entity(entity_path[i + 1])
                edge_type = edge.get('edge_type', '')
                explanation = edge.get('inference_explanation', '')
                
                explanations.append(
                    f"{source_entity.get('entity_label', '')} -> {edge_type} -> {target_entity.get('entity_label', '')} ({explanation})"
                )
        
        return " | ".join(explanations)
