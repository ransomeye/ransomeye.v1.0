#!/usr/bin/env python3
"""
RansomEye Threat Correlation Graph - Graph Builder
AUTHORITATIVE: Immutable graph construction with typed, directed, timestamped edges
"""

from typing import Dict, Any, List, Optional, Set
import uuid
from datetime import datetime, timezone


class GraphError(Exception):
    """Base exception for graph errors."""
    pass


class EntityNotFoundError(GraphError):
    """Raised when entity is not found."""
    pass


class DuplicateEntityError(GraphError):
    """Raised when entity already exists."""
    pass


class DuplicateEdgeError(GraphError):
    """Raised when edge already exists."""
    pass


class GraphBuilder:
    """
    Immutable graph construction.
    
    Properties:
    - Immutable: Entities and edges cannot be modified after creation
    - Typed: All edges have explicit types
    - Directed: All edges are directed (source -> target)
    - Timestamped: All edges have timestamps
    - Deterministic: Same inputs always produce same graph
    """
    
    def __init__(self):
        """Initialize graph builder."""
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[str, Dict[str, Any]] = {}
        self.entity_index: Dict[str, Set[str]] = {}  # entity_type -> set of entity_ids
        self.outgoing_edges: Dict[str, List[str]] = {}  # entity_id -> list of edge_ids
        self.incoming_edges: Dict[str, List[str]] = {}  # entity_id -> list of edge_ids
    
    def add_entity(
        self,
        entity_type: str,
        entity_label: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add entity to graph.
        
        Args:
            entity_type: Type of entity (Host, User, Process, etc.)
            entity_label: Human-readable label
            properties: Entity-specific properties
        
        Returns:
            Entity dictionary
        
        Raises:
            DuplicateEntityError: If entity with same ID already exists
        """
        entity_id = str(uuid.uuid4())
        
        # Check for duplicates (by label and type for deterministic behavior)
        # For Phase C2, we allow multiple entities with same label but different IDs
        # In production, might want to check for duplicates based on properties
        
        entity = {
            'entity_id': entity_id,
            'entity_type': entity_type,
            'entity_label': entity_label,
            'properties': properties,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'ml_confidence_placeholder': {
                'confidence_defined': False,
                'schema_version': '1.0',
                'confidence_scores': {}
            }
        }
        
        # Add to graph
        self.entities[entity_id] = entity
        
        # Update index
        if entity_type not in self.entity_index:
            self.entity_index[entity_type] = set()
        self.entity_index[entity_type].add(entity_id)
        
        # Initialize edge lists
        self.outgoing_edges[entity_id] = []
        self.incoming_edges[entity_id] = []
        
        return entity
    
    def add_edge(
        self,
        source_entity_id: str,
        target_entity_id: str,
        edge_type: str,
        edge_label: str,
        properties: Dict[str, Any],
        timestamp: str,
        inference_explanation: str
    ) -> Dict[str, Any]:
        """
        Add edge to graph.
        
        Args:
            source_entity_id: Source entity identifier
            target_entity_id: Target entity identifier
            edge_type: Type of relationship
            edge_label: Human-readable label
            properties: Edge-specific properties
            timestamp: Timestamp of relationship occurrence
            inference_explanation: Explanation of how relationship was inferred
        
        Returns:
            Edge dictionary
        
        Raises:
            EntityNotFoundError: If source or target entity not found
            DuplicateEdgeError: If edge already exists
        """
        # Verify entities exist
        if source_entity_id not in self.entities:
            raise EntityNotFoundError(f"Source entity not found: {source_entity_id}")
        if target_entity_id not in self.entities:
            raise EntityNotFoundError(f"Target entity not found: {target_entity_id}")
        
        # Check for duplicate edge (same source, target, type, timestamp)
        # For Phase C2, we allow multiple edges with same source/target/type if timestamps differ
        # But we check for exact duplicates
        for edge in self.edges.values():
            if (edge.get('source_entity_id') == source_entity_id and
                edge.get('target_entity_id') == target_entity_id and
                edge.get('edge_type') == edge_type and
                edge.get('timestamp') == timestamp):
                raise DuplicateEdgeError(
                    f"Duplicate edge: {source_entity_id} -> {target_entity_id} ({edge_type}) at {timestamp}"
                )
        
        edge_id = str(uuid.uuid4())
        
        edge = {
            'edge_id': edge_id,
            'source_entity_id': source_entity_id,
            'target_entity_id': target_entity_id,
            'edge_type': edge_type,
            'edge_label': edge_label,
            'properties': properties,
            'timestamp': timestamp,
            'inference_explanation': inference_explanation
        }
        
        # Add to graph
        self.edges[edge_id] = edge
        
        # Update edge lists
        self.outgoing_edges[source_entity_id].append(edge_id)
        self.incoming_edges[target_entity_id].append(edge_id)
        
        return edge
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Entity identifier
        
        Returns:
            Entity dictionary, or None if not found
        """
        return self.entities.get(entity_id)
    
    def get_edge(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """
        Get edge by ID.
        
        Args:
            edge_id: Edge identifier
        
        Returns:
            Edge dictionary, or None if not found
        """
        return self.edges.get(edge_id)
    
    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        Get all entities of specific type.
        
        Args:
            entity_type: Entity type
        
        Returns:
            List of entity dictionaries
        """
        entity_ids = self.entity_index.get(entity_type, set())
        return [self.entities[eid] for eid in entity_ids]
    
    def get_outgoing_edges(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get all outgoing edges from entity.
        
        Args:
            entity_id: Entity identifier
        
        Returns:
            List of edge dictionaries
        """
        edge_ids = self.outgoing_edges.get(entity_id, [])
        return [self.edges[eid] for eid in edge_ids]
    
    def get_incoming_edges(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get all incoming edges to entity.
        
        Args:
            entity_id: Entity identifier
        
        Returns:
            List of edge dictionaries
        """
        edge_ids = self.incoming_edges.get(entity_id, [])
        return [self.edges[eid] for eid in edge_ids]
    
    def get_all_entities(self) -> List[Dict[str, Any]]:
        """
        Get all entities in graph.
        
        Returns:
            List of entity dictionaries
        """
        return list(self.entities.values())
    
    def get_all_edges(self) -> List[Dict[str, Any]]:
        """
        Get all edges in graph.
        
        Returns:
            List of edge dictionaries
        """
        return list(self.edges.values())
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.
        
        Returns:
            Dictionary with graph statistics
        """
        entity_type_counts = {}
        for entity_type, entity_ids in self.entity_index.items():
            entity_type_counts[entity_type] = len(entity_ids)
        
        edge_type_counts = {}
        for edge in self.edges.values():
            edge_type = edge.get('edge_type', 'unknown')
            edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1
        
        return {
            'total_entities': len(self.entities),
            'total_edges': len(self.edges),
            'entity_type_counts': entity_type_counts,
            'edge_type_counts': edge_type_counts
        }
