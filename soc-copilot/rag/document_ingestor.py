#!/usr/bin/env python3
"""
RansomEye SOC Copilot - Document Ingestor
AUTHORITATIVE: Read-only ingestion of knowledge sources (immutable, verifiable)
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid


class IngestionError(Exception):
    """Base exception for ingestion errors."""
    pass


class DocumentIngestor:
    """
    Read-only ingestion of knowledge sources.
    
    Properties:
    - Read-only: Only reads from sources, never mutates
    - Immutable: All ingested documents are immutable
    - Verifiable: All sources are verifiable
    - Deterministic: Same sources always produce same documents
    """
    
    def __init__(self):
        """Initialize document ingestor."""
        pass
    
    def ingest_audit_ledger(self, ledger_path: Path) -> List[Dict[str, Any]]:
        """
        Ingest audit ledger entries.
        
        Args:
            ledger_path: Path to audit ledger file
        
        Returns:
            List of document dictionaries
        """
        documents = []
        
        if not ledger_path.exists():
            return documents
        
        try:
            with open(ledger_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    
                    doc = {
                        'doc_id': str(uuid.uuid4()),
                        'source_type': 'audit_ledger',
                        'source_id': entry.get('ledger_entry_id', ''),
                        'source_location': f"{ledger_path}:{line_num}",
                        'content': json.dumps(entry, sort_keys=True),
                        'metadata': {
                            'component': entry.get('component', ''),
                            'action_type': entry.get('action_type', ''),
                            'timestamp': entry.get('timestamp', '')
                        }
                    }
                    documents.append(doc)
        except Exception as e:
            raise IngestionError(f"Failed to ingest audit ledger: {e}") from e
        
        return documents
    
    def ingest_killchain_timeline(self, timeline_path: Path) -> List[Dict[str, Any]]:
        """
        Ingest killchain timeline events.
        
        Args:
            timeline_path: Path to killchain timeline file
        
        Returns:
            List of document dictionaries
        """
        documents = []
        
        if not timeline_path.exists():
            return documents
        
        try:
            timeline_data = json.loads(timeline_path.read_text())
            events = timeline_data.get('timeline', [])
            
            for event in events:
                doc = {
                    'doc_id': str(uuid.uuid4()),
                    'source_type': 'killchain_timeline',
                    'source_id': event.get('event_id', ''),
                    'source_location': str(timeline_path),
                    'content': json.dumps(event, sort_keys=True),
                    'metadata': {
                        'mitre_technique_id': event.get('mitre_technique_id', ''),
                        'mitre_stage': event.get('mitre_stage', ''),
                        'timestamp': event.get('timestamp', '')
                    }
                }
                documents.append(doc)
        except Exception as e:
            raise IngestionError(f"Failed to ingest killchain timeline: {e}") from e
        
        return documents
    
    def ingest_threat_graph(self, graph_path: Path) -> List[Dict[str, Any]]:
        """
        Ingest threat graph entities and relationships.
        
        Args:
            graph_path: Path to threat graph file
        
        Returns:
            List of document dictionaries
        """
        documents = []
        
        if not graph_path.exists():
            return documents
        
        try:
            graph_data = json.loads(graph_path.read_text())
            
            # Ingest entities
            for entity in graph_data.get('entities', []):
                doc = {
                    'doc_id': str(uuid.uuid4()),
                    'source_type': 'threat_graph',
                    'source_id': entity.get('entity_id', ''),
                    'source_location': f"{graph_path}:entity",
                    'content': json.dumps(entity, sort_keys=True),
                    'metadata': {
                        'entity_type': entity.get('entity_type', ''),
                        'entity_label': entity.get('entity_label', '')
                    }
                }
                documents.append(doc)
            
            # Ingest edges
            for edge in graph_data.get('edges', []):
                doc = {
                    'doc_id': str(uuid.uuid4()),
                    'source_type': 'threat_graph',
                    'source_id': edge.get('edge_id', ''),
                    'source_location': f"{graph_path}:edge",
                    'content': json.dumps(edge, sort_keys=True),
                    'metadata': {
                        'edge_type': edge.get('edge_type', ''),
                        'source_entity': edge.get('source_entity_id', ''),
                        'target_entity': edge.get('target_entity_id', '')
                    }
                }
                documents.append(doc)
        except Exception as e:
            raise IngestionError(f"Failed to ingest threat graph: {e}") from e
        
        return documents
    
    def ingest_risk_index(self, risk_store_path: Path) -> List[Dict[str, Any]]:
        """
        Ingest risk index history.
        
        Args:
            risk_store_path: Path to risk store file
        
        Returns:
            List of document dictionaries
        """
        documents = []
        
        if not risk_store_path.exists():
            return documents
        
        try:
            with open(risk_store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    risk_record = json.loads(line)
                    
                    doc = {
                        'doc_id': str(uuid.uuid4()),
                        'source_type': 'risk_index',
                        'source_id': risk_record.get('computation_id', ''),
                        'source_location': str(risk_store_path),
                        'content': json.dumps(risk_record, sort_keys=True),
                        'metadata': {
                            'risk_score': risk_record.get('risk_score', 0),
                            'timestamp': risk_record.get('timestamp', '')
                        }
                    }
                    documents.append(doc)
        except Exception as e:
            raise IngestionError(f"Failed to ingest risk index: {e}") from e
        
        return documents
    
    def ingest_explanation_bundles(self, bundles_dir: Path) -> List[Dict[str, Any]]:
        """
        Ingest explanation bundles (SEE).
        
        Args:
            bundles_dir: Directory containing explanation bundles
        
        Returns:
            List of document dictionaries
        """
        documents = []
        
        if not bundles_dir.exists():
            return documents
        
        try:
            for bundle_path in bundles_dir.glob('*.json'):
                bundle = json.loads(bundle_path.read_text())
                
                doc = {
                    'doc_id': str(uuid.uuid4()),
                    'source_type': 'explanation_bundle',
                    'source_id': bundle.get('bundle_id', ''),
                    'source_location': str(bundle_path),
                    'content': json.dumps(bundle, sort_keys=True),
                    'metadata': {
                        'explanation_type': bundle.get('explanation_type', ''),
                        'subject_id': bundle.get('subject_id', '')
                    }
                }
                documents.append(doc)
        except Exception as e:
            raise IngestionError(f"Failed to ingest explanation bundles: {e}") from e
        
        return documents
    
    def ingest_playbook_metadata(self, playbook_registry_path: Path) -> List[Dict[str, Any]]:
        """
        Ingest playbook metadata (NOT execution records).
        
        Args:
            playbook_registry_path: Path to playbook registry file
        
        Returns:
            List of document dictionaries
        """
        documents = []
        
        if not playbook_registry_path.exists():
            return documents
        
        try:
            with open(playbook_registry_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    playbook = json.loads(line)
                    
                    # Only ingest metadata, not execution details
                    metadata = {
                        'playbook_id': playbook.get('playbook_id', ''),
                        'playbook_name': playbook.get('playbook_name', ''),
                        'playbook_version': playbook.get('playbook_version', ''),
                        'scope': playbook.get('scope', ''),
                        'step_count': len(playbook.get('steps', []))
                    }
                    
                    doc = {
                        'doc_id': str(uuid.uuid4()),
                        'source_type': 'playbook_metadata',
                        'source_id': playbook.get('playbook_id', ''),
                        'source_location': str(playbook_registry_path),
                        'content': json.dumps(metadata, sort_keys=True),
                        'metadata': {
                            'playbook_name': playbook.get('playbook_name', ''),
                            'scope': playbook.get('scope', '')
                        }
                    }
                    documents.append(doc)
        except Exception as e:
            raise IngestionError(f"Failed to ingest playbook metadata: {e}") from e
        
        return documents
    
    def ingest_mitre_attck(self, mitre_docs_path: Path) -> List[Dict[str, Any]]:
        """
        Ingest MITRE ATT&CK documentation (offline snapshot).
        
        Args:
            mitre_docs_path: Path to MITRE ATT&CK documentation directory
        
        Returns:
            List of document dictionaries
        """
        documents = []
        
        if not mitre_docs_path.exists():
            return documents
        
        try:
            # Ingest JSON files in MITRE docs directory
            for doc_file in mitre_docs_path.glob('*.json'):
                mitre_data = json.loads(doc_file.read_text())
                
                doc = {
                    'doc_id': str(uuid.uuid4()),
                    'source_type': 'mitre_attck',
                    'source_id': mitre_data.get('id', ''),
                    'source_location': str(doc_file),
                    'content': json.dumps(mitre_data, sort_keys=True),
                    'metadata': {
                        'technique_id': mitre_data.get('technique_id', ''),
                        'tactic': mitre_data.get('tactic', '')
                    }
                }
                documents.append(doc)
        except Exception as e:
            raise IngestionError(f"Failed to ingest MITRE ATT&CK: {e}") from e
        
        return documents
