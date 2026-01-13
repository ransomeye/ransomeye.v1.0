#!/usr/bin/env python3
"""
RansomEye v1.0 Linux Agent - File Quarantine
AUTHORITATIVE: Quarantines files (immutable quarantine dir)
Python 3.10+ only
"""

import os
import sys
import shutil
import json
import hashlib
from typing import Dict, Any
from pathlib import Path
from datetime import datetime, timezone


class FileQuarantineError(Exception):
    """Exception raised when file quarantine fails."""
    pass


class FileQuarantine:
    """Quarantines files to immutable quarantine directory."""
    
    def __init__(self, rollback_store_path: Path, quarantine_dir: Path):
        self.rollback_store_path = rollback_store_path
        self.rollback_store_path.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir = quarantine_dir
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    def execute(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file quarantine action."""
        target = command.get('target', {})
        file_path = target.get('file_path')
        
        if not file_path:
            raise FileQuarantineError("Missing file_path in target")
        
        original_path = Path(file_path)
        if not original_path.exists():
            raise FileQuarantineError(f"File not found: {file_path}")
        
        # Create rollback artifact BEFORE execution
        rollback_artifact = self._create_rollback_artifact(original_path)
        rollback_token = self._store_rollback_artifact(rollback_artifact, command['command_id'])
        
        # Move file to quarantine
        try:
            quarantine_path = self._move_to_quarantine(original_path)
            rollback_artifact['quarantine_path'] = str(quarantine_path)
            
            return {
                'status': 'SUCCEEDED',
                'file_path': file_path,
                'quarantine_path': str(quarantine_path),
                'rollback_token': rollback_token,
                'executed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        except Exception as e:
            raise FileQuarantineError(f"File quarantine execution failed: {e}") from e
    
    def _create_rollback_artifact(self, file_path: Path) -> Dict[str, Any]:
        """Create rollback artifact (file metadata snapshot)."""
        stat = file_path.stat()
        return {
            'original_path': str(file_path),
            'file_size': stat.st_size,
            'file_mode': stat.st_mode,
            'rollback_type': 'FILE_RESTORE'
        }
    
    def _store_rollback_artifact(self, artifact: Dict[str, Any], command_id: str) -> str:
        """Store rollback artifact and return token."""
        artifact_json = json.dumps(artifact, sort_keys=True)
        rollback_token = hashlib.sha256(artifact_json.encode('utf-8')).hexdigest()
        artifact_path = self.rollback_store_path / f"{rollback_token}.json"
        artifact_path.write_text(artifact_json)
        return rollback_token
    
    def _move_to_quarantine(self, file_path: Path) -> Path:
        """Move file to quarantine directory."""
        quarantine_path = self.quarantine_dir / f"{file_path.name}_{hashlib.sha256(str(file_path).encode()).hexdigest()[:8]}"
        shutil.move(str(file_path), str(quarantine_path))
        return quarantine_path
