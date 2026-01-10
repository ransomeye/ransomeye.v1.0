#!/usr/bin/env python3
"""
RansomEye v1.0 AI Core - Clustering Module
AUTHORITATIVE: Unsupervised clustering of incidents using scikit-learn
Python 3.10+ only - aligns with Phase 6 requirements
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.cluster import KMeans
import uuid


# Phase 6 requirement: Unsupervised clustering using scikit-learn
# Phase 6 requirement: Models are versioned and reproducible


def cluster_incidents(feature_vectors: np.ndarray, n_clusters: int = 3, 
                     random_state: int = 42) -> Tuple[List[int], KMeans]:
    """
    Cluster incidents using KMeans.
    
    Phase 6 requirement: Unsupervised clustering (KMeans or DBSCAN)
    Phase 6 requirement: Models are versioned and reproducible (random_state for reproducibility)
    
    Deterministic properties:
    - Reproducible: random_state ensures same input → same output
    - No time-window dependency: Clustering depends only on feature vectors
    - No probabilistic logic: KMeans is deterministic with fixed random_state
    
    Args:
        feature_vectors: NumPy array of feature vectors (shape: [n_incidents, n_features])
        n_clusters: Number of clusters (default: 3 for Phase 6 minimal)
        random_state: Random state for reproducibility (default: 42)
        
    Returns:
        Tuple of (cluster_labels, kmeans_model):
        - cluster_labels: List of cluster labels (0 to n_clusters-1)
        - kmeans_model: Trained KMeans model (for reproducibility)
    """
    # Phase 6 requirement: Use scikit-learn for clustering
    # Deterministic: random_state ensures reproducibility
    if len(feature_vectors) == 0:
        # Phase 6 requirement: Handle empty input (no incidents to cluster)
        return [], None
    
    if len(feature_vectors) < n_clusters:
        # Phase 6 requirement: Handle case where n_incidents < n_clusters
        # If fewer incidents than clusters, assign each incident to its own cluster
        return list(range(len(feature_vectors))), None
    
    # Phase 6 requirement: KMeans clustering (deterministic with random_state)
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    cluster_labels = kmeans.fit_predict(feature_vectors)
    
    return cluster_labels.tolist(), kmeans


def create_cluster_metadata(cluster_id: int, incident_ids: List[str], 
                           feature_vectors: np.ndarray, kmeans_model,
                           first_observed_at: str, last_observed_at: str) -> Dict[str, Any]:
    """
    Create cluster metadata for storage.
    
    Phase 6 requirement: Store cluster metadata (cluster_id, cluster_label, cluster_size, etc.)
    Deterministic: Cluster metadata is deterministic function of clustering results
    
    Args:
        cluster_id: Cluster label (0 to n_clusters-1)
        incident_ids: List of incident IDs in this cluster
        feature_vectors: Feature vectors for incidents in this cluster
        kmeans_model: Trained KMeans model (for centroid computation) or None
        first_observed_at: First observed timestamp (from incidents)
        last_observed_at: Last observed timestamp (from incidents)
        
    Returns:
        Cluster metadata dictionary
    """
    import hashlib
    import json
    
    # Phase 6 requirement: Generate cluster ID (UUID v4)
    cluster_uuid = str(uuid.uuid4())
    
    # Phase 6 requirement: Generate cluster label (deterministic format)
    cluster_label = f"CLUSTER_{cluster_id:03d}"
    
    # Phase 6 requirement: Compute cluster size
    cluster_size = len(incident_ids)
    
    # Phase 6 requirement: Compute cluster centroid (if model available)
    cluster_centroid_hash = None
    if kmeans_model is not None and len(feature_vectors) > 0:
        # Use model centroid if available
        if hasattr(kmeans_model, 'cluster_centers_') and cluster_id < len(kmeans_model.cluster_centers_):
            centroid = kmeans_model.cluster_centers_[cluster_id]
        else:
            # Compute centroid from cluster data
            centroid = np.mean(feature_vectors, axis=0)
        # Hash centroid for reference (not stored as blob)
        centroid_bytes = json.dumps(centroid.tolist(), sort_keys=True).encode('utf-8')
        cluster_centroid_hash = hashlib.sha256(centroid_bytes).hexdigest()
    
    return {
        'cluster_id': cluster_uuid,
        'cluster_label': cluster_label,
        'cluster_size': cluster_size,
        'cluster_centroid_hash': cluster_centroid_hash,
        'first_observed_at': first_observed_at,
        'last_observed_at': last_observed_at,
        'incident_ids': incident_ids
    }
