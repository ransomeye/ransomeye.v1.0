#!/usr/bin/env python3
"""
RansomEye v1.0 GA - Ingest Service Diagnostics Router
AUTHORITATIVE: Operational telemetry endpoints for SRE/admin visibility

GA-BLOCKING: /health/metrics endpoint provides operational visibility without
compromising security or privacy.

STRICT SECURITY & PRIVACY RULES:
❌ No hostnames
❌ No IP addresses
❌ No tenant identifiers
❌ No incident metadata
❌ No file paths
❌ No payload samples

This endpoint monitors the system, not threats.
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, timedelta

from services.ingest.app.metrics import get_metrics

router = APIRouter(prefix="/health", tags=["diagnostics"])


@router.get("/metrics")
async def get_metrics_endpoint() -> Dict[str, Any]:
    """
    GA-BLOCKING: Operational telemetry endpoint.
    
    Returns operational metrics for SRE/admin visibility:
    - system_status: "HEALTHY" | "DEGRADED" | "CRITICAL"
    - ingest_rate_eps: 1-minute moving average of events per second
    - db_write_latency_ms: Average of last ~100 DB writes
    - queue_depth: Current size of ingest/processing buffer
    - agent_heartbeat_lag_sec: Max time since last valid agent heartbeat
    
    FAILURE BEHAVIOR (MANDATORY):
    - If DB is unreachable: Return HTTP 200, system_status = "CRITICAL"
    - Do not throw exceptions
    - Do not hang
    - Do not retry indefinitely
    
    Returns:
        JSON response with metrics (always HTTP 200)
    """
    metrics = get_metrics()
    
    # Check DB reachability (non-blocking, with timeout)
    db_reachable = False
    try:
        # Import here to avoid circular dependencies
        from services.ingest.app.main import get_db_connection, put_db_connection
        
        # Quick DB check with timeout (non-blocking)
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            db_reachable = True
        except Exception:
            # DB unreachable - continue with CRITICAL status
            db_reachable = False
        finally:
            if conn:
                put_db_connection(conn)
    except Exception:
        # DB pool not initialized or other error - continue with CRITICAL status
        db_reachable = False
    
    # Query agent heartbeat lag (non-blocking, with timeout)
    heartbeat_lag_sec = None
    if db_reachable:
        try:
            from services.ingest.app.main import get_db_connection, put_db_connection
            
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    # Query max time since last heartbeat (non-blocking)
                    # Do not expose agent identity - only max lag
                    cur.execute("""
                        SELECT MAX(EXTRACT(EPOCH FROM (NOW() - observed_at))) as max_lag_sec
                        FROM health_heartbeat
                        WHERE observed_at >= NOW() - INTERVAL '1 hour'
                    """)
                    result = cur.fetchone()
                    if result and result[0] is not None:
                        heartbeat_lag_sec = float(result[0])
                        metrics.update_agent_heartbeat_lag(heartbeat_lag_sec)
            except Exception:
                # Query failed - use cached value if available
                heartbeat_lag_sec = metrics.get_agent_heartbeat_lag_sec()
            finally:
                if conn:
                    put_db_connection(conn)
        except Exception:
            # DB pool not available - use cached value if available
            heartbeat_lag_sec = metrics.get_agent_heartbeat_lag_sec()
    else:
        # DB unreachable - use cached value if available
        heartbeat_lag_sec = metrics.get_agent_heartbeat_lag_sec()
    
    # Get system status
    system_status = metrics.get_system_status(db_reachable)
    
    # Get all metrics
    ingest_rate_eps = metrics.get_ingest_rate_eps()
    db_write_latency_ms = metrics.get_db_write_latency_ms()
    queue_depth = metrics.get_queue_depth()
    
    # Build response (always HTTP 200, even if CRITICAL)
    response = {
        "system_status": system_status,
        "ingest_rate_eps": round(ingest_rate_eps, 2),
        "db_write_latency_ms": round(db_write_latency_ms, 2),
        "queue_depth": queue_depth,
        "agent_heartbeat_lag_sec": round(heartbeat_lag_sec, 2) if heartbeat_lag_sec is not None else None
    }
    
    return response
