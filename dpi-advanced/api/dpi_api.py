#!/usr/bin/env python3
"""
RansomEye DPI Advanced - DPI API
AUTHORITATIVE: Single API for DPI operations with audit ledger integration
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

# Import DPI components
_dpi_dir = Path(__file__).parent.parent
if str(_dpi_dir) not in sys.path:
    sys.path.insert(0, str(_dpi_dir))

_flow_assembler_spec = importlib.util.spec_from_file_location("flow_assembler", _dpi_dir / "engine" / "flow_assembler.py")
_flow_assembler_module = importlib.util.module_from_spec(_flow_assembler_spec)
_flow_assembler_spec.loader.exec_module(_flow_assembler_module)
FlowAssembler = _flow_assembler_module.FlowAssembler

_behavior_model_spec = importlib.util.spec_from_file_location("behavior_model", _dpi_dir / "engine" / "behavior_model.py")
_behavior_model_module = importlib.util.module_from_spec(_behavior_model_spec)
_behavior_model_spec.loader.exec_module(_behavior_model_module)
BehaviorModel = _behavior_model_module.BehaviorModel

_asset_classifier_spec = importlib.util.spec_from_file_location("asset_classifier", _dpi_dir / "engine" / "asset_classifier.py")
_asset_classifier_module = importlib.util.module_from_spec(_asset_classifier_spec)
_asset_classifier_spec.loader.exec_module(_asset_classifier_module)
AssetClassifier = _asset_classifier_module.AssetClassifier

_privacy_redactor_spec = importlib.util.spec_from_file_location("privacy_redactor", _dpi_dir / "engine" / "privacy_redactor.py")
_privacy_redactor_module = importlib.util.module_from_spec(_privacy_redactor_spec)
_privacy_redactor_spec.loader.exec_module(_privacy_redactor_module)
PrivacyRedactor = _privacy_redactor_module.PrivacyRedactor

_uploader_spec = importlib.util.spec_from_file_location("uploader", _dpi_dir / "engine" / "uploader.py")
_uploader_module = importlib.util.module_from_spec(_uploader_spec)
_uploader_spec.loader.exec_module(_uploader_module)
Uploader = _uploader_module.Uploader


class DPIAPIError(Exception):
    """Base exception for DPI API errors."""
    pass


class DPIAPI:
    """
    Single API for DPI operations.
    
    All operations:
    - Process packets (flow assembly)
    - Analyze flows (behavioral modeling)
    - Classify assets (device type and role)
    - Redact flows (privacy-preserving)
    - Upload chunks (cryptographically enforced)
    - Emit audit ledger entries (every operation)
    """
    
    def __init__(
        self,
        flows_store_path: Path,
        asset_profiles_store_path: Path,
        upload_chunks_store_path: Path,
        privacy_policy: Dict[str, Any],
        ledger_path: Path,
        ledger_key_dir: Path,
        flow_timeout: int = 300,
        chunk_size: int = 1000
    ):
        """
        Initialize DPI API.
        
        Args:
            flows_store_path: Path to flows store
            asset_profiles_store_path: Path to asset profiles store
            upload_chunks_store_path: Path to upload chunks store
            privacy_policy: Privacy policy dictionary
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
            flow_timeout: Flow timeout in seconds
            chunk_size: Chunk size for uploads
        """
        self.flow_assembler = FlowAssembler(flow_timeout=flow_timeout)
        self.behavior_model = BehaviorModel()
        self.asset_classifier = AssetClassifier()
        self.privacy_redactor = PrivacyRedactor(privacy_policy)
        self.uploader = Uploader(chunk_size=chunk_size)
        
        self.flows_store_path = Path(flows_store_path)
        self.flows_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.asset_profiles_store_path = Path(asset_profiles_store_path)
        self.asset_profiles_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.upload_chunks_store_path = Path(upload_chunks_store_path)
        self.upload_chunks_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise DPIAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def process_packet(
        self,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        protocol: str,
        packet_size: int,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Process packet and update flow.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            src_port: Source port
            dst_port: Destination port
            protocol: Protocol (tcp, udp, icmp, other)
            packet_size: Packet size in bytes
            timestamp: Packet timestamp
        
        Returns:
            Completed flow dictionary, or None if flow is still active
        """
        # Process packet
        completed_flow = self.flow_assembler.process_packet(
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
            packet_size=packet_size,
            timestamp=timestamp
        )
        
        if not completed_flow:
            return None
        
        # Analyze flow behavior
        behavior_profile = self.behavior_model.analyze_flow(completed_flow)
        completed_flow['behavioral_profile_id'] = behavior_profile.get('profile_id', '')
        
        # Redact flow (privacy-preserving)
        redacted_flow = self.privacy_redactor.redact_flow(completed_flow)
        
        # Store flow
        self._store_flow(redacted_flow)
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='dpi-advanced',
                component_instance_id='dpi-advanced',
                action_type='flow_completed',
                subject={'type': 'flow', 'id': redacted_flow.get('flow_id', '')},
                actor={'type': 'system', 'identifier': 'dpi-advanced'},
                payload={
                    'flow_id': redacted_flow.get('flow_id', ''),
                    'packet_count': redacted_flow.get('packet_count', 0),
                    'byte_count': redacted_flow.get('byte_count', 0)
                }
            )
        except Exception as e:
            raise DPIAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return redacted_flow
    
    def classify_asset(
        self,
        asset_ip: str,
        flows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Classify asset based on flows.
        
        Args:
            asset_ip: Asset IP address
            flows: List of flows involving this asset
        
        Returns:
            Asset profile dictionary
        """
        # Classify asset
        profile = self.asset_classifier.classify_asset(asset_ip, flows)
        
        # Store profile
        self._store_asset_profile(profile)
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='dpi-advanced',
                component_instance_id='dpi-advanced',
                action_type='asset_classified',
                subject={'type': 'asset', 'ip': asset_ip},
                actor={'type': 'system', 'identifier': 'dpi-advanced'},
                payload={
                    'profile_id': profile.get('profile_id', ''),
                    'device_type': profile.get('device_type', ''),
                    'role': profile.get('role', '')
                }
            )
        except Exception as e:
            raise DPIAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return profile
    
    def upload_flows(
        self,
        flows: List[Dict[str, Any]],
        private_key: bytes,
        key_id: str
    ) -> List[Dict[str, Any]]:
        """
        Upload flows in chunks.
        
        Args:
            flows: List of flow records
            private_key: Ed25519 private key for signing
            key_id: Key identifier
        
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        total_chunks = (len(flows) + self.uploader.chunk_size - 1) // self.uploader.chunk_size
        
        for i in range(0, len(flows), self.uploader.chunk_size):
            chunk_flows = flows[i:i + self.uploader.chunk_size]
            chunk_index = i // self.uploader.chunk_size
            
            # Create chunk
            chunk = self.uploader.create_chunk(
                flow_records=chunk_flows,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                private_key=private_key,
                key_id=key_id
            )
            
            # Buffer chunk
            self.uploader.buffer_chunk(chunk)
            
            # Store chunk
            self._store_upload_chunk(chunk)
            
            chunks.append(chunk)
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='dpi-advanced',
                component_instance_id='dpi-advanced',
                action_type='flows_uploaded',
                subject={'type': 'upload'},
                actor={'type': 'system', 'identifier': 'dpi-advanced'},
                payload={
                    'chunks_count': len(chunks),
                    'flows_count': len(flows)
                }
            )
        except Exception as e:
            raise DPIAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return chunks
    
    def _store_flow(self, flow: Dict[str, Any]) -> None:
        """Store flow to file-based store."""
        try:
            flow_json = json.dumps(flow, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.flows_store_path, 'a', encoding='utf-8') as f:
                f.write(flow_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise DPIAPIError(f"Failed to store flow: {e}") from e
    
    def _store_asset_profile(self, profile: Dict[str, Any]) -> None:
        """Store asset profile to file-based store."""
        try:
            profile_json = json.dumps(profile, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.asset_profiles_store_path, 'a', encoding='utf-8') as f:
                f.write(profile_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise DPIAPIError(f"Failed to store asset profile: {e}") from e
    
    def _store_upload_chunk(self, chunk: Dict[str, Any]) -> None:
        """Store upload chunk to file-based store."""
        try:
            chunk_json = json.dumps(chunk, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            with open(self.upload_chunks_store_path, 'a', encoding='utf-8') as f:
                f.write(chunk_json)
                f.write('\n')
                f.flush()
                import os
                os.fsync(f.fileno())
        except Exception as e:
            raise DPIAPIError(f"Failed to store upload chunk: {e}") from e
