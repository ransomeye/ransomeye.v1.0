#!/usr/bin/env python3
"""
RansomEye System Explanation Engine - Explainer API
AUTHORITATIVE: Single API for building and signing explanation bundles
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
_explainer_dir = Path(__file__).parent.parent
if str(_explainer_dir) not in sys.path:
    sys.path.insert(0, str(_explainer_dir))

from engine.reasoning_reconstructor import ReasoningReconstructor
from engine.explanation_builder import ExplanationBuilder
from crypto.signer import Signer


class ExplainerAPIError(Exception):
    """Base exception for explainer API errors."""
    pass


class ExplainerAPI:
    """
    Single API for building and signing explanation bundles.
    
    All operations:
    - Reconstruct reasoning (read-only from subsystems)
    - Build explanation bundles (deterministic)
    - Sign bundles (cryptographic)
    """
    
    def __init__(
        self,
        ledger_path: Path,
        private_key_path: Path,
        key_id: str,
        killchain_store_path: Path = None,
        threat_graph_path: Path = None,
        risk_store_path: Path = None
    ):
        """
        Initialize explainer API.
        
        Args:
            ledger_path: Path to audit ledger file
            private_key_path: Path to private key for signing
            key_id: Key identifier
            killchain_store_path: Path to killchain store (optional)
            threat_graph_path: Path to threat graph store (optional)
            risk_store_path: Path to risk store (optional)
        """
        self.reconstructor = ReasoningReconstructor(
            ledger_path=ledger_path,
            killchain_store_path=killchain_store_path,
            threat_graph_path=threat_graph_path,
            risk_store_path=risk_store_path
        )
        self.builder = ExplanationBuilder(self.reconstructor)
        self.signer = Signer(private_key_path, key_id)
        self.key_id = key_id
    
    def explain_incident(self, incident_id: str) -> Dict[str, Any]:
        """
        Build and sign explanation bundle for incident.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            Signed explanation bundle dictionary
        """
        # Build bundle
        bundle = self.builder.build_incident_explanation(incident_id)
        
        # Sign bundle
        signature = self.signer.sign_bundle(bundle)
        bundle['signature'] = signature
        bundle['public_key_id'] = self.key_id
        
        return bundle
    
    def explain_killchain_stage(self, killchain_event_id: str) -> Dict[str, Any]:
        """
        Build and sign explanation bundle for killchain stage advancement.
        
        Args:
            killchain_event_id: Killchain event identifier
        
        Returns:
            Signed explanation bundle dictionary
        """
        # Build bundle
        bundle = self.builder.build_killchain_stage_explanation(killchain_event_id)
        
        # Sign bundle
        signature = self.signer.sign_bundle(bundle)
        bundle['signature'] = signature
        bundle['public_key_id'] = self.key_id
        
        return bundle
    
    def explain_campaign_inference(self, campaign_id: str) -> Dict[str, Any]:
        """
        Build and sign explanation bundle for campaign inference.
        
        Args:
            campaign_id: Campaign identifier
        
        Returns:
            Signed explanation bundle dictionary
        """
        # Build bundle
        bundle = self.builder.build_campaign_inference_explanation(campaign_id)
        
        # Sign bundle
        signature = self.signer.sign_bundle(bundle)
        bundle['signature'] = signature
        bundle['public_key_id'] = self.key_id
        
        return bundle
    
    def explain_risk_score_change(self, risk_computation_id: str) -> Dict[str, Any]:
        """
        Build and sign explanation bundle for risk score change.
        
        Args:
            risk_computation_id: Risk computation identifier
        
        Returns:
            Signed explanation bundle dictionary
        """
        # Build bundle
        bundle = self.builder.build_risk_score_change_explanation(risk_computation_id)
        
        # Sign bundle
        signature = self.signer.sign_bundle(bundle)
        bundle['signature'] = signature
        bundle['public_key_id'] = self.key_id
        
        return bundle
    
    def explain_policy_recommendation(self, policy_decision_id: str) -> Dict[str, Any]:
        """
        Build and sign explanation bundle for policy recommendation.
        
        Args:
            policy_decision_id: Policy decision identifier
        
        Returns:
            Signed explanation bundle dictionary
        """
        # Build bundle
        bundle = self.builder.build_policy_recommendation_explanation(policy_decision_id)
        
        # Sign bundle
        signature = self.signer.sign_bundle(bundle)
        bundle['signature'] = signature
        bundle['public_key_id'] = self.key_id
        
        return bundle
