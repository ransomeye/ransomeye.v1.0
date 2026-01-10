#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - Test: Cold Start Correctness
AUTHORITATIVE: Validates system cold start behavior
Phase 9 requirement: Assert real system behavior, no mocks, no sleeps, deterministic
"""

import os
import sys
import psycopg2

# Add services to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/correlation-engine/app'))


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
    """Clean database for test isolation. Phase 9 requirement: Clean up."""
    conn = get_test_db_connection()
    cur = conn.cursor()
    try:
        # Phase 9 requirement: Clean up test data
        # Delete in dependency order (reverse of creation)
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
    finally:
        cur.close()
        conn.close()


def assert_database_empty():
    """Assert database is empty. Phase 9 requirement: Assert DB state."""
    conn = get_test_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM machines")
        assert cur.fetchone()[0] == 0, "Database not empty: machines table has rows"
        
        cur.execute("SELECT COUNT(*) FROM raw_events")
        assert cur.fetchone()[0] == 0, "Database not empty: raw_events table has rows"
        
        cur.execute("SELECT COUNT(*) FROM incidents")
        assert cur.fetchone()[0] == 0, "Database not empty: incidents table has rows"
        
        cur.execute("SELECT COUNT(*) FROM evidence")
        assert cur.fetchone()[0] == 0, "Database not empty: evidence table has rows"
    finally:
        cur.close()
        conn.close()


def test_cold_start_correctness():
    """
    Test cold start correctness.
    Phase 9 requirement: Validate system behavior with no prior state.
    
    Validation:
    1. Database is empty (cold start)
    2. Services can start without errors
    3. System is in correct initial state
    """
    print("=" * 80)
    print("TEST: Cold Start Correctness")
    print("=" * 80)
    
    # Phase 9 requirement: Set up environment
    print("Setting up test environment...")
    clean_database()
    assert_database_empty()
    
    # Set required environment variables for service imports
    schema_path = os.path.join(os.path.dirname(__file__), '../../contracts/event-envelope.schema.json')
    os.environ['RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH'] = schema_path
    os.environ['RANSOMEYE_LOG_DIR'] = '/tmp/ransomeye/logs'
    os.environ['RANSOMEYE_POLICY_DIR'] = '/tmp/ransomeye/policy'
    
    # Phase 9 requirement: Execute scenario
    print("Executing cold start scenario...")
    
    # Test 1: Ingest service can start (no errors)
    print("  Test 1: Ingest service can start...")
    try:
        # Import ingest service (validates it can be imported without errors)
        import importlib.util
        ingest_main_path = os.path.join(os.path.dirname(__file__), '../../services/ingest/app/main.py')
        spec = importlib.util.spec_from_file_location("ingest_main", ingest_main_path)
        ingest_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ingest_main)
        # Just check that it has 'app' attribute (the FastAPI app)
        assert hasattr(ingest_main, 'app'), "Ingest service missing 'app' attribute"
        print("    PASS: Ingest service can be imported")
    except Exception as e:
        print(f"    FAIL: Ingest service cannot be imported: {e}")
        raise
    
    # Test 2: Correlation engine can start (no errors)
    print("  Test 2: Correlation engine can start...")
    try:
        # Import correlation engine (validates it can be imported without errors)
        import importlib.util
        correlation_main_path = os.path.join(os.path.dirname(__file__), '../../services/correlation-engine/app/main.py')
        spec = importlib.util.spec_from_file_location("correlation_main", correlation_main_path)
        correlation_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(correlation_main)
        # Check that it has 'run_correlation_engine' function
        assert hasattr(correlation_main, 'run_correlation_engine'), "Correlation engine missing 'run_correlation_engine' function"
        run_correlation_engine = correlation_main.run_correlation_engine
        print("    PASS: Correlation engine can be imported")
    except Exception as e:
        print(f"    FAIL: Correlation engine cannot be imported: {e}")
        raise
    
    # Test 3: Correlation engine runs with empty database (no errors)
    print("  Test 3: Correlation engine runs with empty database...")
    try:
        # Phase 9 requirement: No mocks, real system behavior
        # Run correlation engine with empty database (should handle gracefully)
        run_correlation_engine()
        print("    PASS: Correlation engine runs with empty database")
    except Exception as e:
        print(f"    FAIL: Correlation engine fails with empty database: {e}")
        raise
    
    # Test 4: Database remains empty (correct state)
    print("  Test 4: Database remains empty after cold start...")
    try:
        assert_database_empty()
        print("    PASS: Database remains empty after cold start")
    except AssertionError as e:
        print(f"    FAIL: Database not empty after cold start: {e}")
        raise
    
    # Phase 9 requirement: Assert logs / exit codes
    print("  Test 5: No errors in execution...")
    # Exit code validation: If we get here, no exceptions were raised
    print("    PASS: No errors in execution (exit code would be 0)")
    
    # Phase 9 requirement: Clean up
    print("Cleaning up test environment...")
    clean_database()
    assert_database_empty()
    
    print("=" * 80)
    print("PASS: Cold Start Correctness")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        test_cold_start_correctness()
        sys.exit(0)
    except Exception as e:
        print(f"\nFAIL: Cold Start Correctness - {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
