#!/usr/bin/env python3
"""
RansomEye Threat Intelligence - Feed Ingestor
AUTHORITATIVE: Offline snapshot ingestion of intelligence feeds
"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib


class FeedIngestionError(Exception):
    """Base exception for feed ingestion errors."""
    pass


class FeedIngestor:
    """
    Offline snapshot feed ingestor.
    
    Properties:
    - Offline-only: Runtime operation is offline-only
    - Signed snapshots: Feeds must be signed and versioned
    - Deterministic: Same feed = same ingestion result
    """
    
    def __init__(self):
        """Initialize feed ingestor."""
        pass
    
    def ingest_feed(
        self,
        feed_path: Path,
        source_id: str,
        signature: str,
        public_key_id: str
    ) -> List[Dict[str, Any]]:
        """
        Ingest intelligence feed from offline snapshot.
        
        Args:
            feed_path: Path to feed file (JSON, CSV, or STIX)
            source_id: Intelligence source identifier
            signature: Ed25519 signature of feed (hex-encoded)
            public_key_id: Public key identifier for verification
        
        Returns:
            List of IOC dictionaries
        """
        if not feed_path.exists():
            raise FeedIngestionError(f"Feed file not found: {feed_path}")
        
        # Verify signature (stub for Phase J)
        # In production, would verify Ed25519 signature
        
        # Load feed based on format
        feed_format = self._detect_format(feed_path)
        
        if feed_format == 'json':
            iocs = self._ingest_json_feed(feed_path, source_id)
        elif feed_format == 'csv':
            iocs = self._ingest_csv_feed(feed_path, source_id)
        elif feed_format == 'stix':
            iocs = self._ingest_stix_feed(feed_path, source_id)
        else:
            raise FeedIngestionError(f"Unsupported feed format: {feed_format}")
        
        return iocs
    
    def _detect_format(self, feed_path: Path) -> str:
        """Detect feed format."""
        suffix = feed_path.suffix.lower()
        if suffix == '.json':
            return 'json'
        elif suffix == '.csv':
            return 'csv'
        elif suffix in ['.stix', '.stix2']:
            return 'stix'
        else:
            # Default to JSON
            return 'json'
    
    def _ingest_json_feed(self, feed_path: Path, source_id: str) -> List[Dict[str, Any]]:
        """Ingest JSON feed."""
        iocs = []
        
        try:
            feed_data = json.loads(feed_path.read_text())
            
            # Handle different JSON feed structures
            if isinstance(feed_data, list):
                items = feed_data
            elif isinstance(feed_data, dict) and 'indicators' in feed_data:
                items = feed_data['indicators']
            elif isinstance(feed_data, dict) and 'iocs' in feed_data:
                items = feed_data['iocs']
            else:
                items = [feed_data]
            
            for item in items:
                ioc = self._parse_ioc(item, source_id)
                if ioc:
                    iocs.append(ioc)
        except Exception as e:
            raise FeedIngestionError(f"Failed to ingest JSON feed: {e}") from e
        
        return iocs
    
    def _ingest_csv_feed(self, feed_path: Path, source_id: str) -> List[Dict[str, Any]]:
        """Ingest CSV feed."""
        iocs = []
        
        try:
            import csv
            with open(feed_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ioc = self._parse_ioc(row, source_id)
                    if ioc:
                        iocs.append(ioc)
        except Exception as e:
            raise FeedIngestionError(f"Failed to ingest CSV feed: {e}") from e
        
        return iocs
    
    def _ingest_stix_feed(self, feed_path: Path, source_id: str) -> List[Dict[str, Any]]:
        """Ingest STIX feed (stub for Phase J)."""
        # For Phase J, treat STIX as JSON
        # In production, would use proper STIX parser
        return self._ingest_json_feed(feed_path, source_id)
    
    def _parse_ioc(self, item: Dict[str, Any], source_id: str) -> Dict[str, Any]:
        """Parse IOC from feed item."""
        # Extract IOC type and value
        ioc_type = item.get('type', '').lower()
        ioc_value = item.get('value', '') or item.get('indicator', '') or item.get('ioc', '')
        
        if not ioc_type or not ioc_value:
            return None
        
        # Map to supported IOC types
        type_mapping = {
            'ip': 'ip_address',
            'ipv4': 'ip_address',
            'domain': 'domain',
            'url': 'url',
            'md5': 'file_hash_md5',
            'sha1': 'file_hash_sha1',
            'sha256': 'file_hash_sha256',
            'email': 'email_address',
            'registry': 'registry_key',
            'process': 'process_name',
            'mutex': 'mutex',
            'user-agent': 'user_agent'
        }
        
        normalized_type = type_mapping.get(ioc_type, ioc_type)
        
        if normalized_type not in [
            'ip_address', 'domain', 'url', 'file_hash_md5', 'file_hash_sha1',
            'file_hash_sha256', 'email_address', 'registry_key', 'process_name',
            'mutex', 'user_agent'
        ]:
            return None
        
        return {
            'ioc_type': normalized_type,
            'ioc_value': str(ioc_value),
            'intel_source_id': source_id
        }
