#!/usr/bin/env python3
"""
RansomEye Threat Correlation Graph - Graph Builder CLI
AUTHORITATIVE: Command-line tool for building threat correlation graphs
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_graph_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_graph_dir))

from api.graph_api import GraphAPI, GraphAPIError


def load_entities(entities_path: Path) -> list:
    """Load entities from JSON file."""
    if not entities_path.exists():
        return []
    
    try:
        content = entities_path.read_text()
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get('entities', [])
        else:
            return []
    except Exception as e:
        print(f"Warning: Failed to load entities from {entities_path}: {e}", file=sys.stderr)
        return []


def load_edges(edges_path: Path) -> list:
    """Load edges from JSON file."""
    if not edges_path.exists():
        return []
    
    try:
        content = edges_path.read_text()
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get('edges', [])
        else:
            return []
    except Exception as e:
        print(f"Warning: Failed to load edges from {edges_path}: {e}", file=sys.stderr)
        return []


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Build threat correlation graph'
    )
    parser.add_argument(
        '--entities',
        type=Path,
        help='Path to entities JSON file (optional)'
    )
    parser.add_argument(
        '--edges',
        type=Path,
        help='Path to edges JSON file (optional)'
    )
    parser.add_argument(
        '--graph-store',
        type=Path,
        required=True,
        help='Path to graph store file'
    )
    parser.add_argument(
        '--ledger',
        type=Path,
        required=True,
        help='Path to audit ledger file'
    )
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        required=True,
        help='Directory containing ledger signing keys'
    )
    parser.add_argument(
        '--added-by',
        default='system',
        help='Entity that added entities/edges (default: system)'
    )
    parser.add_argument(
        '--infer-campaign',
        help='Incident entity ID to infer campaign for (optional)'
    )
    parser.add_argument(
        '--infer-lateral-movement',
        help='Host entity ID to infer lateral movement for (optional)'
    )
    parser.add_argument(
        '--export-neo4j',
        type=Path,
        help='Path to export Neo4j graph (optional)'
    )
    parser.add_argument(
        '--export-format',
        choices=['cypher', 'json', 'csv'],
        default='cypher',
        help='Neo4j export format (default: cypher)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output result JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize graph API
        api = GraphAPI(
            graph_store_path=args.graph_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Load and add entities
        if args.entities:
            entities = load_entities(args.entities)
            for entity_data in entities:
                api.add_entity(
                    entity_type=entity_data.get('entity_type', ''),
                    entity_label=entity_data.get('entity_label', ''),
                    properties=entity_data.get('properties', {}),
                    added_by=args.added_by
                )
        
        # Load and add edges
        if args.edges:
            edges = load_edges(args.edges)
            for edge_data in edges:
                api.add_edge(
                    source_entity_id=edge_data.get('source_entity_id', ''),
                    target_entity_id=edge_data.get('target_entity_id', ''),
                    edge_type=edge_data.get('edge_type', ''),
                    edge_label=edge_data.get('edge_label', ''),
                    properties=edge_data.get('properties', {}),
                    timestamp=edge_data.get('timestamp', ''),
                    inference_explanation=edge_data.get('inference_explanation', ''),
                    added_by=args.added_by
                )
        
        result = {
            'graph_stats': api.get_graph_stats()
        }
        
        # Infer campaign if requested
        if args.infer_campaign:
            campaign_result = api.infer_campaign(args.infer_campaign)
            result['campaign_inference'] = campaign_result
        
        # Infer lateral movement if requested
        if args.infer_lateral_movement:
            lateral_result = api.infer_lateral_movement(args.infer_lateral_movement)
            result['lateral_movement_inference'] = lateral_result
        
        # Export to Neo4j if requested
        if args.export_neo4j:
            api.export_neo4j(args.export_neo4j, format=args.export_format)
            result['export_path'] = str(args.export_neo4j)
            result['export_format'] = args.export_format
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            print(f"Graph built successfully. Result written to: {args.output}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print(f"\nGraph Statistics:")
        stats = result['graph_stats']
        print(f"  Total entities: {stats['total_entities']}")
        print(f"  Total edges: {stats['total_edges']}")
        print(f"  Entity types: {stats['entity_type_counts']}")
        print(f"  Edge types: {stats['edge_type_counts']}")
        
    except GraphAPIError as e:
        print(f"Graph build failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
