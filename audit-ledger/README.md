# RansomEye Audit Ledger

**AUTHORITATIVE:** System-wide append-only, tamper-evident audit ledger with cryptographic signatures

## Overview

The RansomEye Audit Ledger is a foundational subsystem that provides **court/compliance-grade integrity** for all security-relevant actions in the RansomEye platform. It serves as the **root of trust** for the entire system, recording every action that affects security, compliance, or forensic analysis.

## Threat Model

The Audit Ledger is designed to protect against:

1. **Tampering**: Modification or deletion of historical entries
2. **Forgery**: Creation of fake entries with valid signatures
3. **Replay Attacks**: Re-submission of old entries
4. **Repudiation**: Denial of actions that were performed
5. **Chain-of-Custody Breaks**: Gaps in audit trail

### Security Guarantees

- **Append-Only**: Entries cannot be modified or deleted after writing
- **Hash-Chained**: Each entry references the previous entry's hash, creating an unbreakable chain
- **Cryptographically Signed**: Every entry is signed with ed25519, providing non-repudiation
- **Tamper-Evident**: Any modification to an entry breaks the hash chain and signature verification
- **Deterministic Verification**: Verification is fully deterministic and requires no trust assumptions

## Tamper-Evidence Guarantees

The ledger provides **cryptographic proof** of tampering:

1. **Hash Chain Integrity**: Each entry's `prev_entry_hash` must match the previous entry's `entry_hash`. Any modification breaks this chain.

2. **Entry Hash Integrity**: Each entry's `entry_hash` is calculated from the canonical JSON representation. Any modification to entry content changes the hash.

3. **Signature Integrity**: Each entry's `signature` is an ed25519 signature of the `entry_hash`. Any modification invalidates the signature.

4. **Verification Process**: The verification tool (`verify_ledger.py`) replays the entire ledger and verifies:
   - Hash chain integrity (prev_entry_hash matches previous entry_hash)
   - Entry hash integrity (stored hash matches calculated hash)
   - Signature validity (signature verifies against public key)

**Result**: Any tampering is **detectable** and **provable** through cryptographic verification.

## Key Management Model

### Key Generation

- **Key Type**: ed25519 (Edwards-curve Digital Signature Algorithm)
- **Key Generation**: Per-installation keypair generated at first use
- **Key Storage**:
  - Private key: `ledger-signing-key.pem` (owner read/write only, 0o600)
  - Public key: `ledger-signing-key.pub` (readable, 0o644)
  - Key ID: `ledger-signing-key.id` (SHA256 hash of public key)

### Private Key Security

- **Never Logged**: Private key is never logged or printed
- **Never Exported**: Private key is never exported or transmitted
- **Secure Storage**: Private key file has restrictive permissions (0o600)
- **In-Memory Only**: Private key exists in memory only during signing operations

### Public Key Usage

- **Verification**: Public key is used for signature verification
- **Exportable**: Public key can be exported for external verification
- **Key ID**: SHA256 hash of public key serves as `signing_key_id` in entries

### Key Rotation

Key rotation is supported with ledger continuity:

1. Generate new keypair
2. Record key rotation event in ledger (signed with old key)
3. Switch to new key for subsequent entries
4. Verification requires both public keys for full verification

## Failure Semantics (Fail-Closed)

The Audit Ledger follows **fail-closed** semantics:

1. **Write Failures**: If an entry cannot be written (disk full, permission error, etc.), the operation **fails** and raises an exception. No partial writes are allowed.

2. **Verification Failures**: If verification fails at any point, the entire ledger is considered **invalid**. Verification stops at the first failure and reports the failure location.

3. **No Silent Failures**: All failures are explicit exceptions. No silent degradation or fallback behavior.

4. **Read-Only Mode**: Ledger can be mounted read-only for verification without risk of modification.

## How Verification Works

### Verification Process

The `verify_ledger.py` tool performs deterministic verification:

1. **Load Public Key**: Load public key from key directory
2. **Read All Entries**: Read entries sequentially from ledger file
3. **For Each Entry**:
   - Validate JSON schema (if schema provided)
   - Calculate entry hash from canonical JSON
   - Verify stored hash matches calculated hash
   - Verify signature using public key
   - Verify hash chain (prev_entry_hash matches previous entry_hash)
4. **Produce Report**: Generate pass/fail report with failure locations

### Verification Output

Verification produces:
- **PASS/FAIL Status**: Overall verification result
- **Total Entries**: Number of entries processed
- **Verified Entries**: Number of entries that passed verification
- **Failure Details**: List of all failures with entry IDs and error messages
- **First Failure Location**: Entry ID and location of first failure

### Deterministic Verification

Verification is **fully deterministic**:
- No random elements
- No network dependencies
- No database dependencies
- No trust assumptions
- Same input always produces same output

## Legal / Compliance Positioning

The Audit Ledger is designed for **legal and compliance** use cases:

1. **Chain of Custody**: Complete, unbroken chain of all security-relevant actions
2. **Non-Repudiation**: Cryptographic signatures prevent denial of actions
3. **Tamper Evidence**: Cryptographic proof of any tampering attempts
4. **Forensic Integrity**: Entries cannot be modified or deleted after creation
5. **Court Admissibility**: Deterministic verification and cryptographic signatures support legal admissibility

### Compliance Standards

The ledger supports compliance with:
- **SOC 2**: Audit trail requirements
- **ISO 27001**: Security event logging
- **HIPAA**: Audit controls for healthcare data
- **PCI DSS**: Audit trail for payment card data
- **GDPR**: Audit trail for data processing activities

## Architecture

### Components

1. **Schema** (`schema/ledger-entry.schema.json`): Frozen JSON schema defining ledger entry structure
2. **Cryptography** (`crypto/`):
   - `key_manager.py`: Keypair generation and management
   - `signer.py`: Entry signing with ed25519
   - `verifier.py`: Signature and hash verification
3. **Storage** (`storage/append_only_store.py`): Append-only file-based storage
4. **CLI Tools** (`cli/`):
   - `verify_ledger.py`: Ledger verification tool
   - `export_ledger.py`: Ledger export tool
5. **Integration API** (`api.py`): Single, minimal append API for components

### Storage Backend

- **File-Based**: Append-only log file (one entry per line, JSON format)
- **Write-Once Semantics**: Entries written once and never modified
- **fsync**: All writes are synced to disk immediately
- **Read-Only Mount**: Supports read-only filesystem mounts for verification

### Entry Structure

Every ledger entry contains:

- `ledger_entry_id`: UUID v4 identifier
- `timestamp`: RFC3339 UTC timestamp
- `component`: Component name (core, linux-agent, etc.)
- `component_instance_id`: Component instance identifier
- `action_type`: Action type (installer_install, service_start, etc.)
- `subject`: Subject of action (incident_id, model_id, etc.)
- `actor`: Actor that performed action (system, user, module, etc.)
- `payload`: Action-specific payload data
- `prev_entry_hash`: SHA256 hash of previous entry (empty for first entry)
- `entry_hash`: SHA256 hash of this entry (canonical JSON)
- `signature`: Base64-encoded ed25519 signature
- `signing_key_id`: SHA256 hash of public key

**No Optional Fields**: All fields are mandatory. No placeholders or mock data.

## Usage

### Integration API

Components use the single, minimal append API:

```python
from audit_ledger.api import append_entry

entry = append_entry(
    component='core',
    component_instance_id='hostname.example.com',
    action_type='service_start',
    subject={'type': 'service', 'id': 'ransomeye-core'},
    actor={'type': 'system', 'identifier': 'systemd'},
    payload={'service_name': 'ransomeye-core', 'pid': 12345},
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    key_dir=Path('/var/lib/ransomeye/audit/keys')
)
```

### Verification

Verify ledger integrity:

```bash
python3 audit-ledger/cli/verify_ledger.py \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --key-dir /var/lib/ransomeye/audit/keys \
    --schema audit-ledger/schema/ledger-entry.schema.json \
    --output verification-report.json
```

### Export

Export ledger entries:

```bash
python3 audit-ledger/cli/export_ledger.py \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --output exported-ledger.json \
    --format json
```

## Recorded Actions

The ledger records **all security-relevant actions**:

1. **Installer Actions**: install, uninstall, upgrade
2. **Service Lifecycle**: start, stop, restart, crash, health check
3. **Policy Decisions**: recommendation, enforcement, simulation, override
4. **AI Model Lifecycle**: register, promote, revoke, inference
5. **Playbook Execution**: planned, executed, rolled back, failed
6. **Forensic Access**: memory dump, disk artifact read, artifact access
7. **Administrative Actions**: config change, module load/unload, user action, privilege escalation
8. **Correlation Events**: incident created, updated, resolved
9. **Ingest Events**: event received, rejected, validated

**No Silent Actions**: Every security-relevant action must be recorded.

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **cryptography**: Required for ed25519 signing/verification
  - Install: `pip install cryptography`
- **jsonschema**: Optional, for schema validation in verification
  - Install: `pip install jsonschema`

## File Structure

```
audit-ledger/
├── schema/
│   └── ledger-entry.schema.json    # Frozen JSON schema
├── crypto/
│   ├── __init__.py
│   ├── key_manager.py              # Keypair generation and management
│   ├── signer.py                    # Entry signing
│   └── verifier.py                  # Signature verification
├── storage/
│   ├── __init__.py
│   └── append_only_store.py         # Append-only storage
├── cli/
│   ├── __init__.py
│   ├── verify_ledger.py             # Verification tool
│   └── export_ledger.py             # Export tool
├── api.py                           # Integration API
└── README.md                        # This file
```

## Security Considerations

1. **Private Key Protection**: Private key must be protected with restrictive file permissions (0o600)
2. **Ledger File Protection**: Ledger file should be protected from unauthorized modification
3. **Read-Only Verification**: Use read-only mounts for verification to prevent accidental modification
4. **Key Rotation**: Rotate keys periodically and record rotation in ledger
5. **Backup**: Backup ledger file and keys securely (encrypted, off-site)

## Limitations

1. **File-Based Storage**: Phase A uses file-based storage. Future phases may add database-backed storage.
2. **Single Keypair**: Phase A uses single keypair per installation. Key rotation support is planned.
3. **No Compression**: Ledger entries are stored uncompressed. Compression may be added in future phases.

## Future Enhancements

- Database-backed storage for high-volume deployments
- Compression for large ledgers
- Key rotation with full continuity
- Distributed ledger support
- Real-time verification monitoring

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Audit Ledger documentation.
