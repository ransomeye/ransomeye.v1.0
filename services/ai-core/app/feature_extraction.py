#!/usr/bin/env python3
"""
RansomEye v1.0 AI Core - Feature Extraction Module
AUTHORITATIVE: Deterministic feature extraction from incidents
Python 3.10+ only - aligns with Phase 6 requirements
"""

from typing import List, Dict, Any
import numpy as np


# Phase 6 requirement: Feature extraction is deterministic (no probabilistic logic)


def extract_incident_features(incident: Dict[str, Any]) -> List[float]:
    """
    Extract numeric features from incident.
    
    Phase 6 requirement: Feature extraction from:
    - incident confidence (confidence_score)
    - incident stage (current_stage) - encoded as numeric
    - evidence count (total_evidence_count)
    
    Deterministic properties:
    - No probabilistic logic: All features are deterministic functions of incident data
    - No time-window dependency: Features depend only on incident state
    - No heuristics: Explicit feature extraction rules only
    
    Args:
        incident: Incident dictionary from incidents table
        
    Returns:
        List of numeric features (deterministic)
    """
    # Phase 6 requirement: Extract features from incident confidence
    confidence_score = float(incident.get('confidence_score', 0.0))
    
    # Phase 6 requirement: Extract features from incident stage (encoded as numeric)
    # Deterministic: Stage enum encoded as numeric (CLEAN=0, SUSPICIOUS=1, PROBABLE=2, CONFIRMED=3)
    stage_map = {
        'CLEAN': 0.0,
        'SUSPICIOUS': 1.0,
        'PROBABLE': 2.0,
        'CONFIRMED': 3.0
    }
    current_stage = incident.get('current_stage', 'CLEAN')
    stage_numeric = stage_map.get(current_stage, 0.0)
    
    # Phase 6 requirement: Extract features from evidence count
    total_evidence_count = float(incident.get('total_evidence_count', 0))
    
    # Phase 6 requirement: Feature vector is deterministic
    # Deterministic: Features are direct mappings from incident data
    feature_vector = [
        confidence_score,      # Feature 0: confidence_score (0.0 to 100.0)
        stage_numeric,         # Feature 1: current_stage (0.0 to 3.0)
        total_evidence_count   # Feature 2: total_evidence_count (0.0 to inf)
    ]
    
    return feature_vector


def extract_features_batch(incidents: List[Dict[str, Any]]) -> np.ndarray:
    """
    Extract features from batch of incidents.
    
    Phase 6 requirement: Batch processing (offline, non-blocking)
    Deterministic: Features are deterministic functions of incident data
    
    Args:
        incidents: List of incident dictionaries from incidents table
        
    Returns:
        NumPy array of feature vectors (shape: [n_incidents, n_features])
    """
    # Phase 6 requirement: Batch feature extraction (deterministic)
    feature_vectors = [extract_incident_features(incident) for incident in incidents]
    
    # Convert to NumPy array for scikit-learn compatibility
    return np.array(feature_vectors)
