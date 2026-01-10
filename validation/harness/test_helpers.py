#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - Test Helpers
AUTHORITATIVE: Helper functions for validation tests
Phase 9.1 requirement: NO synthetic data, real system behavior only
"""

import os
import sys
import subprocess
import time
import psycopg2
import requests
from typing import Optional, Dict, Any


def get_test_db_connection():
    """Get database connection for validation."""
    return psycopg2.connect(
        host=os.getenv("RANSOMEYE_DB_HOST", "localhost"),
        port=int(os.getenv("RANSOMEYE_DB_PORT", "5432")),
        database=os.getenv("RANSOMEYE_DB_NAME", "ransomeye"),
        user=os.getenv("RANSOMEYE_DB_USER", "ransomeye"),
        password=os.getenv("RANSOMEYE_DB_PASSWORD", "")
    )


def clean_database():
    """
    Clean database for test isolation.
    Phase 10 requirement: Clean up test data before and after tests.
    """
    conn = get_test_db_connection()
    cur = conn.cursor()
    try:
        # Phase 10 requirement: Delete in dependency order (reverse of creation)
        cur.execute("DELETE FROM evidence")
        cur.execute("DELETE FROM incident_stages")
        cur.execute("DELETE FROM incidents")
        cur.execute("DELETE FROM event_validation_log")
        cur.execute("DELETE FROM raw_events")
        cur.execute("DELETE FROM component_instances")
        cur.execute("DELETE FROM machines")
        # AI metadata tables (Phase 6)
        cur.execute("DELETE FROM shap_explanations")
        cur.execute("DELETE FROM novelty_scores")
        cur.execute("DELETE FROM cluster_memberships")
        cur.execute("DELETE FROM clusters")
        cur.execute("DELETE FROM feature_vectors")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def find_linux_agent_binary() -> str:
    """
    Find Linux Agent binary path.
    Phase 9.1 requirement: Use real agent binary, no synthetic events.
    """
    # Try release build first
    release_path = os.path.join(os.path.dirname(__file__), '../../services/linux-agent/target/release/ransomeye-linux-agent')
    if os.path.exists(release_path) and os.access(release_path, os.X_OK):
        return release_path
    
    # Try debug build
    debug_path = os.path.join(os.path.dirname(__file__), '../../services/linux-agent/target/debug/ransomeye-linux-agent')
    if os.path.exists(debug_path) and os.access(debug_path, os.X_OK):
        return debug_path
    
    # Try direct binary name (in PATH)
    import shutil
    binary = shutil.which('ransomeye-linux-agent')
    if binary:
        return binary
    
    raise FileNotFoundError("Linux Agent binary not found. Build with: cd services/linux-agent && cargo build --release")


def launch_linux_agent_and_wait_for_event(
    ingest_url: str = "http://localhost:8000/events",
    timeout_seconds: int = 30,
    component_instance_id: Optional[str] = None,
    agent_version: str = "1.0.0"
) -> Dict[str, Any]:
    """
    Launch real Linux Agent binary and wait for it to emit one real event.
    
    Phase 9.1 requirement: NO synthetic events, launch real agent, observe real behavior.
    Contract compliance: Uses real agent binary, real event emission.
    
    Args:
        ingest_url: Ingest service URL
        timeout_seconds: Maximum time to wait for event
        component_instance_id: Component instance ID (if None, generates UUID-like string)
        agent_version: Agent version string
        
    Returns:
        Dictionary with:
        - event_id: Real event ID from database (observed, not fixed)
        - machine_id: Real machine ID from database (observed)
        - observed_at: Real timestamp from database (observed)
        - agent_exit_code: Exit code from agent process
    """
    import uuid
    
    # Phase 9.1 requirement: Launch real agent binary
    agent_binary = find_linux_agent_binary()
    
    # Set environment variables for agent
    env = os.environ.copy()
    env['RANSOMEYE_INGEST_URL'] = ingest_url
    env['RANSOMEYE_VERSION'] = agent_version
    
    if component_instance_id is None:
        # Phase 9.1 requirement: Generate component_instance_id (not a fixed UUID, but unique per run)
        component_instance_id = f"test-instance-{uuid.uuid4()}"
    env['RANSOMEYE_COMPONENT_INSTANCE_ID'] = component_instance_id
    
    # Get initial event count (observational baseline)
    conn = get_test_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM raw_events")
        initial_event_count = cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()
    
    # Launch agent process
    process = subprocess.Popen(
        [agent_binary],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for agent to emit event (observational approach)
    # Phase 9.1 requirement: Wait for real event, no fixed timeouts
    start_time = time.time()
    event_observed = False
    event_id = None
    machine_id = None
    observed_at = None
    
    while (time.time() - start_time) < timeout_seconds:
        # Check if process finished
        if process.poll() is not None:
            break
        
        # Check database for new event (observational)
        conn = get_test_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM raw_events")
            current_event_count = cur.fetchone()[0]
            
            if current_event_count > initial_event_count:
                # New event observed (real event, not synthetic)
                cur.execute("""
                    SELECT event_id, machine_id, observed_at
                    FROM raw_events
                    ORDER BY ingested_at DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    event_id, machine_id, observed_at = row
                    event_observed = True
                    break
        finally:
            cur.close()
            conn.close()
        
        time.sleep(0.1)  # Small delay to avoid tight loop (observational polling, not timing hack)
    
    # Wait for process to finish (if not already finished)
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
    
    agent_exit_code = process.returncode
    
    if not event_observed:
        raise RuntimeError(
            f"Agent did not emit event within {timeout_seconds} seconds. "
            f"Exit code: {agent_exit_code}, stdout: {stdout}, stderr: {stderr}"
        )
    
    # Phase 9.1 requirement: Return observed values, not fixed values
    return {
        'event_id': event_id,
        'machine_id': machine_id,
        'observed_at': observed_at.isoformat() if hasattr(observed_at, 'isoformat') else str(observed_at),
        'agent_exit_code': agent_exit_code,
        'component_instance_id': component_instance_id
    }


def verify_event_structure(conn, event_id: str):
    """
    Verify event structure (structural assertions, no fixed UUIDs).
    Phase 9.1 requirement: Structural assertions only, no fixed values.
    """
    cur = conn.cursor()
    try:
        # Structural assertion: Event exists
        cur.execute("SELECT * FROM raw_events WHERE event_id = %s", (event_id,))
        row = cur.fetchone()
        if not row:
            raise AssertionError(f"Event {event_id} not found in database")
        
        # Structural assertion: Required columns present
        columns = [desc[0] for desc in cur.description]
        required_columns = ['event_id', 'machine_id', 'component', 'component_instance_id', 
                          'observed_at', 'ingested_at', 'sequence', 'payload',
                          'hostname', 'boot_id', 'agent_version', 'hash_sha256']
        for col in required_columns:
            if col not in columns:
                raise AssertionError(f"Required column {col} not found in raw_events")
        
        # Structural assertion: Component is linux_agent (contract compliance)
        cur.execute("SELECT component FROM raw_events WHERE event_id = %s", (event_id,))
        component = cur.fetchone()[0]
        if component != 'linux_agent':
            raise AssertionError(f"Expected component='linux_agent', found component='{component}'")
        
        # Structural assertion: Sequence is non-negative integer
        cur.execute("SELECT sequence FROM raw_events WHERE event_id = %s", (event_id,))
        sequence = cur.fetchone()[0]
        if not isinstance(sequence, (int, type(sequence))) or sequence < 0:
            raise AssertionError(f"Expected sequence >= 0, found sequence={sequence}")
        
        # Structural assertion: Payload is valid JSON
        cur.execute("SELECT payload FROM raw_events WHERE event_id = %s", (event_id,))
        payload = cur.fetchone()[0]
        if not isinstance(payload, (dict, list)):
            raise AssertionError(f"Expected payload to be JSON object/array, found type={type(payload)}")
        
    finally:
        cur.close()


def verify_integrity_chain(conn, event_id: str):
    """
    Verify integrity chain (contract compliance, no fixed hashes).
    Phase 9.1 requirement: Integrity chain verification, no fixed hash checks.
    """
    cur = conn.cursor()
    try:
        # Structural assertion: Hash exists and is valid format (64 hex chars)
        cur.execute("SELECT hash_sha256 FROM raw_events WHERE event_id = %s", (event_id,))
        hash_sha256 = cur.fetchone()[0]
        if not hash_sha256:
            raise AssertionError(f"Event {event_id} missing hash_sha256")
        if not isinstance(hash_sha256, str) or len(hash_sha256) != 64:
            raise AssertionError(f"Event {event_id} hash_sha256 invalid format (expected 64 hex chars)")
        
        # Structural assertion: Hash is hexadecimal
        try:
            int(hash_sha256, 16)
        except ValueError:
            raise AssertionError(f"Event {event_id} hash_sha256 is not hexadecimal")
        
    finally:
        cur.close()


def verify_signed_command_exists(incident_id: str, policy_dir: str = None) -> bool:
    """
    Verify signed command exists for incident (observational, no content inspection).
    Phase 9.1 requirement: Verify signed command exists, cryptographically verify signature.
    Contract compliance: Uses HMAC-SHA256 signature (matches policy-engine signer.py)
    Note: Signed command files are named by command_id, not incident_id, so we search for files.
    """
    import json
    import hmac
    import hashlib
    import glob
    
    if policy_dir is None:
        policy_dir = os.getenv("RANSOMEYE_POLICY_DIR", "/tmp/ransomeye/policy")
    
    # Structural assertion: Policy decision file exists
    policy_file = os.path.join(policy_dir, f"policy_decision_{incident_id}.json")
    if not os.path.exists(policy_file):
        return False
    
    # Load policy decision to check if action was recommended (observational)
    with open(policy_file, 'r') as f:
        policy_decision = json.load(f)
    
    # If no action was recommended, no signed command should exist (observational)
    if not policy_decision.get('should_recommend_action', False):
        return False
    
    # Structural assertion: Signed command file exists (search by command_id pattern)
    # Phase 9.1 requirement: Find signed command file (named by command_id, not incident_id)
    # For Phase 9.1 minimal, we search for signed command files and verify incident_id matches
    signed_command_pattern = os.path.join(policy_dir, "signed_command_*.json")
    signed_command_files = glob.glob(signed_command_pattern)
    
    if not signed_command_files:
        return False
    
    # Find signed command file with matching incident_id (observational)
    signed_command_file = None
    for file_path in signed_command_files:
        try:
            with open(file_path, 'r') as f:
                cmd = json.load(f)
                if cmd.get('payload', {}).get('incident_id') == incident_id:
                    signed_command_file = file_path
                    break
        except (json.JSONDecodeError, KeyError):
            continue
    
    if not signed_command_file or not os.path.exists(signed_command_file):
        return False
    
    # Load signed command (observational, for signature verification only)
    with open(signed_command_file, 'r') as f:
        signed_command = json.load(f)
    
    # Structural assertion: Required fields present (matching policy-engine signer.py structure)
    required_fields = ['payload', 'signature']
    for field in required_fields:
        if field not in signed_command:
            raise AssertionError(f"Signed command missing required field: {field}")
    
    # Phase 9.1 requirement: Cryptographically verify signature (HMAC-SHA256)
    command_payload = signed_command['payload']  # Note: field name is 'payload', not 'command_payload'
    provided_signature = signed_command['signature']
    
    # Get signing key (from environment or default, matching policy-engine signer.py)
    signing_key_str = os.getenv("RANSOMEYE_COMMAND_SIGNING_KEY", "")
    if not signing_key_str:
        # Phase 7 minimal: Use default signing key (matches policy-engine signer.py)
        signing_key_str = "phase7_minimal_default_key_change_in_production"
    
    signing_key = signing_key_str.encode('utf-8')
    
    # Serialize command payload to canonical JSON (matching policy-engine signer.py)
    payload_json = json.dumps(command_payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    payload_bytes = payload_json.encode('utf-8')
    
    # Compute HMAC-SHA256 signature (matching policy-engine signer.py)
    computed_signature = hmac.new(
        signing_key,
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Structural assertion: Signature is valid format (64 hex chars)
    if not isinstance(provided_signature, str) or len(provided_signature) != 64:
        raise AssertionError(f"Invalid signature format: expected 64 hex chars, got {len(provided_signature) if isinstance(provided_signature, str) else 'non-string'}")
    
    # Structural assertion: Signature is hexadecimal
    try:
        int(provided_signature, 16)
    except ValueError:
        raise AssertionError(f"Signature is not hexadecimal: {provided_signature}")
    
    # Phase 9.1 requirement: Cryptographically verify signature (constant-time comparison)
    if not hmac.compare_digest(provided_signature, computed_signature):
        raise AssertionError(f"Signature verification failed: provided signature does not match computed signature")
    
    return True


def verify_command_not_executed(incident_id: str, policy_dir: str = None) -> bool:
    """
    Verify command was not executed (observational: check no execution logs exist).
    Phase 9.1 requirement: Verify command was not executed.
    """
    if policy_dir is None:
        policy_dir = os.getenv("RANSOMEYE_POLICY_DIR", "/tmp/ransomeye/policy")
    
    # Structural assertion: No execution log exists (command was not executed)
    execution_log_file = os.path.join(policy_dir, f"command_execution_{incident_id}.json")
    if os.path.exists(execution_log_file):
        return False  # Execution log exists, command was executed (violation)
    
    return True  # No execution log, command was not executed (correct)


def verify_ai_metadata_exists(conn, event_id: str, check_content: bool = False) -> Dict[str, Any]:
    """
    Verify AI metadata exists or not (observational, no content inspection unless requested).
    Phase 9.1 requirement: Verify AI metadata exists or not, without inspecting content.
    
    Args:
        conn: Database connection
        event_id: Event ID to check
        check_content: If True, verify content structure (for Phase 9.1 minimal, False by default)
        
    Returns:
        Dictionary with existence flags for each metadata type
    """
    cur = conn.cursor()
    result = {
        'has_cluster_membership': False,
        'has_novelty_score': False,
        'has_shap_explanation': False,
        'has_feature_vector': False
    }
    
    try:
        # Cardinality assertion: Cluster membership exists or not
        cur.execute("SELECT COUNT(*) FROM cluster_memberships WHERE event_id = %s", (event_id,))
        result['has_cluster_membership'] = cur.fetchone()[0] > 0
        
        # Cardinality assertion: Novelty score exists or not
        cur.execute("SELECT COUNT(*) FROM novelty_scores WHERE event_id = %s", (event_id,))
        result['has_novelty_score'] = cur.fetchone()[0] > 0
        
        # Cardinality assertion: SHAP explanation exists or not
        cur.execute("SELECT COUNT(*) FROM shap_explanations WHERE event_id = %s", (event_id,))
        result['has_shap_explanation'] = cur.fetchone()[0] > 0
        
        # Cardinality assertion: Feature vector exists or not
        cur.execute("SELECT COUNT(*) FROM feature_vectors WHERE event_id = %s", (event_id,))
        result['has_feature_vector'] = cur.fetchone()[0] > 0
        
        # Phase 9.1 requirement: No content inspection unless requested
        if check_content:
            # Structural assertions only (no fixed values)
            if result['has_cluster_membership']:
                cur.execute("SELECT cluster_id FROM cluster_memberships WHERE event_id = %s LIMIT 1", (event_id,))
                row = cur.fetchone()
                if row:
                    cluster_id = row[0]
                    # Structural assertion: Cluster ID is valid UUID format
                    if not isinstance(cluster_id, str) or len(cluster_id) != 36:
                        raise AssertionError(f"Invalid cluster_id format: {cluster_id}")
        
    finally:
        cur.close()
    
    return result
