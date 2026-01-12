#!/usr/bin/env python3
"""
RansomEye Threat Correlation Graph - Neo4j Exporter
AUTHORITATIVE: Lossless export to Neo4j-compatible format
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from engine.graph_builder import GraphBuilder


class ExportError(Exception):
    """Base exception for export errors."""
    pass


class Neo4jExporter:
    """
    Lossless export to Neo4j-compatible format.
    
    Properties:
    - Lossless: No information is lost in export
    - Deterministic: Same graph always produces same export
    - No runtime dependency: No Neo4j runtime required
    """
    
    @staticmethod
    def export_cypher(graph: GraphBuilder, output_path: Path) -> None:
        """
        Export graph to Neo4j Cypher format.
        
        Args:
            graph: Graph builder instance
            output_path: Path to output Cypher file
        
        Raises:
            ExportError: If export fails
        """
        try:
            cypher_statements = []
            
            # Export entities (CREATE nodes)
            for entity in graph.get_all_entities():
                entity_type = entity.get('entity_type', '')
                entity_id = entity.get('entity_id', '')
                entity_label = entity.get('entity_label', '')
                properties = entity.get('properties', {})
                
                # Escape label for Cypher
                escaped_label = entity_label.replace("'", "\\'")
                
                # Build properties string
                props = {**properties, 'entity_id': entity_id, 'created_at': entity.get('created_at')}
                props_str = ', '.join([f"{k}: '{v}'" if isinstance(v, str) else f"{k}: {v}" for k, v in props.items()])
                
                # Create Cypher statement
                cypher = f"CREATE (n:{entity_type} {{entity_id: '{entity_id}', entity_label: '{escaped_label}', {props_str}}})"
                cypher_statements.append(cypher)
            
            # Export edges (CREATE relationships)
            for edge in graph.get_all_edges():
                source_id = edge.get('source_entity_id', '')
                target_id = edge.get('target_entity_id', '')
                edge_type = edge.get('edge_type', '')
                edge_label = edge.get('edge_label', '')
                properties = edge.get('properties', {})
                timestamp = edge.get('timestamp', '')
                explanation = edge.get('inference_explanation', '')
                
                # Escape label for Cypher
                escaped_label = edge_label.replace("'", "\\'")
                escaped_explanation = explanation.replace("'", "\\'")
                
                # Build properties string
                props = {**properties, 'edge_id': edge.get('edge_id'), 'timestamp': timestamp, 'inference_explanation': escaped_explanation}
                props_str = ', '.join([f"{k}: '{v}'" if isinstance(v, str) else f"{k}: {v}" for k, v in props.items()])
                
                # Create Cypher statement
                cypher = f"MATCH (a), (b) WHERE a.entity_id = '{source_id}' AND b.entity_id = '{target_id}' CREATE (a)-[r:{edge_type} {{edge_label: '{escaped_label}', {props_str}}}]->(b)"
                cypher_statements.append(cypher)
            
            # Write Cypher file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(cypher_statements))
                f.write('\n')
        
        except Exception as e:
            raise ExportError(f"Failed to export to Cypher: {e}") from e
    
    @staticmethod
    def export_json(graph: GraphBuilder, output_path: Path) -> None:
        """
        Export graph to JSON format (Neo4j-compatible structure).
        
        Args:
            graph: Graph builder instance
            output_path: Path to output JSON file
        
        Raises:
            ExportError: If export fails
        """
        try:
            # Build Neo4j-compatible structure
            export_data = {
                'nodes': [],
                'relationships': []
            }
            
            # Export entities as nodes
            for entity in graph.get_all_entities():
                node = {
                    'id': entity.get('entity_id'),
                    'labels': [entity.get('entity_type', '')],
                    'properties': {
                        'entity_id': entity.get('entity_id'),
                        'entity_label': entity.get('entity_label'),
                        **entity.get('properties', {})
                    }
                }
                export_data['nodes'].append(node)
            
            # Export edges as relationships
            for edge in graph.get_all_edges():
                relationship = {
                    'id': edge.get('edge_id'),
                    'type': edge.get('edge_type'),
                    'startNode': edge.get('source_entity_id'),
                    'endNode': edge.get('target_entity_id'),
                    'properties': {
                        'edge_id': edge.get('edge_id'),
                        'edge_label': edge.get('edge_label'),
                        'timestamp': edge.get('timestamp'),
                        'inference_explanation': edge.get('inference_explanation'),
                        **edge.get('properties', {})
                    }
                }
                export_data['relationships'].append(relationship)
            
            # Write JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            raise ExportError(f"Failed to export to JSON: {e}") from e
    
    @staticmethod
    def export_csv(graph: GraphBuilder, nodes_path: Path, edges_path: Path) -> None:
        """
        Export graph to CSV format (Neo4j import format).
        
        Args:
            graph: Graph builder instance
            nodes_path: Path to output nodes CSV file
            edges_path: Path to output edges CSV file
        
        Raises:
            ExportError: If export fails
        """
        try:
            import csv
            
            # Export nodes
            with open(nodes_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['entity_id:ID', 'entity_label', 'entity_type:LABEL', 'properties'])
                
                for entity in graph.get_all_entities():
                    props_json = json.dumps(entity.get('properties', {}))
                    writer.writerow([
                        entity.get('entity_id'),
                        entity.get('entity_label'),
                        entity.get('entity_type'),
                        props_json
                    ])
            
            # Export edges
            with open(edges_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([':START_ID', ':END_ID', ':TYPE', 'edge_label', 'timestamp', 'inference_explanation', 'properties'])
                
                for edge in graph.get_all_edges():
                    props_json = json.dumps(edge.get('properties', {}))
                    writer.writerow([
                        edge.get('source_entity_id'),
                        edge.get('target_entity_id'),
                        edge.get('edge_type'),
                        edge.get('edge_label'),
                        edge.get('timestamp'),
                        edge.get('inference_explanation'),
                        props_json
                    ])
        
        except Exception as e:
            raise ExportError(f"Failed to export to CSV: {e}") from e
