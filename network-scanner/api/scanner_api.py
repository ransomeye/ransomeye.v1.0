#!/usr/bin/env python3
"""
RansomEye Network Scanner - Scanner API
AUTHORITATIVE: Single API for network scanning with audit ledger integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

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

# Import scanner components
_scanner_dir = Path(__file__).parent.parent
if str(_scanner_dir) not in sys.path:
    sys.path.insert(0, str(_scanner_dir))

_active_scanner_spec = importlib.util.spec_from_file_location("active_scanner", _scanner_dir / "engine" / "active_scanner.py")
_active_scanner_module = importlib.util.module_from_spec(_active_scanner_spec)
_active_scanner_spec.loader.exec_module(_active_scanner_module)
ActiveScanner = _active_scanner_module.ActiveScanner

_passive_discoverer_spec = importlib.util.spec_from_file_location("passive_discoverer", _scanner_dir / "engine" / "passive_discoverer.py")
_passive_discoverer_module = importlib.util.module_from_spec(_passive_discoverer_spec)
_passive_discoverer_spec.loader.exec_module(_passive_discoverer_module)
PassiveDiscoverer = _passive_discoverer_module.PassiveDiscoverer

_topology_builder_spec = importlib.util.spec_from_file_location("topology_builder", _scanner_dir / "engine" / "topology_builder.py")
_topology_builder_module = importlib.util.module_from_spec(_topology_builder_spec)
_topology_builder_spec.loader.exec_module(_topology_builder_module)
TopologyBuilder = _topology_builder_module.TopologyBuilder

_cve_matcher_spec = importlib.util.spec_from_file_location("cve_matcher", _scanner_dir / "engine" / "cve_matcher.py")
_cve_matcher_module = importlib.util.module_from_spec(_cve_matcher_spec)
_cve_matcher_spec.loader.exec_module(_cve_matcher_module)
CVEMatcher = _cve_matcher_module.CVEMatcher


class ScannerAPIError(Exception):
    """Base exception for scanner API errors."""
    pass


class ScannerAPI:
    """
    Single API for network scanning operations.
    
    All operations:
    - Active scanning (bounded, explicit)
    - Passive discovery (DPI/flow-based)
    - Topology building (immutable graph)
    - CVE matching (offline NVD snapshot)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        assets_store_path: Path,
        services_store_path: Path,
        topology_store_path: Path,
        cve_matches_store_path: Path,
        cve_db_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path,
        rate_limit: int = 100
    ):
        """
        Initialize scanner API.
        
        Args:
            assets_store_path: Path to assets store
            services_store_path: Path to services store
            topology_store_path: Path to topology edges store
            cve_matches_store_path: Path to CVE matches store
            cve_db_path: Path to CVE database directory
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
            rate_limit: Rate limit for active scanning
        """
        self.active_scanner = ActiveScanner(rate_limit=rate_limit)
        self.passive_discoverer = PassiveDiscoverer()
        self.topology_builder = TopologyBuilder()
        self.cve_matcher = CVEMatcher(cve_db_path)
        
        self.assets_store_path = Path(assets_store_path)
        self.assets_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.services_store_path = Path(services_store_path)
        self.services_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.topology_store_path = Path(topology_store_path)
        self.topology_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.cve_matches_store_path = Path(cve_matches_store_path)
        self.cve_matches_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise ScannerAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def scan_network(
        self,
        scan_scope: str,
        ports: Optional[List[int]] = None,
        scan_type: str = 'syn'
    ) -> Dict[str, Any]:
        """
        Perform active network scan.
        
        Args:
            scan_scope: Scan scope (CIDR notation)
            ports: List of ports to scan
            scan_type: Scan type (syn, connect, udp)
        
        Returns:
            Dictionary with assets and services
        """
        # Emit scan start audit entry
        try:
            scan_start_entry = self.ledger_writer.create_entry(
                component='network-scanner',
                component_instance_id='network-scanner',
                action_type='scan_started',
                subject={'type': 'scan', 'scope': scan_scope},
                actor={'type': 'system', 'identifier': 'network-scanner'},
                payload={
                    'scan_scope': scan_scope,
                    'ports': ports or [],
                    'scan_type': scan_type
                }
            )
        except Exception as e:
            raise ScannerAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        # Perform scan
        try:
            assets = self.active_scanner.scan_network(scan_scope, ports, scan_type)
            
            # Store assets
            for asset in assets:
                self._store_asset(asset)
            
            # Emit scan completion audit entry
            try:
                self.ledger_writer.create_entry(
                    component='network-scanner',
                    component_instance_id='network-scanner',
                    action_type='scan_completed',
                    subject={'type': 'scan', 'scope': scan_scope},
                    actor={'type': 'system', 'identifier': 'network-scanner'},
                    payload={
                        'scan_scope': scan_scope,
                        'assets_discovered': len(assets)
                    }
                )
            except Exception as e:
                raise ScannerAPIError(f"Failed to emit audit ledger entry: {e}") from e
            
            return {
                'assets': assets,
                'services': []  # Services would be discovered during scan
            }
        except Exception as e:
            # Emit scan failure audit entry
            try:
                self.ledger_writer.create_entry(
                    component='network-scanner',
                    component_instance_id='network-scanner',
                    action_type='scan_failed',
                    subject={'type': 'scan', 'scope': scan_scope},
                    actor={'type': 'system', 'identifier': 'network-scanner'},
                    payload={
                        'scan_scope': scan_scope,
                        'error': str(e)
                    }
                )
            except Exception:
                pass
            raise ScannerAPIError(f"Scan failed: {e}") from e
    
    def discover_passive(
        self,
        dpi_data: Optional[List[Dict[str, Any]]] = None,
        flow_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform passive discovery.
        
        Args:
            dpi_data: DPI probe output data
            flow_data: Flow metadata
        
        Returns:
            List of discovered assets
        """
        assets = []
        
        if dpi_data:
            dpi_assets = self.passive_discoverer.discover_from_dpi(dpi_data)
            assets.extend(dpi_assets)
        
        if flow_data:
            flow_assets = self.passive_discoverer.discover_from_flow(flow_data)
            assets.extend(flow_assets)
        
        # Store assets
        for asset in assets:
            self._store_asset(asset)
        
        # Emit discovery audit entry
        try:
            self.ledger_writer.create_entry(
                component='network-scanner',
                component_instance_id='network-scanner',
                action_type='passive_discovery_completed',
                subject={'type': 'discovery'},
                actor={'type': 'system', 'identifier': 'network-scanner'},
                payload={
                    'assets_discovered': len(assets)
                }
            )
        except Exception as e:
            raise ScannerAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return assets
    
    def build_topology(
        self,
        assets: List[Dict[str, Any]],
        services: List[Dict[str, Any]],
        communication_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Build topology graph.
        
        Args:
            assets: List of asset dictionaries
            services: List of service dictionaries
            communication_data: Communication data for edge building
        
        Returns:
            List of topology edge dictionaries
        """
        edges = []
        
        # Build asset-to-service edges
        asset_service_edges = self.topology_builder.build_edges_from_assets(assets, services)
        edges.extend(asset_service_edges)
        
        # Build communication edges
        if communication_data:
            asset_map = {asset['ip_address']: asset['asset_id'] for asset in assets}
            comm_edges = self.topology_builder.build_edges_from_communication(communication_data, asset_map)
            edges.extend(comm_edges)
        
        # Store edges
        for edge in edges:
            self._store_topology_edge(edge)
        
        # Emit topology build audit entry
        try:
            self.ledger_writer.create_entry(
                component='network-scanner',
                component_instance_id='network-scanner',
                action_type='topology_built',
                subject={'type': 'topology'},
                actor={'type': 'system', 'identifier': 'network-scanner'},
                payload={
                    'edges_count': len(edges)
                }
            )
        except Exception as e:
            raise ScannerAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return edges
    
    def match_cves(self, services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match CVEs against services.
        
        Args:
            services: List of service dictionaries
        
        Returns:
            List of CVE match dictionaries
        """
        all_matches = []
        
        for service in services:
            matches = self.cve_matcher.match_cves(service)
            all_matches.extend(matches)
            
            # Store matches
            for match in matches:
                self._store_cve_match(match)
        
        # Emit CVE matching audit entry
        try:
            self.ledger_writer.create_entry(
                component='network-scanner',
                component_instance_id='network-scanner',
                action_type='cve_matching_completed',
                subject={'type': 'cve_matching'},
                actor={'type': 'system', 'identifier': 'network-scanner'},
                payload={
                    'matches_count': len(all_matches)
                }
            )
        except Exception as e:
            raise ScannerAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return all_matches
    
    def _store_asset(self, asset: Dict[str, Any]) -> None:
        """Store asset to file-based store."""
        try:
            asset_json = json.dumps(asset, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.assets_store_path, 'a', encoding='utf-8') as f:
                f.write(asset_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise ScannerAPIError(f"Failed to store asset: {e}") from e
    
    def _store_topology_edge(self, edge: Dict[str, Any]) -> None:
        """Store topology edge to file-based store."""
        try:
            edge_json = json.dumps(edge, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.topology_store_path, 'a', encoding='utf-8') as f:
                f.write(edge_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise ScannerAPIError(f"Failed to store topology edge: {e}") from e
    
    def _store_cve_match(self, match: Dict[str, Any]) -> None:
        """Store CVE match to file-based store."""
        try:
            match_json = json.dumps(match, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.cve_matches_store_path, 'a', encoding='utf-8') as f:
                f.write(match_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise ScannerAPIError(f"Failed to store CVE match: {e}") from e
