#!/usr/bin/env python3
"""
RansomEye v1.0 AI Core - SHAP Explainer Module
AUTHORITATIVE: SHAP explainability for incident confidence contributions
Python 3.10+ only - aligns with Phase 6 requirements
"""

from typing import List, Dict, Any
import numpy as np


# Phase 6 requirement: SHAP explainability for confidence and evidence contributions
# Phase 6 requirement: Store references only, not raw arrays
# Phase 6 minimal: Simple SHAP-like explanation method (full SHAP library not required)


def explain_incident_confidence(incident: Dict[str, Any], 
                                feature_vector: List[float]) -> List[Dict[str, Any]]:
    """
    Generate SHAP-like explanation for incident confidence contribution.
    
    Phase 6 requirement: SHAP explanations for:
    - confidence contribution (how features contribute to confidence_score)
    - evidence contribution (how evidence_count contributes to confidence)
    
    Phase 6 requirement: Store references only, not raw arrays
    Phase 6 requirement: SHAP output is generated per run
    
    Phase 6 minimal: Simple SHAP-like explanation method (full SHAP library not required)
    In production, this would use actual SHAP (SHapley Additive exPlanations) library
    
    Deterministic properties:
    - Reproducible: Explanations are deterministic (computed from feature values)
    - No time-window dependency: Explanations depend only on incident state
    - No probabilistic logic: Contributions are deterministic functions of feature values
    
    Args:
        incident: Incident dictionary from incidents table
        feature_vector: Feature vector extracted from incident (3 features)
        
    Returns:
        List of feature contribution dictionaries:
        [{"feature": "confidence_score", "contribution": 0.123, "feature_value": 30.0}, ...]
    """
    # Phase 6 requirement: SHAP explainability (SHAP-like for Phase 6 minimal)
    # Phase 6 minimal: Simple linear contribution model (proportional to feature value)
    # In production, this would use actual SHAP values from a trained model
    
    feature_names = ['confidence_score', 'current_stage', 'total_evidence_count']
    
    # Phase 6 requirement: SHAP explanation for confidence contribution
    # Deterministic: Contributions are computed deterministically from feature values
    # For Phase 6 minimal, we use simple proportional contributions
    contributions = []
    
    for feature_name, feature_value in zip(feature_names, feature_vector):
        # Phase 6 minimal: Simple contribution model (proportional to feature value)
        # Deterministic: Contribution is deterministic function of feature value
        if feature_name == 'confidence_score':
            # Confidence score directly contributes to itself (baseline contribution)
            contribution = feature_value * 0.1  # 10% of confidence score as contribution
        elif feature_name == 'current_stage':
            # Stage contributes proportionally (SUSPICIOUS=1.0, CONFIRMED=3.0)
            # Higher stage → higher contribution
            contribution = feature_value * 15.0  # Stage contribution factor
        elif feature_name == 'total_evidence_count':
            # Evidence count contributes proportionally (more evidence → higher contribution)
            contribution = feature_value * 2.0  # Evidence contribution factor
        else:
            contribution = 0.0
        
        contributions.append({
            'feature': feature_name,
            'contribution': float(contribution),
            'feature_value': float(feature_value)
        })
    
    # Phase 6 requirement: Sort by absolute contribution (for top N extraction)
    contributions_sorted = sorted(contributions, key=lambda x: abs(x['contribution']), reverse=True)
    
    return contributions_sorted


def explain_batch(incidents: List[Dict[str, Any]], 
                  feature_vectors: List[List[float]]) -> List[List[Dict[str, Any]]]:
    """
    Generate SHAP explanations for batch of incidents.
    
    Phase 6 requirement: Batch processing (offline, non-blocking)
    Phase 6 requirement: SHAP output is generated per run
    
    Args:
        incidents: List of incident dictionaries
        feature_vectors: List of feature vectors (one per incident)
        
    Returns:
        List of SHAP explanations (one per incident)
    """
    # Phase 6 requirement: Batch SHAP explanation generation
    shap_explanations = []
    
    for incident, feature_vector in zip(incidents, feature_vectors):
        explanation = explain_incident_confidence(incident, feature_vector)
        shap_explanations.append(explanation)
    
    return shap_explanations
