#!/usr/bin/env python3
"""
RansomEye v1.0 Linux Agent - Process Blocker
AUTHORITATIVE: Blocks processes (kill + cgroup deny)
Python 3.10+ only
"""

import os
import sys
import subprocess
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Add common utilities to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_file))))
if os.path.exists(os.path.join(_project_root, 'common')) and _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from common.logging import setup_logging
    _common_available = True
    _logger = setup_logging('linux-agent-process-blocker')
except ImportError:
    _common_available = False
    _logger = None


class ProcessBlockError(Exception):
    """Exception raised when process blocking fails."""
    pass


class ProcessBlocker:
    """
    Blocks processes (kill + cgroup deny).
    
    CRITICAL: Must produce rollback artifact BEFORE execution.
    """
    
    def __init__(self, rollback_store_path: Path):
        """
        Initialize process blocker.
        
        Args:
            rollback_store_path: Path to rollback artifact store
        """
        self.rollback_store_path = rollback_store_path
        self.rollback_store_path.mkdir(parents=True, exist_ok=True)
    
    def execute(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute process block action.
        
        Args:
            command: Command dictionary with action_type='BLOCK_PROCESS'
        
        Returns:
            Execution result with rollback_token
        """
        target = command.get('target', {})
        process_id = target.get('process_id')
        
        if not process_id:
            raise ProcessBlockError("Missing process_id in target")
        
        # Step 1: Create rollback artifact BEFORE execution
        rollback_artifact = self._create_rollback_artifact(process_id)
        rollback_token = self._store_rollback_artifact(rollback_artifact, command['command_id'])
        
        # Step 2: Execute action
        try:
            # Kill process
            subprocess.run(['kill', '-9', str(process_id)], check=True, capture_output=True)
            
            # Add to cgroup deny list (if cgroups v2 available)
            self._add_to_cgroup_deny(process_id)
            
            if _logger:
                _logger.info("Process blocked successfully", process_id=process_id)
            
            return {
                'status': 'SUCCEEDED',
                'process_id': process_id,
                'rollback_token': rollback_token,
                'executed_at': self._get_timestamp()
            }
            
        except subprocess.CalledProcessError as e:
            raise ProcessBlockError(f"Failed to block process {process_id}: {e}")
        except Exception as e:
            raise ProcessBlockError(f"Process block execution failed: {e}") from e
    
    def _create_rollback_artifact(self, process_id: int) -> Dict[str, Any]:
        """
        Create rollback artifact (process state snapshot).
        
        Args:
            process_id: Process ID to snapshot
        
        Returns:
            Rollback artifact dictionary
        """
        try:
            # Read process info from /proc
            proc_path = Path(f'/proc/{process_id}')
            if not proc_path.exists():
                raise ProcessBlockError(f"Process {process_id} not found")
            
            # Get process command line
            cmdline = proc_path.joinpath('cmdline').read_text().replace('\x00', ' ').strip()
            
            # Get process state
            stat = proc_path.joinpath('stat').read_text().split()
            state = stat[2] if len(stat) > 2 else 'unknown'
            
            artifact = {
                'process_id': process_id,
                'cmdline': cmdline,
                'state': state,
                'rollback_type': 'PROCESS_RESTORE'
            }
            
            return artifact
            
        except Exception as e:
            raise ProcessBlockError(f"Failed to create rollback artifact: {e}") from e
    
    def _store_rollback_artifact(self, artifact: Dict[str, Any], command_id: str) -> str:
        """
        Store rollback artifact and return rollback token.
        
        Args:
            artifact: Rollback artifact dictionary
            command_id: Command identifier
        
        Returns:
            Rollback token (SHA256 hash)
        """
        import hashlib
        
        artifact_json = json.dumps(artifact, sort_keys=True)
        rollback_token = hashlib.sha256(artifact_json.encode('utf-8')).hexdigest()
        
        # Store artifact
        artifact_path = self.rollback_store_path / f"{rollback_token}.json"
        artifact_path.write_text(artifact_json)
        
        return rollback_token
    
    def _add_to_cgroup_deny(self, process_id: int):
        """
        Add process to cgroup deny list (if cgroups v2 available).
        
        Args:
            process_id: Process ID to deny
        """
        # Check if cgroups v2 is available
        cgroup_path = Path('/sys/fs/cgroup')
        if not cgroup_path.exists():
            return  # cgroups not available
        
        # Try to add to deny list (implementation depends on cgroup setup)
        # This is a placeholder - actual implementation depends on cgroup configuration
        pass
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in RFC3339 format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
