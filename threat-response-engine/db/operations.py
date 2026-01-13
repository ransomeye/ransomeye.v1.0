#!/usr/bin/env python3
"""
RansomEye v1.0 Threat Response Engine - Database Operations
AUTHORITATIVE: Database operations for TRE actions and rollbacks
Python 3.10+ only
"""

import os
import sys
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.db.safety import (create_write_connection, IsolationLevel,
                                   execute_write_operation, begin_transaction,
                                   commit_transaction, rollback_transaction)
    from common.logging import setup_logging
    _common_db_safety_available = True
    _logger = setup_logging('tre-db')
except ImportError:
    _common_db_safety_available = False
    _logger = None
    def create_write_connection(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def execute_write_operation(*args, **kwargs): raise RuntimeError("Database safety utilities not available")
    def begin_transaction(*args, **kwargs): pass
    def commit_transaction(*args, **kwargs): pass
    def rollback_transaction(*args, **kwargs): pass
    class IsolationLevel: READ_COMMITTED = 2


def store_response_action(conn, action: Dict[str, Any]) -> str:
    """
    Store response action in database.
    
    Args:
        conn: Database connection
        action: Response action dictionary
        
    Returns:
        Action ID
    """
    def _do_store():
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO response_actions (
                    action_id, policy_decision_id, incident_id, machine_id,
                    command_type, command_payload, command_signature, command_signing_key_id,
                    required_authority, authority_action_id, execution_status,
                    executed_at, executed_by, rollback_capable, rollback_id, ledger_entry_id
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                action['action_id'],
                action['policy_decision_id'],
                action['incident_id'],
                action['machine_id'],
                action['command_type'],
                json.dumps(action['command_payload']),
                action['command_signature'],
                action['command_signing_key_id'],
                action['required_authority'],
                action.get('authority_action_id'),
                action['execution_status'],
                action.get('executed_at'),
                action.get('executed_by', 'TRE'),
                action.get('rollback_capable', True),
                action.get('rollback_id'),
                action['ledger_entry_id']
            ))
            return action['action_id']
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_write_operation(conn, "store_response_action", _do_store, _logger)
    else:
        begin_transaction(conn, _logger)
        try:
            result = _do_store()
            commit_transaction(conn, _logger, "store_response_action")
            return result
        except Exception as e:
            rollback_transaction(conn, _logger, "store_response_action")
            raise


def update_action_status(conn, action_id: str, status: str, executed_at: Optional[datetime] = None):
    """
    Update action execution status.
    
    Args:
        conn: Database connection
        action_id: Action identifier
        status: New execution status
        executed_at: Optional execution timestamp
    """
    def _do_update():
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE response_actions
                SET execution_status = %s, executed_at = %s
                WHERE action_id = %s
            """, (status, executed_at, action_id))
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_write_operation(conn, "update_action_status", _do_update, _logger)
    else:
        begin_transaction(conn, _logger)
        try:
            _do_update()
            commit_transaction(conn, _logger, "update_action_status")
        except Exception as e:
            rollback_transaction(conn, _logger, "update_action_status")
            raise


def store_rollback_record(conn, rollback: Dict[str, Any]) -> str:
    """
    Store rollback record in database.
    
    Args:
        conn: Database connection
        rollback: Rollback record dictionary
        
    Returns:
        Rollback ID
    """
    def _do_store():
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO rollback_records (
                    rollback_id, action_id, rollback_reason, rollback_type,
                    rollback_payload, rollback_signature, rollback_signing_key_id,
                    required_authority, authority_action_id, rollback_status,
                    rolled_back_at, rolled_back_by, ledger_entry_id
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                rollback['rollback_id'],
                rollback['action_id'],
                rollback['rollback_reason'],
                rollback['rollback_type'],
                json.dumps(rollback['rollback_payload']),
                rollback['rollback_signature'],
                rollback['rollback_signing_key_id'],
                rollback['required_authority'],
                rollback.get('authority_action_id'),
                rollback['rollback_status'],
                rollback.get('rolled_back_at'),
                rollback.get('rolled_back_by', 'TRE'),
                rollback['ledger_entry_id']
            ))
            
            # Update action status to ROLLED_BACK
            cur.execute("""
                UPDATE response_actions
                SET execution_status = 'ROLLED_BACK', rollback_id = %s
                WHERE action_id = %s
            """, (rollback['rollback_id'], rollback['action_id']))
            
            return rollback['rollback_id']
        finally:
            cur.close()
    
    if _common_db_safety_available:
        return execute_write_operation(conn, "store_rollback_record", _do_store, _logger)
    else:
        begin_transaction(conn, _logger)
        try:
            result = _do_store()
            commit_transaction(conn, _logger, "store_rollback_record")
            return result
        except Exception as e:
            rollback_transaction(conn, _logger, "store_rollback_record")
            raise


def get_action_by_id(conn, action_id: str) -> Optional[Dict[str, Any]]:
    """
    Get action by ID.
    
    Args:
        conn: Database connection
        action_id: Action identifier
        
    Returns:
        Action dictionary or None if not found
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                action_id, policy_decision_id, incident_id, machine_id,
                command_type, command_payload, command_signature, command_signing_key_id,
                required_authority, authority_action_id, execution_status,
                executed_at, executed_by, rollback_capable, rollback_id, ledger_entry_id,
                created_at
            FROM response_actions
            WHERE action_id = %s
        """, (action_id,))
        
        row = cur.fetchone()
        if not row:
            return None
        
        columns = [desc[0] for desc in cur.description]
        action = dict(zip(columns, row))
        
        # Parse JSONB fields
        if isinstance(action['command_payload'], str):
            action['command_payload'] = json.loads(action['command_payload'])
        
        return action
    finally:
        cur.close()
