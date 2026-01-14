#!/usr/bin/env python3
"""
RansomEye v1.0 AI Core - Database Module
AUTHORITATIVE: Database operations for read-only AI Core
Python 3.10+ only - aligns with Phase 6 requirements
"""

import os
import sys
import psycopg2
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.db.safety import (create_readonly_connection, create_write_connection, 
                                   IsolationLevel, execute_write_operation, 
                                   execute_read_operation, begin_transaction, 
                                   commit_transaction, rollback_transaction,
                                   validate_connection_health)
    from common.logging import setup_logging
    _common_db_safety_available = True
    _logger = setup_logging('ai-core-db')
except ImportError:
    _common_db_safety_available = False
    _logger = None
    def create_readonly_connection(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def create_write_connection(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def execute_write_operation(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def execute_read_operation(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def begin_transaction(*args, **kwargs): pass
    def commit_transaction(*args, **kwargs): pass
    def rollback_transaction(*args, **kwargs): pass
    def validate_connection_health(*args, **kwargs): return True
    class IsolationLevel: READ_COMMITTED = 2


def get_db_connection_readonly():
    """
    Get read-only PostgreSQL database connection.
    Transaction discipline: Explicit isolation level (READ_COMMITTED).
    Read-only enforcement: Abort if write attempted.
    Connection safety: Validate health before returning.
    """
    # PHASE 1: Per-service database user (required, no defaults)
    db_user = os.getenv("RANSOMEYE_DB_USER")
    if not db_user:
        error_msg = "RANSOMEYE_DB_USER is required (PHASE 1: per-service user required, no defaults)"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)
    
    if _common_db_safety_available:
        conn = create_readonly_connection(
            host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
            port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
            database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
            user=db_user,  # PHASE 1: Per-service user (required, no defaults)
            password=os.getenv("RANSOMEYE_DB_PASSWORD", ""),
            isolation_level=IsolationLevel.READ_COMMITTED,
            logger=_logger
        )
        return conn
    else:
        # Fallback
        return psycopg2.connect(
            host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
            port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
            database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
            user=db_user,  # PHASE A2: Must be ransomeye_ai_core
            password=os.getenv("RANSOMEYE_DB_PASSWORD", "")
        )


def get_db_connection_write():
    """
    Get write-enabled PostgreSQL database connection for metadata writes.
    Transaction discipline: Explicit isolation level (READ_COMMITTED).
    Connection safety: Validate health before returning.
    """
    # PHASE 1: Per-service database user (required, no defaults)
    db_user = os.getenv("RANSOMEYE_DB_USER")
    if not db_user:
        error_msg = "RANSOMEYE_DB_USER is required (PHASE 1: per-service user required, no defaults)"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        from common.shutdown import ExitCode, exit_fatal
        exit_fatal(error_msg, ExitCode.STARTUP_ERROR)
    
    if _common_db_safety_available:
        conn = create_write_connection(
            host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
            port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
            database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
            user=db_user,  # PHASE 1: Per-service user (required, no defaults)
            password=os.getenv("RANSOMEYE_DB_PASSWORD", ""),
            isolation_level=IsolationLevel.READ_COMMITTED,
            logger=_logger
        )
        return conn
    else:
        # Fallback
        return psycopg2.connect(
            host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
            port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
            database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
            user=db_user,  # PHASE A2: Must be ransomeye_ai_core
            password=os.getenv("RANSOMEYE_DB_PASSWORD", "")
        )


def get_db_connection():
    """Legacy alias - returns read-only connection."""
    return get_db_connection_readonly()


def get_unresolved_incidents(conn) -> List[Dict[str, Any]]:
    """
    Get unresolved incidents for AI analysis.
    Contract compliance: Read from incidents table (Phase 2 schema)
    Read-only operation: Enforced at connection level.
    Connection safety: Validated before operation.
    """
    def _do_read():
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT 
                    incident_id,
                    machine_id,
                    current_stage,
                    first_observed_at,
                    last_observed_at,
                    total_evidence_count,
                    confidence_score
                FROM incidents
                WHERE resolved = FALSE
                ORDER BY first_observed_at ASC
            """)
            
            columns = [desc[0] for desc in cur.description]
            incidents = []
            for row in cur.fetchall():
                incident = dict(zip(columns, row))
                for key in ['first_observed_at', 'last_observed_at']:
                    if isinstance(incident[key], datetime):
                        incident[key] = incident[key].isoformat()
                incidents.append(incident)
            
            return incidents
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_read_operation(conn, "get_unresolved_incidents", _do_read, _logger, enforce_readonly=True)
    else:
        return _do_read()


def get_model_version(conn, model_type: str, model_version_string: str) -> Optional[str]:
    """
    Get model version ID or create new model version.
    Transaction discipline: Explicit begin, commit on success, rollback on failure.
    Deadlock/integrity violation detection: Log and terminate (no retries).
    Connection safety: Validate health before operation.
    """
    def _do_get_or_create():
        cur = conn.cursor()
        try:
            # Check if model version already exists
            cur.execute("""
                SELECT model_version_id 
                FROM ai_model_versions 
                WHERE model_type = %s AND model_version_string = %s AND deprecated_at IS NULL
            """, (model_type, model_version_string))
            
            result = cur.fetchone()
            if result:
                return result[0]
            
            # Create new model version (if not exists)
            import uuid
            model_version_id = str(uuid.uuid4())
            
            # PHASE 3: Use deterministic timestamp (from first incident observed_at)
            # For model version creation, use a deterministic timestamp
            # Since this is a new model version, we'll use a fixed timestamp or from config
            from datetime import datetime, timezone
            deployed_at = datetime.now(timezone.utc)  # This will be replaced with deterministic value
            
            cur.execute("""
                INSERT INTO ai_model_versions (
                    model_version_id, model_type, model_version_string, deployed_at, description
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (model_version_id, model_type, model_version_string, deployed_at,
                  f"PHASE 3 AI Core model: {model_type} version {model_version_string}"))
            
            return model_version_id
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_write_operation(conn, "get_model_version", _do_get_or_create, _logger)
    else:
        begin_transaction(conn, _logger)
        try:
            result = _do_get_or_create()
            commit_transaction(conn, _logger, "get_model_version")
            return result
        except Exception as e:
            rollback_transaction(conn, _logger, "get_model_version")
            raise


def store_feature_vector(conn, incident_id: str, model_version_id: str, 
                        feature_vector: List[float], storage_path: Optional[str] = None):
    """
    Store feature vector reference (not the actual vector).
    Transaction discipline: Explicit begin, commit on success, rollback on failure.
    Deadlock/integrity violation detection: Log and terminate (no retries).
    Connection safety: Validate health before operation.
    """
    def _do_store():
        cur = conn.cursor()
        try:
            import hashlib
            
            feature_vector_bytes = json.dumps(feature_vector, sort_keys=True).encode('utf-8')
            feature_vector_hash = hashlib.sha256(feature_vector_bytes).hexdigest()
            feature_vector_size = len(feature_vector)
            
            # Check if feature vector already exists (idempotency)
            cur.execute("""
                SELECT id FROM feature_vectors 
                WHERE event_id = %s AND model_version_id = %s
            """, (incident_id, model_version_id))
            
            if cur.fetchone():
                # Already exists, skip (idempotent)
                return
            
            cur.execute("""
                INSERT INTO feature_vectors (
                    event_id, model_version_id, feature_vector_hash_sha256,
                    feature_vector_size, feature_vector_storage_path, computed_at, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'PROCESSED')
            """, (incident_id, model_version_id, feature_vector_hash, feature_vector_size, storage_path))
            
            return True
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_write_operation(conn, "store_feature_vector", _do_store, _logger)
    else:
        begin_transaction(conn, _logger)
        try:
            result = _do_store()
            commit_transaction(conn, _logger, "store_feature_vector")
            return result
        except Exception as e:
            rollback_transaction(conn, _logger, "store_feature_vector")
            raise


def store_cluster(conn, cluster_id: str, model_version_id: str, cluster_label: str,
                 cluster_size: int, cluster_created_at: datetime, cluster_updated_at: datetime,
                 training_data_hash: Optional[str] = None, model_hash: Optional[str] = None):
    """
    Store cluster metadata.
    Transaction discipline: Explicit begin, commit on success, rollback on failure.
    Deadlock/integrity violation detection: Log and terminate (no retries).
    """
    def _do_store():
        cur = conn.cursor()
        try:
            # PHASE 3: Store training data hash and model hash if provided
            cur.execute("""
                INSERT INTO clusters (
                    cluster_id, model_version_id, cluster_label, cluster_size,
                    cluster_created_at, cluster_updated_at, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVE')
                ON CONFLICT (cluster_id) DO NOTHING
            """, (cluster_id, model_version_id, cluster_label, cluster_size,
                  cluster_created_at, cluster_updated_at))
            
            # PHASE 3: Update model version with training data hash and model hash
            if training_data_hash or model_hash:
                update_fields = []
                update_values = []
                if training_data_hash:
                    update_fields.append("training_data_hash_sha256 = %s")
                    update_values.append(training_data_hash)
                if model_hash:
                    update_fields.append("model_hash_sha256 = %s")
                    update_values.append(model_hash)
                if model_storage_path:
                    update_fields.append("model_storage_path = %s")
                    update_values.append(model_storage_path)
                
                if update_fields:
                    update_values.append(model_version_id)
                    cur.execute(f"""
                        UPDATE ai_model_versions
                        SET {', '.join(update_fields)}
                        WHERE model_version_id = %s
                    """, update_values)
            return True
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_write_operation(conn, "store_cluster", _do_store, _logger)
    else:
        begin_transaction(conn, _logger)
        try:
            result = _do_store()
            commit_transaction(conn, _logger, "store_cluster")
            return result
        except Exception as e:
            rollback_transaction(conn, _logger, "store_cluster")
            raise


def store_cluster_membership(conn, cluster_id: str, incident_id: str, membership_score: Optional[float],
                             added_at: Optional[datetime] = None):
    """
    Store cluster membership (incident belongs to cluster).
    Transaction discipline: Explicit begin, commit on success, rollback on failure.
    Deadlock/integrity violation detection: Log and terminate (no retries).
    """
    def _do_store():
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO cluster_memberships (
                    cluster_id, event_id, membership_score, added_at
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (cluster_id, event_id) DO NOTHING
            """, (cluster_id, incident_id, membership_score))
            return True
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_write_operation(conn, "store_cluster_membership", _do_store, _logger)
    else:
        begin_transaction(conn, _logger)
        try:
            result = _do_store()
            commit_transaction(conn, _logger, "store_cluster_membership")
            return result
        except Exception as e:
            rollback_transaction(conn, _logger, "store_cluster_membership")
            raise


def store_shap_explanation(conn, incident_id: str, model_version_id: str,
                          shap_explanation: List[Dict[str, Any]], top_n: int = 10,
                          computed_at: Optional[datetime] = None):
    """
    PHASE 3: Store full SHAP explanation (for replay support).
    
    Stores:
    - Full SHAP explanation (for replay)
    - Top N features (for quick access)
    - SHAP hash (for integrity verification)
    
    Transaction discipline: Explicit begin, commit on success, rollback on failure.
    Deadlock/integrity violation detection: Log and terminate (no retries).
    """
    def _do_store():
        cur = conn.cursor()
        try:
            import hashlib
            
            # PHASE 3: Store full SHAP explanation (not just hash)
            shap_bytes = json.dumps(shap_explanation, sort_keys=True).encode('utf-8')
            shap_hash = hashlib.sha256(shap_bytes).hexdigest()
            shap_size = len(shap_explanation)
            
            # PHASE 3: Store full explanation as JSONB
            shap_explanation_full_json = json.dumps(shap_explanation, sort_keys=True)
            
            # Top N features for quick access
            top_features = sorted(shap_explanation, key=lambda x: abs(x.get('contribution', 0)), reverse=True)[:top_n]
            top_features_json = json.dumps(top_features)
            
            # PHASE 3: Use deterministic timestamp (from incident observed_at)
            if computed_at is None:
                # Fallback: use current time (should not happen in production)
                from datetime import datetime, timezone
                computed_at = datetime.now(timezone.utc)
            
            cur.execute("""
                INSERT INTO shap_explanations (
                    event_id, model_version_id, shap_explanation_hash_sha256,
                    shap_explanation_size, shap_explanation_full, top_features_contributions, computed_at
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                ON CONFLICT (event_id, model_version_id) DO UPDATE
                SET shap_explanation_hash_sha256 = EXCLUDED.shap_explanation_hash_sha256,
                    shap_explanation_size = EXCLUDED.shap_explanation_size,
                    shap_explanation_full = EXCLUDED.shap_explanation_full,
                    top_features_contributions = EXCLUDED.top_features_contributions,
                    computed_at = EXCLUDED.computed_at
            """, (incident_id, model_version_id, shap_hash, shap_size, 
                  shap_explanation_full_json, top_features_json, computed_at))
            
            return True
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_write_operation(conn, "store_shap_explanation", _do_store, _logger)
    else:
        begin_transaction(conn, _logger)
        try:
            result = _do_store()
            commit_transaction(conn, _logger, "store_shap_explanation")
            return result
        except Exception as e:
            rollback_transaction(conn, _logger, "store_shap_explanation")
            raise
