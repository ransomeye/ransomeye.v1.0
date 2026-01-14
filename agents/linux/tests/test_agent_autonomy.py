#!/usr/bin/env python3
"""
RansomEye v1.0 GA - Agent Autonomy Validation Tests
AUTHORITATIVE: Tests proving agent autonomous enforcement when Core is offline

GA-BLOCKING: These tests prove that:
1. Agent enforces policy without Core (autonomous enforcement)
2. No fail-open paths exist
3. Agent does not crash
4. Behavior is deterministic and logged
"""

import sys
import os
import json
import time
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Add parent directory to path for imports
_agents_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_agents_dir))

from linux.command_gate import CommandGate, CommandRejectionError


def test_agent_enforces_policy_when_core_offline():
    """
    GA-BLOCKING: Test that agent enforces cached policy when Core is offline.
    
    Scenario:
    1. Agent starts with cached policy
    2. Core becomes unreachable
    3. Prohibited action is attempted
    4. Agent blocks action (fail-closed)
    """
    # Setup: Create temporary policy cache
    with tempfile.TemporaryDirectory() as tmpdir:
        policy_path = Path(tmpdir) / 'cached_policy.json'
        policy = {
            'version': '1.0',
            'prohibited_actions': ['BLOCK_PROCESS', 'QUARANTINE_FILE'],
            'allowed_actions': [],
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'integrity_hash': None
        }
        with open(policy_path, 'w') as f:
            json.dump(policy, f)
        
        # Create command gate with cached policy
        gate = CommandGate(
            tre_public_key=b'fake_key',
            tre_key_id='fake_key_id',
            agent_id='test_agent',
            audit_log_path=Path(tmpdir) / 'audit.log',
            cached_policy_path=policy_path,
            core_endpoint='http://localhost:9999/health'  # Unreachable endpoint
        )
        
        # Mock signature verification to pass (focus on policy enforcement)
        gate.verifier = MagicMock()
        gate.verifier.verify = MagicMock(return_value=True)
        
        # Create prohibited command
        prohibited_command = {
            'command_id': 'test-command-1',
            'action_type': 'BLOCK_PROCESS',  # Prohibited action
            'target': {'process_id': 1234},
            'incident_id': None,
            'tre_mode': 'FULL_ENFORCE',
            'issued_by_user_id': 'user-123',
            'issued_by_role': 'SECURITY_ANALYST',
            'issued_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'expires_at': (datetime.now(timezone.utc).replace(tzinfo=timezone.utc) + 
                          __import__('datetime').timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
            'rollback_token': 'test-token',
            'signature': 'fake_signature'
        }
        
        # GA-BLOCKING: Attempt prohibited action when Core is offline
        try:
            gate.receive_command(prohibited_command)
            assert False, "GA-BLOCKING FAILURE: Agent should have rejected prohibited action when Core is offline"
        except CommandRejectionError as e:
            # Verify error message indicates autonomous enforcement
            assert 'Core offline' in str(e) or 'autonomous' in str(e).lower() or 'prohibited' in str(e).lower()
            print("✓ Test passed: Agent blocked prohibited action when Core is offline")
            return True
        
        assert False, "GA-BLOCKING FAILURE: Agent did not reject prohibited action"


def test_agent_default_deny_when_no_policy():
    """
    GA-BLOCKING: Test that agent defaults to DENY when no policy exists.
    
    Scenario:
    1. Agent starts with no cached policy
    2. Core becomes unreachable
    3. Any action is attempted
    4. Agent blocks action (default deny)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        policy_path = Path(tmpdir) / 'cached_policy.json'
        
        # Create command gate without cached policy (will create default deny)
        gate = CommandGate(
            tre_public_key=b'fake_key',
            tre_key_id='fake_key_id',
            agent_id='test_agent',
            audit_log_path=Path(tmpdir) / 'audit.log',
            cached_policy_path=policy_path,
            core_endpoint='http://localhost:9999/health'  # Unreachable endpoint
        )
        
        # Mock signature verification
        gate.verifier = MagicMock()
        gate.verifier.verify = MagicMock(return_value=True)
        
        # Verify default policy is deny-all
        assert gate.cached_policy['allowed_actions'] == [], "Default policy should have no allowed actions"
        assert len(gate.cached_policy['prohibited_actions']) > 0, "Default policy should prohibit actions"
        
        # Create any command
        test_command = {
            'command_id': 'test-command-2',
            'action_type': 'BLOCK_PROCESS',
            'target': {'process_id': 1234},
            'incident_id': None,
            'tre_mode': 'FULL_ENFORCE',
            'issued_by_user_id': 'user-123',
            'issued_by_role': 'SECURITY_ANALYST',
            'issued_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'expires_at': (datetime.now(timezone.utc).replace(tzinfo=timezone.utc) + 
                          __import__('datetime').timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
            'rollback_token': 'test-token',
            'signature': 'fake_signature'
        }
        
        # GA-BLOCKING: Attempt action when no policy exists (should default deny)
        try:
            gate.receive_command(test_command)
            assert False, "GA-BLOCKING FAILURE: Agent should have default denied action when no policy exists"
        except CommandRejectionError as e:
            # Verify error message indicates default deny
            assert 'default deny' in str(e).lower() or 'no policy' in str(e).lower() or 'prohibited' in str(e).lower()
            print("✓ Test passed: Agent default denied action when no policy exists")
            return True
        
        assert False, "GA-BLOCKING FAILURE: Agent did not default deny action"


def test_agent_does_not_crash_when_core_offline():
    """
    GA-BLOCKING: Test that agent does not crash when Core is offline.
    
    Scenario:
    1. Agent starts normally
    2. Core becomes unreachable
    3. Multiple commands are processed
    4. Agent remains running (no crash)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        policy_path = Path(tmpdir) / 'cached_policy.json'
        policy = {
            'version': '1.0',
            'prohibited_actions': ['BLOCK_PROCESS'],
            'allowed_actions': [],
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        with open(policy_path, 'w') as f:
            json.dump(policy, f)
        
        gate = CommandGate(
            tre_public_key=b'fake_key',
            tre_key_id='fake_key_id',
            agent_id='test_agent',
            audit_log_path=Path(tmpdir) / 'audit.log',
            cached_policy_path=policy_path,
            core_endpoint='http://localhost:9999/health'  # Unreachable
        )
        
        # Mock signature verification
        gate.verifier = MagicMock()
        gate.verifier.verify = MagicMock(return_value=True)
        
        # GA-BLOCKING: Process multiple commands (agent should not crash)
        for i in range(10):
            test_command = {
                'command_id': f'test-command-{i}',
                'action_type': 'BLOCK_PROCESS',
                'target': {'process_id': 1234},
                'incident_id': None,
                'tre_mode': 'FULL_ENFORCE',
                'issued_by_user_id': 'user-123',
                'issued_by_role': 'SECURITY_ANALYST',
                'issued_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'expires_at': (datetime.now(timezone.utc).replace(tzinfo=timezone.utc) + 
                              __import__('datetime').timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
                'rollback_token': 'test-token',
                'signature': 'fake_signature'
            }
            
            try:
                gate.receive_command(test_command)
                assert False, f"GA-BLOCKING FAILURE: Command {i} should have been rejected"
            except CommandRejectionError:
                # Expected - command should be rejected
                pass
        
        # GA-BLOCKING: Agent should still be functional (not crashed)
        assert gate.cached_policy is not None, "Agent should still have cached policy"
        assert gate._is_core_online() == False, "Core should be detected as offline"
        print("✓ Test passed: Agent did not crash when Core is offline")


def test_agent_logs_autonomous_enforcement():
    """
    GA-BLOCKING: Test that agent logs autonomous enforcement explicitly.
    
    Scenario:
    1. Agent starts with cached policy
    2. Core becomes unreachable
    3. Action is attempted
    4. Agent logs explicit autonomous enforcement message
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        policy_path = Path(tmpdir) / 'cached_policy.json'
        audit_log_path = Path(tmpdir) / 'audit.log'
        
        policy = {
            'version': '1.0',
            'prohibited_actions': ['BLOCK_PROCESS'],
            'allowed_actions': [],
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        with open(policy_path, 'w') as f:
            json.dump(policy, f)
        
        gate = CommandGate(
            tre_public_key=b'fake_key',
            tre_key_id='fake_key_id',
            agent_id='test_agent',
            audit_log_path=audit_log_path,
            cached_policy_path=policy_path,
            core_endpoint='http://localhost:9999/health'  # Unreachable
        )
        
        # Mock signature verification
        gate.verifier = MagicMock()
        gate.verifier.verify = MagicMock(return_value=True)
        
        test_command = {
            'command_id': 'test-command-log',
            'action_type': 'BLOCK_PROCESS',
            'target': {'process_id': 1234},
            'incident_id': None,
            'tre_mode': 'FULL_ENFORCE',
            'issued_by_user_id': 'user-123',
            'issued_by_role': 'SECURITY_ANALYST',
            'issued_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'expires_at': (datetime.now(timezone.utc).replace(tzinfo=timezone.utc) + 
                          __import__('datetime').timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
            'rollback_token': 'test-token',
            'signature': 'fake_signature'
        }
        
        # GA-BLOCKING: Attempt action and verify logging
        try:
            gate.receive_command(test_command)
            assert False, "GA-BLOCKING FAILURE: Command should have been rejected"
        except CommandRejectionError:
            pass
        
        # GA-BLOCKING: Verify audit log contains autonomous enforcement entry
        assert audit_log_path.exists(), "Audit log should exist"
        with open(audit_log_path, 'r') as f:
            log_entries = [json.loads(line) for line in f]
        
        # Find rejection entry
        rejection_entries = [e for e in log_entries if e.get('outcome') == 'REJECTED']
        assert len(rejection_entries) > 0, "Audit log should contain rejection entry"
        
        # Verify reason contains autonomous enforcement indicator
        rejection_reason = rejection_entries[0].get('reason', '')
        assert 'Core offline' in rejection_reason or 'autonomous' in rejection_reason.lower() or 'prohibited' in rejection_reason.lower(), \
            f"GA-BLOCKING FAILURE: Audit log should contain autonomous enforcement message. Got: {rejection_reason}"
        
        print("✓ Test passed: Agent logged autonomous enforcement explicitly")


def main():
    """Run all GA-blocking tests."""
    print("=" * 80)
    print("RansomEye v1.0 GA - Agent Autonomy Validation Tests")
    print("=" * 80)
    print()
    
    tests = [
        test_agent_enforces_policy_when_core_offline,
        test_agent_default_deny_when_no_policy,
        test_agent_does_not_crash_when_core_offline,
        test_agent_logs_autonomous_enforcement
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed > 0:
        print("GA-BLOCKING: Agent autonomy validation FAILED")
        sys.exit(1)
    else:
        print("GA-BLOCKING: Agent autonomy validation PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
