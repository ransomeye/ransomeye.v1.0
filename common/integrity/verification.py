#!/usr/bin/env python3
"""
RansomEye v1.0 Common Integrity Verification
AUTHORITATIVE: Hash-chain continuity, sequence monotonicity, idempotency verification
Phase 10 requirement: Data integrity hardening, corruption detection
"""

import psycopg2
from typing import Dict, Any, Optional, Tuple


def verify_hash_chain_continuity(conn, component_instance_id: str, prev_hash_sha256: Optional[str], 
                                 sequence: int) -> Tuple[bool, Optional[str]]:
    """
    Verify hash-chain continuity for event.
    
    Phase 10 requirement: Enforce hash-chain continuity checks.
    Contract compliance: prev_hash_sha256 must match previous event's hash_sha256 (if sequence > 0).
    
    Args:
        conn: Database connection
        component_instance_id: Component instance ID (for finding previous events)
        prev_hash_sha256: Previous hash from current event (may be None)
        sequence: Current event sequence number
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    cur = conn.cursor()
    try:
        # Phase 10 requirement: For first event (sequence=0), prev_hash_sha256 must be None
        if sequence == 0:
            if prev_hash_sha256 is not None:
                return False, f"First event (sequence=0) must have prev_hash_sha256=NULL, found: {prev_hash_sha256}"
            return True, None
        
        # Phase 10 requirement: For non-first events (sequence > 0), prev_hash_sha256 must match previous event
        if prev_hash_sha256 is None:
            return False, f"Non-first event (sequence={sequence}) must have prev_hash_sha256 set (not NULL)"
        
        # Find previous event in same component instance
        cur.execute("""
            SELECT event_id, sequence, hash_sha256
            FROM raw_events
            WHERE component_instance_id = %s
            AND sequence = %s
            ORDER BY sequence DESC
            LIMIT 1
        """, (component_instance_id, sequence - 1))
        
        prev_event = cur.fetchone()
        if not prev_event:
            # Previous event not found - check if there are any earlier events for this component instance
            cur.execute("""
                SELECT COUNT(*) FROM raw_events
                WHERE component_instance_id = %s
                AND sequence < %s
            """, (component_instance_id, sequence))
            prev_count = cur.fetchone()[0]
            if prev_count > 0:
                return False, f"Previous event with sequence={sequence-1} not found for component_instance_id={component_instance_id}, but {prev_count} earlier events exist (potential corruption)"
            # This is the first event for this component instance, but sequence > 0 - this is an error
            return False, f"Sequence={sequence} for component_instance_id={component_instance_id} but no previous events found (sequence should be 0 for first event)"
        
        prev_event_hash = prev_event[2]
        
        # Phase 10 requirement: prev_hash_sha256 must match previous event's hash_sha256
        if prev_event_hash != prev_hash_sha256:
            return False, f"Hash chain broken: prev_hash_sha256={prev_hash_sha256} does not match previous event (sequence={sequence-1}) hash={prev_event_hash} for component_instance_id={component_instance_id}"
        
        return True, None
    finally:
        cur.close()


def verify_sequence_monotonicity(conn, component_instance_id: str, sequence: int) -> Tuple[bool, Optional[str]]:
    """
    Verify sequence monotonicity for component instance.
    
    Phase 10 requirement: Enforce sequence monotonicity.
    Contract compliance: Sequence numbers must be monotonically increasing within component instance.
    
    Args:
        conn: Database connection
        component_instance_id: Component instance ID
        sequence: Current sequence number
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    cur = conn.cursor()
    try:
        # Phase 10 requirement: Check for sequence gaps or duplicates
        cur.execute("""
            SELECT MAX(sequence) FROM raw_events
            WHERE component_instance_id = %s
        """, (component_instance_id,))
        
        max_sequence_row = cur.fetchone()
        max_sequence = max_sequence_row[0] if max_sequence_row[0] is not None else -1
        
        # Phase 10 requirement: Sequence must be >= max_sequence (monotonically increasing)
        if sequence <= max_sequence:
            # Check if this sequence already exists (duplicate detection)
            cur.execute("""
                SELECT COUNT(*) FROM raw_events
                WHERE component_instance_id = %s AND sequence = %s
            """, (component_instance_id, sequence))
            dup_count = cur.fetchone()[0]
            if dup_count > 0:
                return False, f"Duplicate sequence {sequence} for component_instance_id {component_instance_id}"
            
            # Sequence is not duplicate but not monotonic (gap or regression)
            return False, f"Sequence monotonicity violation: sequence={sequence} <= max_sequence={max_sequence} for component_instance_id={component_instance_id}"
        
        # Phase 10 requirement: Check for large gaps (potential corruption or missing events)
        if sequence > max_sequence + 1000:
            return False, f"Large sequence gap detected: sequence={sequence}, max_sequence={max_sequence}, gap={sequence - max_sequence} (potential corruption)"
        
        return True, None
    finally:
        cur.close()


def verify_idempotency(conn, event_id: str) -> bool:
    """
    Verify event idempotency (event not already processed).
    
    Phase 10 requirement: Enforce idempotency across restarts.
    Contract compliance: Same event_id must not be processed twice.
    
    Args:
        conn: Database connection
        event_id: Event ID to check
        
    Returns:
        True if event is new (not duplicate), False if already exists
    """
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM raw_events WHERE event_id = %s", (event_id,))
        return cur.fetchone() is None
    finally:
        cur.close()


def detect_corruption(conn, component_instance_id: str) -> Tuple[bool, Optional[str]]:
    """
    Detect data corruption in component instance event chain.
    
    Phase 10 requirement: Detect and log corruption explicitly.
    Contract compliance: No silent acceptance of bad state.
    
    Args:
        conn: Database connection
        component_instance_id: Component instance ID to check
        
    Returns:
        Tuple of (is_corrupted, error_message)
    """
    cur = conn.cursor()
    try:
        # Phase 10 requirement: Check for hash chain breaks
        cur.execute("""
            SELECT e1.event_id, e1.sequence, e1.hash_sha256, e1.prev_hash_sha256,
                   e2.event_id as prev_event_id, e2.hash_sha256 as prev_hash
            FROM raw_events e1
            LEFT JOIN raw_events e2 ON e1.component_instance_id = e2.component_instance_id
                AND e2.sequence = e1.sequence - 1
            WHERE e1.component_instance_id = %s
            AND e1.sequence > 0
            ORDER BY e1.sequence
        """, (component_instance_id,))
        
        events = cur.fetchall()
        for event in events:
            event_id, seq, hash_sha256, prev_hash, prev_event_id, prev_hash_actual = event
            
            if prev_hash is None:
                continue  # First event, prev_hash should be None
            
            if prev_event_id is None:
                return True, f"Hash chain corruption: Event {event_id} (sequence={seq}) has prev_hash_sha256 but previous event not found"
            
            if prev_hash != prev_hash_actual:
                return True, f"Hash chain corruption: Event {event_id} (sequence={seq}) prev_hash_sha256={prev_hash} does not match previous event hash={prev_hash_actual}"
        
        # Phase 10 requirement: Check for sequence gaps
        cur.execute("""
            SELECT sequence, LEAD(sequence) OVER (ORDER BY sequence) as next_sequence
            FROM raw_events
            WHERE component_instance_id = %s
            ORDER BY sequence
        """, (component_instance_id,))
        
        sequences = cur.fetchall()
        for seq_row in sequences:
            seq, next_seq = seq_row
            if next_seq is not None and next_seq != seq + 1:
                return True, f"Sequence gap detected: sequence={seq}, next_sequence={next_seq}, gap={next_seq - seq - 1}"
        
        return False, None
    finally:
        cur.close()
