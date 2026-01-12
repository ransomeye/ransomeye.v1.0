#!/usr/bin/env python3
"""
RansomEye KillChain & Forensics - Forensics API
AUTHORITATIVE: Single API for timeline reconstruction and evidence management with audit ledger integration
"""

import sys
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

# Import forensics components
_forensics_dir = Path(__file__).parent.parent
if str(_forensics_dir) not in sys.path:
    sys.path.insert(0, str(_forensics_dir))

_timeline_builder_spec = importlib.util.spec_from_file_location("timeline_builder", _forensics_dir / "engine" / "timeline_builder.py")
_timeline_builder_module = importlib.util.module_from_spec(_timeline_builder_spec)
_timeline_builder_spec.loader.exec_module(_timeline_builder_module)
TimelineBuilder = _timeline_builder_module.TimelineBuilder

_mitre_mapper_spec = importlib.util.spec_from_file_location("mitre_mapper", _forensics_dir / "engine" / "mitre_mapper.py")
_mitre_mapper_module = importlib.util.module_from_spec(_mitre_mapper_spec)
_mitre_mapper_spec.loader.exec_module(_mitre_mapper_module)
MITREMapper = _mitre_mapper_module.MITREMapper

_campaign_stitcher_spec = importlib.util.spec_from_file_location("campaign_stitcher", _forensics_dir / "engine" / "campaign_stitcher.py")
_campaign_stitcher_module = importlib.util.module_from_spec(_campaign_stitcher_spec)
_campaign_stitcher_spec.loader.exec_module(_campaign_stitcher_module)
CampaignStitcher = _campaign_stitcher_module.CampaignStitcher

_artifact_store_spec = importlib.util.spec_from_file_location("artifact_store", _forensics_dir / "evidence" / "artifact_store.py")
_artifact_store_module = importlib.util.module_from_spec(_artifact_store_spec)
_artifact_store_spec.loader.exec_module(_artifact_store_module)
ArtifactStore = _artifact_store_module.ArtifactStore

_hasher_spec = importlib.util.spec_from_file_location("hasher", _forensics_dir / "evidence" / "hasher.py")
_hasher_module = importlib.util.module_from_spec(_hasher_spec)
_hasher_spec.loader.exec_module(_hasher_module)
Hasher = _hasher_module.Hasher


class ForensicsAPIError(Exception):
    """Base exception for forensics API errors."""
    pass


class ForensicsAPI:
    """
    Single API for timeline reconstruction and evidence management.
    
    All operations:
    - Reconstruct timelines (immutable)
    - Manage evidence (chain-of-custody)
    - Correlate campaigns (deterministic)
    - Emit audit ledger entries (no silent reads)
    """
    
    def __init__(
        self,
        artifact_store_path: Path,
        artifact_storage_root: Path,
        ledger_path: Path,
        ledger_key_dir: Path
    ):
        """
        Initialize forensics API.
        
        Args:
            artifact_store_path: Path to evidence index file
            artifact_storage_root: Root directory for evidence storage
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
        """
        self.artifact_store = ArtifactStore(artifact_store_path, artifact_storage_root)
        self.timeline_builder = TimelineBuilder()
        self.mitre_mapper = MITREMapper()
        self.campaign_stitcher = CampaignStitcher()
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise ForensicsAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def register_evidence(
        self,
        artifact_path: Path,
        evidence_type: str,
        registered_by: str
    ) -> Dict[str, Any]:
        """
        Register evidence artifact.
        
        Process:
        1. Calculate artifact hash
        2. Get artifact size
        3. Register in artifact store
        4. Emit audit ledger entry
        
        Args:
            artifact_path: Path to evidence artifact
            evidence_type: Type of evidence (memory_dump, disk_artifact, etc.)
            registered_by: Entity that registered evidence
        
        Returns:
            Evidence record dictionary
        """
        # Calculate hash
        artifact_hash = Hasher.calculate_sha256(artifact_path)
        artifact_size = artifact_path.stat().st_size
        
        # Register in store
        evidence_record = self.artifact_store.register_artifact(
            artifact_path=artifact_path,
            evidence_type=evidence_type,
            artifact_hash=artifact_hash,
            artifact_size=artifact_size,
            compression_applied=False
        )
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='killchain-forensics',
                component_instance_id='forensics-engine',
                action_type='forensic_artifact_access',
                subject={'type': 'forensic_artifact', 'id': evidence_record['evidence_id']},
                actor={'type': 'user', 'identifier': registered_by},
                payload={
                    'evidence_type': evidence_type,
                    'artifact_path': str(artifact_path),
                    'artifact_hash': artifact_hash,
                    'action': 'register'
                }
            )
        except Exception as e:
            raise ForensicsAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return evidence_record
    
    def access_evidence(
        self,
        evidence_id: str,
        accessed_by: str,
        access_type: str
    ) -> Dict[str, Any]:
        """
        Access evidence artifact (with chain-of-custody logging).
        
        Process:
        1. Find evidence record
        2. Log access to artifact store
        3. Emit audit ledger entry
        4. Return evidence record
        
        Args:
            evidence_id: Evidence identifier
            accessed_by: Entity that accessed evidence
            access_type: Type of access (read, verify, export)
        
        Returns:
            Evidence record dictionary
        
        Raises:
            ForensicsAPIError: If access fails
        """
        # Find evidence
        evidence_record = self.artifact_store.find_by_id(evidence_id)
        if not evidence_record:
            raise ForensicsAPIError(f"Evidence not found: {evidence_id}")
        
        # Emit audit ledger entry first (no silent reads)
        try:
            ledger_entry = self.ledger_writer.create_entry(
                component='killchain-forensics',
                component_instance_id='forensics-engine',
                action_type='forensic_artifact_access',
                subject={'type': 'forensic_artifact', 'id': evidence_id},
                actor={'type': 'user', 'identifier': accessed_by},
                payload={
                    'evidence_type': evidence_record.get('evidence_type'),
                    'access_type': access_type,
                    'action': 'access'
                }
            )
            ledger_entry_id = ledger_entry.get('ledger_entry_id', '')
        except Exception as e:
            raise ForensicsAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        # Log access to artifact store
        try:
            self.artifact_store.log_access(
                evidence_id=evidence_id,
                accessed_by=accessed_by,
                access_type=access_type,
                ledger_entry_id=ledger_entry_id
            )
        except Exception as e:
            raise ForensicsAPIError(f"Failed to log access: {e}") from e
        
        return evidence_record
    
    def verify_evidence_integrity(
        self,
        evidence_id: str,
        verified_by: str
    ) -> bool:
        """
        Verify evidence artifact integrity.
        
        Process:
        1. Find evidence record
        2. Verify hash matches
        3. Update integrity flag
        4. Emit audit ledger entry
        
        Args:
            evidence_id: Evidence identifier
            verified_by: Entity that verified integrity
        
        Returns:
            True if integrity verified
        
        Raises:
            ForensicsAPIError: If verification fails
        """
        # Verify integrity
        try:
            self.artifact_store.verify_integrity(evidence_id)
        except Exception as e:
            raise ForensicsAPIError(f"Integrity verification failed: {e}") from e
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='killchain-forensics',
                component_instance_id='forensics-engine',
                action_type='forensic_artifact_access',
                subject={'type': 'forensic_artifact', 'id': evidence_id},
                actor={'type': 'user', 'identifier': verified_by},
                payload={
                    'access_type': 'verify',
                    'action': 'integrity_verification',
                    'result': 'verified'
                }
            )
        except Exception as e:
            raise ForensicsAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return True
    
    def reconstruct_timeline(
        self,
        source_events: List[Dict[str, Any]],
        reconstructed_by: str
    ) -> Dict[str, Any]:
        """
        Reconstruct killchain timeline from source events.
        
        Process:
        1. Map events to MITRE ATT&CK techniques
        2. Correlate events into campaigns
        3. Build ordered timeline
        4. Emit audit ledger entry
        
        Args:
            source_events: List of source events (read-only, no mutation)
            reconstructed_by: Entity that reconstructed timeline
        
        Returns:
            Timeline reconstruction result dictionary
        """
        # Process each event
        for source_event in source_events:
            # Map to MITRE ATT&CK
            try:
                mitre_mapping = self.mitre_mapper.map_event(source_event)
            except Exception as e:
                raise ForensicsAPIError(f"MITRE mapping failed: {e}") from e
            
            # Extract correlation metadata
            correlation_metadata = {
                'ip_addresses': source_event.get('ip_addresses', []),
                'malware_families': source_event.get('malware_families', []),
                'indicators': source_event.get('indicators', [])
            }
            
            # Link to campaign
            campaign_id = self.campaign_stitcher.link_event(source_event, correlation_metadata)
            
            # Get evidence references (if any)
            evidence_references = source_event.get('evidence_references', [])
            
            # Add to timeline
            self.timeline_builder.add_event(
                source_event=source_event,
                mitre_mapping=mitre_mapping,
                evidence_references=evidence_references,
                campaign_id=campaign_id,
                correlation_metadata=correlation_metadata
            )
        
        # Build timeline
        timeline = self.timeline_builder.build_timeline()
        
        # Detect stage transitions
        transitions = self.timeline_builder.detect_stage_transitions()
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='killchain-forensics',
                component_instance_id='forensics-engine',
                action_type='forensic_timeline_reconstructed',
                subject={'type': 'timeline', 'id': str(uuid.uuid4())},
                actor={'type': 'user', 'identifier': reconstructed_by},
                payload={
                    'events_processed': len(source_events),
                    'timeline_events': len(timeline),
                    'stage_transitions': len(transitions),
                    'campaigns': len(self.campaign_stitcher.get_all_campaigns())
                }
            )
        except Exception as e:
            raise ForensicsAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return {
            'timeline': timeline,
            'stage_transitions': transitions,
            'campaigns': self.campaign_stitcher.get_all_campaigns()
        }
    
    def get_timeline_by_campaign(self, campaign_id: str) -> List[Dict[str, Any]]:
        """
        Get timeline events for specific campaign.
        
        Args:
            campaign_id: Campaign identifier
        
        Returns:
            List of killchain events
        """
        return self.timeline_builder.get_timeline_by_campaign(campaign_id)
    
    def get_timeline_by_stage(self, stage: str) -> List[Dict[str, Any]]:
        """
        Get timeline events for specific MITRE stage.
        
        Args:
            stage: MITRE stage (e.g., 'execution', 'persistence')
        
        Returns:
            List of killchain events
        """
        return self.timeline_builder.get_timeline_by_stage(stage)
