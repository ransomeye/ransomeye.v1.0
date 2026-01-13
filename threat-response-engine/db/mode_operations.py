#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Mode Operations
AUTHORITATIVE: Database operations for TRE enforcement modes
Python 3.10+ only
"""

import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    from common.db.safety import create_write_connection, IsolationLevel
    _common_available = True
    _logger = setup_logging('tre-mode-ops')
except ImportError:
    _common_available = False
    _logger = None

# Add threat-response-engine to path
_threat_response_path = os.path.join(_project_root, 'threat-response-engine')
if os.path.exists(_threat_response_path) and _threat_response_path not in sys.path:
    sys.path.insert(0, _threat_response_path)

from engine.enforcement_mode import TREMode


def get_current_mode(conn) -> Optional[TREMode]:
    """
    Get current active TRE enforcement mode.
    
    Args:
        conn: Database connection
    
    Returns:
        Current TREMode or None if not set
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT mode FROM tre_execution_modes
            WHERE is_active = TRUE
            ORDER BY changed_at DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            return TREMode(row[0])
        return None


def set_mode(
    conn,
    mode: TREMode,
    changed_by_user_id: str,
    reason: Optional[str] = None,
    ledger_entry_id: str = ''
) -> str:
    """
    Set TRE enforcement mode (deactivates previous active mode).
    
    Args:
        conn: Database connection
        mode: New TRE mode
        changed_by_user_id: User who changed the mode
        reason: Optional reason for change
        ledger_entry_id: Audit ledger entry ID
    
    Returns:
        Mode record ID
    """
    # Deactivate all existing active modes
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE tre_execution_modes
            SET is_active = FALSE
            WHERE is_active = TRUE
        """)
        
        # Insert new active mode
        import uuid
        mode_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO tre_execution_modes (
                mode_id, mode, changed_by_user_id, reason, ledger_entry_id, is_active
            ) VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (mode_id, mode.value, changed_by_user_id, reason, ledger_entry_id))
        
        conn.commit()
        return mode_id


def get_mode_history(conn, limit: int = 10) -> list:
    """
    Get TRE mode change history.
    
    Args:
        conn: Database connection
        limit: Maximum number of records to return
    
    Returns:
        List of mode change records
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT mode_id, mode, changed_by_user_id, changed_at, reason, ledger_entry_id
            FROM tre_execution_modes
            ORDER BY changed_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        return [
            {
                'mode_id': row[0],
                'mode': row[1],
                'changed_by_user_id': row[2],
                'changed_at': row[3].isoformat() if row[3] else None,
                'reason': row[4],
                'ledger_entry_id': row[5]
            }
            for row in rows
        ]
