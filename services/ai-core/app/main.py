#!/usr/bin/env python3
"""
RansomEye v1.0 AI Core (Phase 6 - Read-Only, Non-Blocking)
AUTHORITATIVE: Minimal AI Core operating in read-only advisory mode
Python 3.10+ only - aligns with Phase 6 requirements
"""

import os
import sys
import uuid
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

# Add common utilities to path (Phase 10 requirement)
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.config import ConfigLoader, ConfigError, validate_port
    from common.logging import setup_logging
    from common.shutdown import ShutdownHandler, ExitCode, exit_config_error, exit_startup_error
    from common.resource.safety import check_file_descriptors
    _common_available = True
    _common_resource_safety_available = True
except ImportError:
    _common_available = False
    _common_resource_safety_available = False
    def check_file_descriptors(*args, **kwargs): pass
    class ConfigLoader:
        def __init__(self, name): self.config = {}; self.required_vars = []
        def require(self, *args, **kwargs): return self
        def optional(self, *args, **kwargs): return self  
        def load(self): return {}
    class ConfigError(Exception): pass
    def validate_port(p): return int(p)
    def setup_logging(name):
        class Logger:
            def info(self, m, **k): print(m)
            def error(self, m, **k): print(m, file=sys.stderr)
            def warning(self, m, **k): print(m, file=sys.stderr)
            def fatal(self, m, **k): print(f"FATAL: {m}", file=sys.stderr)
            def startup(self, m, **k): print(f"STARTUP: {m}")
            def shutdown(self, m, **k): print(f"SHUTDOWN: {m}")
            def db_error(self, m, op, **k): print(f"DB_ERROR[{op}]: {m}", file=sys.stderr)
        return Logger()
    class ShutdownHandler:
        def __init__(self, *args, **kwargs): pass
        def is_shutdown_requested(self): return False
    class ExitCode:
        SUCCESS = 0
        CONFIG_ERROR = 1
        STARTUP_ERROR = 2
        FATAL_ERROR = 4
    def exit_config_error(m): 
        print(f"CONFIG_ERROR: {m}", file=sys.stderr)
        sys.exit(1)
    def exit_startup_error(m): 
        print(f"STARTUP_ERROR: {m}", file=sys.stderr)
        sys.exit(2)

# Contract compliance: No async, no background threads (Phase 6 requirements)
# Synchronous batch processing only

from db import (get_db_connection_readonly, get_db_connection_write, get_unresolved_incidents, 
                get_model_version, store_feature_vector, store_cluster, 
                store_cluster_membership, store_shap_explanation)
from feature_extraction import extract_features_batch
from clustering import cluster_incidents, create_cluster_metadata
from shap_explainer import explain_batch

# Phase 10 requirement: Centralized configuration
if _common_available:
    config_loader = ConfigLoader('ai-core')
    config_loader.require('RANSOMEYE_DB_PASSWORD', description='Database password (security-sensitive)')
    config_loader.optional('RANSOMEYE_DB_HOST', default='localhost')
    config_loader.optional('RANSOMEYE_DB_PORT', default='5432', validator=validate_port)
    config_loader.optional('RANSOMEYE_DB_NAME', default='ransomeye')
    config_loader.optional('RANSOMEYE_DB_USER', default='ransomeye')
    try:
        config = config_loader.load()
    except ConfigError as e:
        exit_config_error(str(e))
else:
    config = {}
    if not os.getenv('RANSOMEYE_DB_PASSWORD'):
        exit_config_error('RANSOMEYE_DB_PASSWORD required')

logger = setup_logging('ai-core')
shutdown_handler = ShutdownHandler('ai-core')


def run_ai_core():
    """
    Main AI Core loop.
    
    Phase 6 requirement: Consume existing incidents, perform offline batch analysis, produce metadata only
    Phase 6 requirement: AI is read-only, non-blocking, advisory only
    Phase 6 requirement: System remains correct if AI is disabled
    
    Contract compliance:
    - Read from incidents table (read-only, does not modify)
    - Write to AI metadata tables only (feature_vectors, clusters, cluster_memberships, shap_explanations)
    - Does NOT modify incidents, evidence, or any fact tables
    """
    logger.startup("AI Core starting")
    
    # Resource safety: Check file descriptors at startup
    if _common_resource_safety_available:
        check_file_descriptors(logger)
    
    # Phase 6 requirement: No async, no background threads, no background schedulers
    # Synchronous batch processing only
    
    # Phase 10 requirement: Database connection with error handling
    # Read incidents using read-only connection
    try:
        from db import get_db_connection_readonly, get_db_connection_write
        read_conn = get_db_connection_readonly()
    except Exception as e:
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.db_error(safe_error, "connection_readonly")
        exit_startup_error(f"Failed to connect to database (read-only): {safe_error}")
    
    # Write connection for metadata (separate from read connection)
    write_conn = None
    try:
        write_conn = get_db_connection_write()
    except Exception as e:
        if read_conn:
            read_conn.close()
        # Security: Sanitize exception message before logging
        try:
            from common.security.redaction import sanitize_exception
            safe_error = sanitize_exception(e)
        except ImportError:
            safe_error = str(e)
        logger.db_error(safe_error, "connection_write")
        exit_startup_error(f"Failed to connect to database (write): {safe_error}")
    
    try:
        # Phase 6 requirement: Consume existing incidents (read-only)
        # Contract compliance: Read from incidents table (does not modify incidents)
        # Security: Validate untrusted input (incidents from database)
        try:
            incidents = get_unresolved_incidents(read_conn)
        except Exception as e:
            # Security: Sanitize exception message before logging
            try:
                from common.security.redaction import sanitize_exception
                safe_error = sanitize_exception(e)
            except ImportError:
                safe_error = str(e)
            logger.db_error(safe_error, "get_unresolved_incidents")
            raise
        
        if not incidents:
            logger.info("No unresolved incidents found for AI analysis")
            return
        
        # Security: Validate incident structures before processing
        try:
            from common.security.validation import validate_incidents_list
            incidents = validate_incidents_list(incidents)
        except ImportError:
            # Basic validation if security utilities not available
            if not isinstance(incidents, list):
                error_msg = "SECURITY VIOLATION: Incidents data is not a list"
                logger.fatal(error_msg)
                from common.shutdown import ExitCode, exit_fatal
                exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
            if len(incidents) > 10000:
                error_msg = f"SECURITY VIOLATION: Incidents list too large: {len(incidents)}"
                logger.fatal(error_msg)
                from common.shutdown import ExitCode, exit_fatal
                exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
        except SystemExit:
            # validate_incidents_list terminates Core on invalid input
            raise
        
        logger.info(f"Processing {len(incidents)} unresolved incidents", incident_count=len(incidents))
        
        # Phase 6 requirement: Get or create model versions (versioned and reproducible)
        clustering_model_version = get_model_version(write_conn, 'CLUSTERING', '1.0.0')
        explainability_model_version = get_model_version(write_conn, 'EXPLAINABILITY', '1.0.0')
        
        # Phase 6 requirement: Feature Extraction (Deterministic)
        # Extract numeric features from incidents (confidence, stage, evidence_count)
        try:
            feature_vectors = extract_features_batch(incidents)
            logger.info(f"Extracted features from {len(incidents)} incidents", feature_count=len(feature_vectors))
        except MemoryError:
            error_msg = "MEMORY ALLOCATION FAILURE: Failed to extract features from incidents"
            logger.fatal(error_msg)
            from common.shutdown import ExitCode, exit_fatal
            exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
        except Exception as e:
            # Security: Sanitize exception message before logging
            try:
                from common.security.redaction import sanitize_exception
                safe_error = sanitize_exception(e)
            except ImportError:
                safe_error = str(e)
            logger.error(f"Feature extraction failed: {safe_error}")
            raise
        
        # Store feature vectors (references only, not blobs)
        stored_features = 0
        for incident, feature_vector in zip(incidents, feature_vectors):
            try:
                store_feature_vector(conn, incident['incident_id'], clustering_model_version, 
                                   feature_vector.tolist())
                stored_features += 1
            except Exception as e:
                # Security: Sanitize exception message before logging
                try:
                    from common.security.redaction import sanitize_exception
                    safe_error = sanitize_exception(e)
                except ImportError:
                    safe_error = str(e)
                logger.db_error(safe_error, "store_feature_vector", incident_id=incident.get('incident_id'))
                conn.rollback()
                raise
        
        # Phase 6 requirement: Unsupervised Clustering (scikit-learn)
        # Cluster incidents using KMeans
        try:
            n_clusters = min(3, len(incidents))  # Phase 6 minimal: up to 3 clusters
            cluster_labels, kmeans_model = cluster_incidents(feature_vectors, n_clusters=n_clusters, random_state=42)
        except MemoryError:
            error_msg = "MEMORY ALLOCATION FAILURE: Failed to cluster incidents"
            logger.fatal(error_msg)
            from common.shutdown import ExitCode, exit_fatal
            exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
        except Exception as e:
            # Security: Sanitize exception message before logging
            try:
                from common.security.redaction import sanitize_exception
                safe_error = sanitize_exception(e)
            except ImportError:
                safe_error = str(e)
            logger.error(f"Clustering failed: {safe_error}")
            raise
        
        if len(cluster_labels) > 0:
            # Group incidents by cluster
            cluster_groups = {}
            for i, (incident, cluster_label) in enumerate(zip(incidents, cluster_labels)):
                if cluster_label not in cluster_groups:
                    cluster_groups[cluster_label] = []
                cluster_groups[cluster_label].append((incident, i))
            
            # Store clusters and memberships
            from dateutil import parser
            
            for cluster_label, cluster_incidents_list in cluster_groups.items():
                incident_list = [inc[0] for inc in cluster_incidents_list]
                incident_indices = [inc[1] for inc in cluster_incidents_list]
                incident_ids = [inc['incident_id'] for inc in incident_list]
                cluster_feature_vectors = feature_vectors[incident_indices]
                
                # Create cluster metadata
                try:
                    cluster_metadata = create_cluster_metadata(
                        cluster_label, incident_ids, cluster_feature_vectors, kmeans_model,
                        incident_list[0]['first_observed_at'],
                        incident_list[-1]['last_observed_at']
                    )
                except MemoryError:
                    error_msg = f"MEMORY ALLOCATION FAILURE: Failed to create cluster metadata for cluster {cluster_label}"
                    logger.fatal(error_msg)
                    from common.shutdown import ExitCode, exit_fatal
                    exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
                
                # Store cluster
                try:
                    first_obs = parser.isoparse(cluster_metadata['first_observed_at']) if isinstance(cluster_metadata['first_observed_at'], str) else cluster_metadata['first_observed_at']
                    last_obs = parser.isoparse(cluster_metadata['last_observed_at']) if isinstance(cluster_metadata['last_observed_at'], str) else cluster_metadata['last_observed_at']
                    
                    store_cluster(write_conn, cluster_metadata['cluster_id'], clustering_model_version,
                                cluster_metadata['cluster_label'], cluster_metadata['cluster_size'],
                                first_obs, last_obs)
                except MemoryError:
                    error_msg = f"MEMORY ALLOCATION FAILURE: Failed to store cluster {cluster_metadata['cluster_id']}"
                    logger.fatal(error_msg)
                    from common.shutdown import ExitCode, exit_fatal
                    exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
                except Exception as e:
                    # Security: Sanitize exception message before logging
                    try:
                        from common.security.redaction import sanitize_exception
                        safe_error = sanitize_exception(e)
                    except ImportError:
                        safe_error = str(e)
                    logger.db_error(safe_error, "store_cluster", cluster_id=cluster_metadata.get('cluster_id'))
                    raise
                
                # Store cluster memberships
                for incident_id, feature_vec in zip(incident_ids, cluster_feature_vectors):
                    try:
                        # Compute membership score (distance to centroid)
                        if kmeans_model is not None and hasattr(kmeans_model, 'cluster_centers_'):
                            centroid = kmeans_model.cluster_centers_[cluster_label]
                            distance = np.linalg.norm(feature_vec - centroid)
                            membership_score = 1.0 / (1.0 + distance)  # Inverse distance as score
                        else:
                            membership_score = 1.0
                        
                        store_cluster_membership(write_conn, cluster_metadata['cluster_id'], incident_id, membership_score)
                    except MemoryError:
                        error_msg = f"MEMORY ALLOCATION FAILURE: Failed to store cluster membership for incident {incident_id}"
                        logger.fatal(error_msg)
                        from common.shutdown import ExitCode, exit_fatal
                        exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
                    except Exception as e:
                        # Security: Sanitize exception message before logging
                        try:
                            from common.security.redaction import sanitize_exception
                            safe_error = sanitize_exception(e)
                        except ImportError:
                            safe_error = str(e)
                        logger.db_error(safe_error, "store_cluster_membership", incident_id=incident_id)
                        raise
            
            logger.info(f"Clustered {len(incidents)} incidents into {len(cluster_groups)} clusters",
                       clusters=len(cluster_groups))
        
        # Phase 6 requirement: SHAP Explainability
        # Generate SHAP explanations for incident confidence contributions
        try:
            shap_explanations = explain_batch(incidents, feature_vectors.tolist())
            logger.info(f"Generated SHAP explanations for {len(incidents)} incidents", 
                       shap_count=len(shap_explanations))
        except MemoryError:
            error_msg = "MEMORY ALLOCATION FAILURE: Failed to generate SHAP explanations"
            logger.fatal(error_msg)
            from common.shutdown import ExitCode, exit_fatal
            exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
        except Exception as e:
            # Security: Sanitize exception message before logging
            try:
                from common.security.redaction import sanitize_exception
                safe_error = sanitize_exception(e)
            except ImportError:
                safe_error = str(e)
            logger.error(f"SHAP explanation failed: {safe_error}")
            raise
        
        # Store SHAP explanations (references only, not blobs)
        stored_shap = 0
        for incident, shap_explanation in zip(incidents, shap_explanations):
            try:
                store_shap_explanation(write_conn, incident['incident_id'], explainability_model_version,
                                     shap_explanation, top_n=10)
                stored_shap += 1
            except MemoryError:
                error_msg = f"MEMORY ALLOCATION FAILURE: Failed to store SHAP explanation for incident {incident.get('incident_id')}"
                logger.fatal(error_msg)
                from common.shutdown import ExitCode, exit_fatal
                exit_fatal(error_msg, ExitCode.RUNTIME_ERROR)
            except Exception as e:
                # Security: Sanitize exception message before logging
                try:
                    from common.security.redaction import sanitize_exception
                    safe_error = sanitize_exception(e)
                except ImportError:
                    safe_error = str(e)
                logger.db_error(safe_error, "store_shap_explanation", incident_id=incident.get('incident_id'))
                raise
        
        logger.info("AI Core batch processing complete", 
                   features_stored=stored_features, shap_stored=stored_shap)
        
    except Exception as e:
        logger.fatal(f"Fatal error in AI Core: {e}")
        raise
    finally:
        if read_conn:
            read_conn.close()
            logger.shutdown("Read-only database connection closed")
        if write_conn:
            write_conn.close()
            logger.shutdown("Write database connection closed")


if __name__ == "__main__":
    # Phase 6 requirement: No async, no background threads, no background schedulers
    # Synchronous batch execution only
    try:
        run_ai_core()
        logger.shutdown("AI Core completed successfully")
        sys.exit(ExitCode.SUCCESS)
    except KeyboardInterrupt:
        logger.shutdown("Received interrupt, shutting down")
        sys.exit(ExitCode.SUCCESS)
    except ConfigError as e:
        logger.config_error(str(e))
        sys.exit(ExitCode.CONFIG_ERROR)
    except Exception as e:
        logger.fatal(f"Fatal error: {e}")
        sys.exit(ExitCode.FATAL_ERROR)
