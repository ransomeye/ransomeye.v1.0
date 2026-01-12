#!/usr/bin/env python3
"""
RansomEye Network Scanner - CVE Matcher
AUTHORITATIVE: Offline CVE matching from NVD snapshot
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import uuid
import hashlib
import json
import re


class CVEMatchError(Exception):
    """Base exception for CVE matching errors."""
    pass


class CVEMatcher:
    """
    Offline CVE matcher.
    
    Properties:
    - Offline: Uses offline NVD snapshot only
    - Banner-based: Banner/service-based matching only
    - Deterministic: Deterministic matching rules only
    - No exploitability scoring: No exploitability scoring
    """
    
    def __init__(self, cve_db_path: Path):
        """
        Initialize CVE matcher.
        
        Args:
            cve_db_path: Path to CVE database directory
        """
        self.cve_db_path = Path(cve_db_path)
        self.cve_db_path.mkdir(parents=True, exist_ok=True)
        self.cve_cache = {}
        self._load_cve_db()
    
    def _load_cve_db(self) -> None:
        """Load CVE database from offline snapshot."""
        # For Phase H, use simplified CVE database
        # In production, would load from NVD JSON feed snapshot
        cve_db_file = self.cve_db_path / 'cve_db.json'
        
        if cve_db_file.exists():
            try:
                with open(cve_db_file, 'r', encoding='utf-8') as f:
                    self.cve_cache = json.load(f)
            except Exception:
                self.cve_cache = {}
        else:
            # Initialize with sample CVEs for demonstration
            self.cve_cache = {
                'CVE-2021-44228': {
                    'service_name': 'log4j',
                    'version_pattern': r'log4j.*2\.(0|1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16)\.',
                    'confidence': 'HIGH'
                },
                'CVE-2021-45046': {
                    'service_name': 'log4j',
                    'version_pattern': r'log4j.*2\.(0|1|2|3|4|5|6|7|8|9|10|11|12|13|14|15)\.',
                    'confidence': 'HIGH'
                }
            }
            
            # Save to file
            with open(cve_db_file, 'w', encoding='utf-8') as f:
                json.dump(self.cve_cache, f, indent=2)
    
    def match_cves(self, service: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Match CVEs against service.
        
        Args:
            service: Service dictionary
        
        Returns:
            List of CVE match dictionaries
        """
        matches = []
        matched_at = datetime.now(timezone.utc).isoformat()
        
        service_name = service.get('service_name', '').lower()
        banner = service.get('banner', '').lower()
        
        # Match against CVE database
        for cve_id, cve_data in self.cve_cache.items():
            match_reason = None
            confidence = cve_data.get('confidence', 'LOW')
            
            # Check service name match
            if cve_data.get('service_name', '').lower() in service_name:
                match_reason = 'service_name'
            
            # Check banner version match
            if banner and cve_data.get('version_pattern'):
                pattern = cve_data.get('version_pattern', '')
                if re.search(pattern, banner, re.IGNORECASE):
                    match_reason = 'banner_version'
                    confidence = 'HIGH'
            
            # Check version string in banner
            if banner and cve_id in banner:
                match_reason = 'version_string'
                confidence = 'MEDIUM'
            
            if match_reason:
                match = {
                    'match_id': str(uuid.uuid4()),
                    'service_id': service.get('service_id', ''),
                    'cve_id': cve_id,
                    'match_reason': match_reason,
                    'confidence': confidence,
                    'matched_at': matched_at,
                    'immutable_hash': ''
                }
                
                match['immutable_hash'] = self._calculate_hash(match)
                matches.append(match)
        
        return matches
    
    def _calculate_hash(self, match: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of CVE match record."""
        hashable_content = {k: v for k, v in match.items() if k != 'immutable_hash'}
        canonical_json = json.dumps(hashable_content, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_bytes = canonical_json.encode('utf-8')
        hash_obj = hashlib.sha256(content_bytes)
        return hash_obj.hexdigest()
