#!/usr/bin/env python3
"""
RansomEye Threat Intelligence - Intel API
AUTHORITATIVE: Single API for threat intelligence operations with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import uuid
import hashlib

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

# Import threat intel components
_intel_dir = Path(__file__).parent.parent
if str(_intel_dir) not in sys.path:
    sys.path.insert(0, str(_intel_dir))

_feed_ingestor_spec = importlib.util.spec_from_file_location("feed_ingestor", _intel_dir / "engine" / "feed_ingestor.py")
_feed_ingestor_module = importlib.util.module_from_spec(_feed_ingestor_spec)
_feed_ingestor_spec.loader.exec_module(_feed_ingestor_module)
FeedIngestor = _feed_ingestor_module.FeedIngestor

_normalizer_spec = importlib.util.spec_from_file_location("normalizer", _intel_dir / "engine" / "normalizer.py")
_normalizer_module = importlib.util.module_from_spec(_normalizer_spec)
_normalizer_spec.loader.exec_module(_normalizer_module)
Normalizer = _normalizer_module.Normalizer

_deduplicator_spec = importlib.util.spec_from_file_location("deduplicator", _intel_dir / "engine" / "deduplicator.py")
_deduplicator_module = importlib.util.module_from_spec(_deduplicator_spec)
_deduplicator_spec.loader.exec_module(_deduplicator_module)
Deduplicator = _deduplicator_module.Deduplicator

_correlator_spec = importlib.util.spec_from_file_location("correlator", _intel_dir / "engine" / "correlator.py")
_correlator_module = importlib.util.module_from_spec(_correlator_spec)
_correlator_spec.loader.exec_module(_correlator_module)
Correlator = _correlator_module.Correlator

_intel_store_spec = importlib.util.spec_from_file_location("intel_store", _intel_dir / "storage" / "intel_store.py")
_intel_store_module = importlib.util.module_from_spec(_intel_store_spec)
_intel_store_spec.loader.exec_module(_intel_store_module)
IntelStore = _intel_store_module.IntelStore


class IntelAPIError(Exception):
    """Base exception for intel API errors."""
    pass


class IntelAPI:
    """
    Single API for threat intelligence operations.
    
    All operations:
    - Register intelligence sources (signed, versioned)
    - Ingest feeds (offline snapshots)
    - Normalize IOCs (canonical form)
    - Deduplicate IOCs (hash-based)
    - Correlate IOCs with evidence (deterministic)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        iocs_store_path: Path,
        sources_store_path: Path,
        correlations_store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize intel API.
        
        Args:
            iocs_store_path: Path to IOCs store
            sources_store_path: Path to intelligence sources store
            correlations_store_path: Path to correlations store
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.feed_ingestor = FeedIngestor()
        self.normalizer = Normalizer()
        self.deduplicator = Deduplicator()
        self.correlator = Correlator()
        self.intel_store = IntelStore(iocs_store_path)
        
        self.sources_store_path = Path(sources_store_path)
        self.sources_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.correlations_store_path = Path(correlations_store_path)
        self.correlations_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise IntelAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def register_source(
        self,
        source_name: str,
        source_type: str,
        source_version: str,
        signature: str,
        public_key_id: str
    ) -> Dict[str, Any]:
        """
        Register intelligence source.
        
        Args:
            source_name: Human-readable source name
            source_type: Type of source (public_feed, internal_deception, etc.)
            source_version: Source version
            signature: Ed25519 signature (hex-encoded)
            public_key_id: Public key identifier
        
        Returns:
            Source dictionary
        """
        source = {
            'source_id': str(uuid.uuid4()),
            'source_name': source_name,
            'source_type': source_type,
            'source_version': source_version,
            'signature': signature,
            'public_key_id': public_key_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'immutable_hash': ''
        }
        
        # Calculate hash
        source['immutable_hash'] = self._calculate_hash(source)
        
        # Store source
        self._store_source(source)
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='threat-intel',
                component_instance_id='threat-intel',
                action_type='intel_source_registered',
                subject={'type': 'intel_source', 'id': source.get('source_id', '')},
                actor={'type': 'system', 'identifier': 'threat-intel'},
                payload={
                    'source_id': source.get('source_id', ''),
                    'source_name': source_name,
                    'source_type': source_type
                }
            )
        except Exception as e:
            raise IntelAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return source
    
    def ingest_feed(
        self,
        feed_path: Path,
        source_id: str,
        signature: str,
        public_key_id: str
    ) -> List[Dict[str, Any]]:
        """
        Ingest intelligence feed.
        
        Args:
            feed_path: Path to feed file
            source_id: Intelligence source identifier
            signature: Feed signature
            public_key_id: Public key identifier
        
        Returns:
            List of IOC dictionaries
        """
        # Ingest feed
        raw_iocs = self.feed_ingestor.ingest_feed(feed_path, source_id, signature, public_key_id)
        
        # Normalize and store IOCs
        stored_iocs = []
        for raw_ioc in raw_iocs:
            # Normalize
            normalized_value = self.normalizer.normalize(raw_ioc)
            raw_ioc['normalized_value'] = normalized_value
            
            # Check for duplicates
            if not self.deduplicator.is_duplicate(raw_ioc):
                # Store IOC
                ioc = self.intel_store.store_ioc(
                    ioc_type=raw_ioc.get('ioc_type', ''),
                    ioc_value=raw_ioc.get('ioc_value', ''),
                    normalized_value=normalized_value,
                    intel_source_id=source_id
                )
                stored_iocs.append(ioc)
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='threat-intel',
                component_instance_id='threat-intel',
                action_type='feed_ingested',
                subject={'type': 'feed', 'path': str(feed_path)},
                actor={'type': 'system', 'identifier': 'threat-intel'},
                payload={
                    'source_id': source_id,
                    'iocs_ingested': len(stored_iocs)
                }
            )
        except Exception as e:
            raise IntelAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return stored_iocs
    
    def correlate_iocs(
        self,
        evidence: Dict[str, Any],
        evidence_type: str
    ) -> List[Dict[str, Any]]:
        """
        Correlate IOCs with evidence.
        
        Args:
            evidence: Evidence dictionary
            evidence_type: Type of evidence
        
        Returns:
            List of correlation dictionaries
        """
        # Get all IOCs
        iocs = self.intel_store.list_iocs()
        
        correlations = []
        
        # Correlate each IOC
        for ioc in iocs:
            correlation = self.correlator.correlate(ioc, evidence, evidence_type)
            if correlation:
                # Store correlation
                self._store_correlation(correlation)
                
                # Emit audit ledger entry
                try:
                    ledger_entry = self.ledger_writer.create_entry(
                        component='threat-intel',
                        component_instance_id='threat-intel',
                        action_type='ioc_correlated',
                        subject={'type': 'ioc', 'id': ioc.get('ioc_id', '')},
                        actor={'type': 'system', 'identifier': 'threat-intel'},
                        payload={
                            'correlation_id': correlation.get('correlation_id', ''),
                            'evidence_type': evidence_type,
                            'correlation_method': correlation.get('correlation_method', '')
                        }
                    )
                    correlation['ledger_entry_id'] = ledger_entry.get('ledger_entry_id', '')
                except Exception as e:
                    raise IntelAPIError(f"Failed to emit audit ledger entry: {e}") from e
                
                correlations.append(correlation)
        
        return correlations
    
    def _calculate_hash(self, source: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of source record."""
        hashable_content = {k: v for k, v in source.items() if k != 'immutable_hash'}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
    
    def _store_source(self, source: Dict[str, Any]) -> None:
        """Store source to file-based store."""
        try:
            source_json = json.dumps(source, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.sources_store_path, 'a', encoding='utf-8') as f:
                f.write(source_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise IntelAPIError(f"Failed to store source: {e}") from e
    
    def _store_correlation(self, correlation: Dict[str, Any]) -> None:
        """Store correlation to file-based store."""
        try:
            correlation_json = json.dumps(correlation, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.correlations_store_path, 'a', encoding='utf-8') as f:
                f.write(correlation_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise IntelAPIError(f"Failed to store correlation: {e}") from e
