#!/usr/bin/env python3
"""
RansomEye v1.0 Credential Rotation Script
AUTHORITATIVE: Rotate exposed credentials and generate rotation log
Phase-9: Complete credential rotation with audit trail
"""

import os
import sys
import json
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


def generate_secure_password(length: int = 32) -> str:
    """Generate secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Remove ambiguous characters
    alphabet = alphabet.replace('"', '').replace("'", '').replace('\\', '').replace('`', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_secure_signing_key(length: int = 64) -> str:
    """Generate secure random signing key."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Remove ambiguous characters
    alphabet = alphabet.replace('"', '').replace("'", '').replace('\\', '').replace('`', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def rotate_credential(
    credential_id: str,
    credential_type: str,
    old_value_hash: Optional[str] = None,
    rotation_reason: str = "Phase-9 credential remediation"
) -> Dict[str, Any]:
    """
    Rotate a credential.
    
    Returns:
        Dictionary with new credential and rotation metadata
    """
    if credential_type == "database_password":
        new_value = generate_secure_password(32)
    elif credential_type == "signing_key":
        new_value = generate_secure_signing_key(64)
    elif credential_type == "api_key":
        new_value = generate_secure_password(40)
    else:
        new_value = generate_secure_password(32)
    
    # Hash the new value for logging (never log actual value)
    import hashlib
    new_value_hash = hashlib.sha256(new_value.encode()).hexdigest()
    
    return {
        'credential_id': credential_id,
        'credential_type': credential_type,
        'old_value_hash': old_value_hash,
        'new_value_hash': new_value_hash,
        'rotation_date': datetime.now(timezone.utc).isoformat(),
        'rotation_reason': rotation_reason,
        'new_value': new_value  # Only for immediate use, not stored in log
    }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Credential Rotation Script'
    )
    parser.add_argument(
        '--credential-id',
        required=True,
        help='Credential identifier (e.g., test_db_password)'
    )
    parser.add_argument(
        '--credential-type',
        required=True,
        choices=['database_password', 'signing_key', 'api_key', 'other'],
        help='Type of credential'
    )
    parser.add_argument(
        '--rotation-reason',
        default='Phase-9 credential remediation',
        help='Reason for rotation'
    )
    parser.add_argument(
        '--log-path',
        type=Path,
        default=Path('security/credential-rotation-log.json'),
        help='Path to rotation log file'
    )
    parser.add_argument(
        '--output-secret',
        action='store_true',
        help='Output new credential to stdout (for immediate use)'
    )
    
    args = parser.parse_args()
    
    # Rotate credential
    rotation_result = rotate_credential(
        credential_id=args.credential_id,
        credential_type=args.credential_type,
        rotation_reason=args.rotation_reason
    )
    
    # Load existing log
    log_path = Path(args.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    if log_path.exists():
        with open(log_path, 'r') as f:
            log = json.load(f)
    else:
        log = {
            'version': '1.0',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'rotations': []
        }
    
    # Add rotation entry (without actual credential value)
    rotation_entry = {
        'credential_id': rotation_result['credential_id'],
        'credential_type': rotation_result['credential_type'],
        'old_value_hash': rotation_result['old_value_hash'],
        'new_value_hash': rotation_result['new_value_hash'],
        'rotation_date': rotation_result['rotation_date'],
        'rotation_reason': rotation_result['rotation_reason']
    }
    log['rotations'].append(rotation_entry)
    log['last_updated'] = datetime.now(timezone.utc).isoformat()
    
    # Save log
    with open(log_path, 'w') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Credential rotated: {args.credential_id}")
    print(f"   Type: {args.credential_type}")
    print(f"   Rotation date: {rotation_result['rotation_date']}")
    print(f"   New value hash: {rotation_result['new_value_hash']}")
    print(f"   Log: {log_path}")
    
    if args.output_secret:
        print("")
        print("⚠️  NEW CREDENTIAL (use immediately, then secure):")
        print(rotation_result['new_value'])
        print("")
        print("⚠️  IMPORTANT: Store this credential securely and update:")
        print("   - GitHub Secrets")
        print("   - CI/CD configuration")
        print("   - Test environments")
        print("   - Documentation (remove old values)")


if __name__ == '__main__':
    main()
