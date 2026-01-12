#!/usr/bin/env python3
"""
RansomEye Threat Correlation Graph - Graph API
AUTHORITATIVE: Single API for graph operations with audit ledger integration
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone

# Add audit-ledger to path
_audit_ledger_dir = Path(__file__).parent.parent.parent / "audit-ledger"
if str(_audit_ledger_dir) not in sys.path:
    sys.path.insert(0, str(_audit_ledger_dir))

# Import audit ledger components
import importlib.util

_store_spec = importlib.util.spec_from_file_location("audit_ledger_storage", _audit_ledger_dir / "storage" / "append_only_store.py")
_store_module = importlib.util.module_from_spec(_store_spec)
_store_spec.loader.exec_module(_store_module)
AppendOnlyStore = _store_module.AppendOnlyStore
LedgerWriter = _store_module.LedgerWriter

_key_manager_spec = importlib.util.spec_from_file_location("audit_ledger_key_manager", _audit_ledger_dir / "crypto" / "key_manager.py")
_key_manager_module = importlib.util.module_from_spec(_key_manager_spec)
_key_manager_spec.loader.exec_module(_key_manager_module)
KeyManager = _key_manager_module.KeyManager

_signer_spec = importlib.util.spec_from_file_location("audit_ledger_signer", _audit_ledger_dir / "crypto" / "signer.py")
_signer_module = importlib.util.module_from_spec(_signer_spec)
_signer_spec.loader.exec_module(_signer_module)
Signer = _signer_module.Signer

# Import graph components
_graph_dir = Path(__file__).parent.parent
if str(_graph_dir) not in sys.path:
    sys.path.insert(0, str(_graph_dir))

_graph_builder_spec = importlib.util.spec_from_file_location("graph_builder", _graph_dir / "engine" / "graph_builder.py")
_graph_builder_module = importlib.util.module_from_spec(_graph_builder_spec)
_graph_builder_spec.loader.exec_module(_graph_builder_module)
GraphBuilder = _graph_builder_module.GraphBuilder

_campaign_inference_spec = importlib.util.spec_from_file_location("campaign_inference", _graph_dir / "engine" / "campaign_inference.py")
_campaign_inference_module = importlib.util.module_from_spec(_campaign_inference_spec)
_campaign_inference_spec.loader.exec_module(_campaign_inference_module)
CampaignInference = _campaign_inference_module.CampaignInference


class GraphAPIError(Exception):
    """Base exception for graph API errors."""
    pass


class GraphAPI:
    """
    Single API for graph operations.
    
    All operations:
    - Add entities and edges (immutable)
    - Infer campaigns (deterministic)
    - Export to Neo4j (lossless)
    - Emit audit ledger entries (every mutation)
    """
    
    def __init__(
        self,
        graph_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize graph API.
        
        Args:
            graph_store_path: Path to graph store file (JSON format)
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.graph_store_path = graph_store_path
        self.graph = GraphBuilder()
        self.campaign_inference = CampaignInference(self.graph)
        
        # Load existing graph if it exists
        if graph_store_path.exists():
            self._load_graph()
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise GraphAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def _load_graph(self) -> None:
        """Load graph from store file."""
        try:
            graph_data = json.loads(self.graph_store_path.read_text())
            
            # Load entities
            for entity in graph_data.get('entities', []):
                self.graph.entities[entity['entity_id']] = entity
                entity_type = entity.get('entity_type', '')
                if entity_type not in self.graph.entity_index:
                    self.graph.entity_index[entity_type] = set()
                self.graph.entity_index[entity_type].add(entity['entity_id'])
                self.graph.outgoing_edges[entity['entity_id']] = []
                self.graph.incoming_edges[entity['entity_id']] = []
            
            # Load edges
            for edge in graph_data.get('edges', []):
                self.graph.edges[edge['edge_id']] = edge
                source_id = edge.get('source_entity_id')
                target_id = edge.get('target_entity_id')
                self.graph.outgoing_edges[source_id].append(edge['edge_id'])
                self.graph.incoming_edges[target_id].append(edge['edge_id'])
        except Exception as e:
            raise GraphAPIError(f"Failed to load graph: {e}") from e
    
    def _save_graph(self) -> None:
        """Save graph to store file."""
        try:
            graph_data = {
                'entities': self.graph.get_all_entities(),
                'edges': self.graph.get_all_edges()
            }
            self.graph_store_path.write_text(json.dumps(graph_data, indent=2, ensure_ascii=False))
        except Exception as e:
            raise GraphAPIError(f"Failed to save graph: {e}") from e
    
    def add_entity(
        self,
        entity_type: str,
        entity_label: str,
        properties: Dict[str, Any],
        added_by: str
    ) -> Dict[str, Any]:
        """
        Add entity to graph.
        
        Process:
        1. Add entity to graph
        2. Save graph
        3. Emit audit ledger entry
        
        Args:
            entity_type: Type of entity
            entity_label: Human-readable label
            properties: Entity-specific properties
            added_by: Entity that added this entity
        
        Returns:
            Entity dictionary
        """
        entity = self.graph.add_entity(
            entity_type=entity_type,
            entity_label=entity_label,
            properties=properties
        )
        
        # Save graph
        self._save_graph()
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='threat-graph',
                component_instance_id='graph-engine',
                action_type='graph_entity_added',
                subject={'type': 'entity', 'id': entity['entity_id']},
                actor={'type': 'user', 'identifier': added_by},
                payload={
                    'entity_type': entity_type,
                    'entity_label': entity_label
                }
            )
        except Exception as e:
            raise GraphAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return entity
    
    def add_edge(
        self,
        source_entity_id: str,
        target_entity_id: str,
        edge_type: str,
        edge_label: str,
        properties: Dict[str, Any],
        timestamp: str,
        inference_explanation: str,
        added_by: str
    ) -> Dict[str, Any]:
        """
        Add edge to graph.
        
        Process:
        1. Add edge to graph
        2. Save graph
        3. Emit audit ledger entry
        
        Args:
            source_entity_id: Source entity identifier
            target_entity_id: Target entity identifier
            edge_type: Type of relationship
            edge_label: Human-readable label
            properties: Edge-specific properties
            timestamp: Timestamp of relationship
            inference_explanation: Explanation of inference
            added_by: Entity that added this edge
        
        Returns:
            Edge dictionary
        """
        edge = self.graph.add_edge(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            edge_type=edge_type,
            edge_label=edge_label,
            properties=properties,
            timestamp=timestamp,
            inference_explanation=inference_explanation
        )
        
        # Save graph
        self._save_graph()
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='threat-graph',
                component_instance_id='graph-engine',
                action_type='graph_edge_added',
                subject={'type': 'edge', 'id': edge['edge_id']},
                actor={'type': 'user', 'identifier': added_by},
                payload={
                    'source_entity_id': source_entity_id,
                    'target_entity_id': target_entity_id,
                    'edge_type': edge_type,
                    'inference_explanation': inference_explanation
                }
            )
        except Exception as e:
            raise GraphAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return edge
    
    def infer_campaign(self, incident_entity_id: str) -> Dict[str, Any]:
        """
        Infer campaign entities from incident.
        
        Args:
            incident_entity_id: Incident entity identifier
        
        Returns:
            Campaign inference result dictionary
        """
        related_entities = self.campaign_inference.infer_campaign_entities(incident_entity_id)
        
        return {
            'incident_entity_id': incident_entity_id,
            'related_entities': related_entities,
            'total_entities': len(related_entities)
        }
    
    def infer_lateral_movement(self, host_entity_id: str) -> Dict[str, Any]:
        """
        Infer lateral movement paths from host.
        
        Args:
            host_entity_id: Host entity identifier
        
        Returns:
            Lateral movement inference result dictionary
        """
        lateral_paths = self.campaign_inference.infer_lateral_movement(host_entity_id)
        
        return {
            'host_entity_id': host_entity_id,
            'lateral_paths': lateral_paths,
            'total_paths': len(lateral_paths)
        }
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.
        
        Returns:
            Graph statistics dictionary
        """
        return self.graph.get_graph_stats()
    
    def export_neo4j(self, output_path: Path, format: str = 'cypher') -> None:
        """
        Export graph to Neo4j-compatible format.
        
        Args:
            output_path: Path to output file
            format: Export format ('cypher', 'json', or 'csv')
        
        Raises:
            GraphAPIError: If export fails
        """
        from export.neo4j_exporter import Neo4jExporter
        
        try:
            if format == 'cypher':
                Neo4jExporter.export_cypher(self.graph, output_path)
            elif format == 'json':
                Neo4jExporter.export_json(self.graph, output_path)
            elif format == 'csv':
                nodes_path = output_path.parent / f"{output_path.stem}_nodes.csv"
                edges_path = output_path.parent / f"{output_path.stem}_edges.csv"
                Neo4jExporter.export_csv(self.graph, nodes_path, edges_path)
            else:
                raise GraphAPIError(f"Unsupported export format: {format}")
        except Exception as e:
            raise GraphAPIError(f"Failed to export graph: {e}") from e
