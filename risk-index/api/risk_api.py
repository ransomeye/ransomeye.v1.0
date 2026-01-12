#!/usr/bin/env python3
"""
RansomEye Enterprise Risk Index - Risk Computation API
AUTHORITATIVE: Single API for risk score computation with audit ledger integration
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

# Import risk index components
_risk_index_dir = Path(__file__).parent.parent
if str(_risk_index_dir) not in sys.path:
    sys.path.insert(0, str(_risk_index_dir))

_aggregator_spec = importlib.util.spec_from_file_location("aggregator", _risk_index_dir / "engine" / "aggregator.py")
_aggregator_module = importlib.util.module_from_spec(_aggregator_spec)
_aggregator_spec.loader.exec_module(_aggregator_module)
Aggregator = _aggregator_module.Aggregator

_normalizer_spec = importlib.util.spec_from_file_location("normalizer", _risk_index_dir / "engine" / "normalizer.py")
_normalizer_module = importlib.util.module_from_spec(_normalizer_spec)
_normalizer_spec.loader.exec_module(_normalizer_module)
Normalizer = _normalizer_module.Normalizer

_store_spec = importlib.util.spec_from_file_location("risk_store", _risk_index_dir / "storage" / "risk_store.py")
_store_module = importlib.util.module_from_spec(_store_spec)
_store_spec.loader.exec_module(_store_module)
RiskStore = _store_module.RiskStore


class RiskAPIError(Exception):
    """Base exception for risk API errors."""
    pass


class RiskAPI:
    """
    Single API for risk score computation.
    
    All operations:
    - Ingest signals (read-only, no mutation)
    - Compute deterministic risk score
    - Store historical record (immutable)
    - Emit audit ledger entry
    """
    
    COMPUTATION_VERSION = "1.0.0"
    
    def __init__(
        self,
        store_path: Path,
        ledger_path: Path,
        ledger_key_dir: Path,
        weights: Optional[Dict[str, float]] = None,
        decay_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize risk API.
        
        Args:
            store_path: Path to risk score store file
            ledger_path: Path to audit ledger file
            ledger_key_dir: Directory containing ledger signing keys
            weights: Optional component weights (default: equal weights)
            decay_config: Optional temporal decay configuration
        """
        self.store = RiskStore(store_path)
        
        # Default weights (equal distribution)
        if weights is None:
            weights = {
                'incidents': 0.3,
                'ai_metadata': 0.3,
                'policy_decisions': 0.2,
                'threat_correlation': 0.1,
                'uba': 0.1
            }
        
        self.aggregator = Aggregator(weights, decay_config)
        
        # Initialize audit ledger
        try:
            ledger_store = AppendOnlyStore(ledger_path, read_only=False)
            ledger_key_manager = KeyManager(ledger_key_dir)
            ledger_private_key, ledger_public_key, ledger_key_id = ledger_key_manager.get_or_create_keypair()
            ledger_signer = Signer(ledger_private_key, ledger_key_id)
            self.ledger_writer = LedgerWriter(ledger_store, ledger_signer)
        except Exception as e:
            raise RiskAPIError(f"Failed to initialize audit ledger: {e}") from e
    
    def compute_risk(
        self,
        incidents: List[Dict[str, Any]],
        ai_metadata: List[Dict[str, Any]],
        policy_decisions: List[Dict[str, Any]],
        threat_correlation: Optional[List[Dict[str, Any]]] = None,
        uba: Optional[List[Dict[str, Any]]] = None,
        computed_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Compute enterprise risk score.
        
        Process:
        1. Ingest signals (read-only, no mutation)
        2. Aggregate risk scores
        3. Normalize to 0-100
        4. Store historical record
        5. Emit audit ledger entry
        
        Args:
            incidents: List of incident signals (read-only)
            ai_metadata: List of AI metadata signals (read-only)
            policy_decisions: List of policy decision signals (read-only)
            threat_correlation: Optional threat correlation signals (read-only, future)
            uba: Optional UBA signals (read-only, future)
            computed_by: Entity that computed risk score
        
        Returns:
            Complete risk score record dictionary
        """
        current_timestamp = datetime.now(timezone.utc)
        
        # Aggregate risk signals
        aggregation_result = self.aggregator.aggregate(
            incidents=incidents,
            ai_metadata=ai_metadata,
            policy_decisions=policy_decisions,
            threat_correlation=threat_correlation or [],
            uba=uba or [],
            current_timestamp=current_timestamp
        )
        
        # Determine severity band
        severity_band = Normalizer.determine_severity_band(aggregation_result['risk_score'])
        
        # Extract signal source IDs (read-only references)
        signal_sources = {
            'incident_ids': [inc.get('id', '') for inc in incidents if inc.get('id')],
            'ai_metadata_ids': [meta.get('id', '') for meta in ai_metadata if meta.get('id')],
            'policy_decision_ids': [dec.get('id', '') for dec in policy_decisions if dec.get('id')],
            'threat_correlation_ids': [threat.get('id', '') for threat in (threat_correlation or []) if threat.get('id')],
            'uba_ids': [uba_item.get('id', '') for uba_item in (uba or []) if uba_item.get('id')]
        }
        
        # Determine decay metadata
        decay_applied = {
            'decay_function': self.aggregator.decay_config.get('function', 'none'),
            'decay_parameters': self.aggregator.decay_config.get('parameters', {})
        }
        
        # Create risk score record
        score_id = str(uuid.uuid4())
        score_record = {
            'score_id': score_id,
            'timestamp': current_timestamp.isoformat(),
            'risk_score': aggregation_result['risk_score'],
            'severity_band': severity_band,
            'component_scores': aggregation_result['component_scores'],
            'signal_sources': signal_sources,
            'computation_metadata': {
                'computation_version': self.COMPUTATION_VERSION,
                'signals_processed': len(incidents) + len(ai_metadata) + len(policy_decisions),
                'signals_missing': 0,  # For Phase B2, assume all expected signals are present
                'temporal_decay_applied': decay_applied['decay_function'] != 'none',
                'confidence_adjustment_applied': True
            },
            'confidence_score': aggregation_result['confidence_score'],
            'decay_applied': decay_applied,
            'weights_used': aggregation_result['weights_used']
        }
        
        # Store historical record (immutable)
        try:
            self.store.store_score(score_record)
        except Exception as e:
            raise RiskAPIError(f"Failed to store risk score: {e}") from e
        
        # Emit audit ledger entry
        try:
            self.ledger_writer.create_entry(
                component='risk-index',
                component_instance_id='risk-engine',
                action_type='risk_score_computed',
                subject={'type': 'risk_score', 'id': score_id},
                actor={'type': 'system', 'identifier': computed_by},
                payload={
                    'risk_score': aggregation_result['risk_score'],
                    'severity_band': severity_band,
                    'component_scores': aggregation_result['component_scores'],
                    'signals_processed': score_record['computation_metadata']['signals_processed']
                }
            )
        except Exception as e:
            raise RiskAPIError(f"Failed to emit audit ledger entry: {e}") from e
        
        return score_record
    
    def get_latest_score(self) -> Optional[Dict[str, Any]]:
        """
        Get latest risk score.
        
        Returns:
            Latest risk score record, or None if no scores exist
        """
        return self.store.get_latest()
    
    def get_score_history(
        self,
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get risk score history within timestamp range.
        
        Args:
            start_timestamp: Optional start timestamp (RFC3339)
            end_timestamp: Optional end timestamp (RFC3339)
        
        Returns:
            List of risk score records
        """
        if start_timestamp and end_timestamp:
            return list(self.store.get_by_timestamp_range(start_timestamp, end_timestamp))
        else:
            return list(self.store.read_all())
