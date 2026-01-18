#!/usr/bin/env python3
"""Generate NaCl Ed25519 telemetry signing keypair for linux-agent"""

import hashlib
from pathlib import Path
import nacl.signing

# Generate Ed25519 keypair (NaCl format, 32 bytes)
signing_key = nacl.signing.SigningKey.generate()
verify_key = signing_key.verify_key

# Get raw key bytes
private_key_bytes = bytes(signing_key)
public_key_bytes = bytes(verify_key)

# Compute key_id (SHA256 of public key)
key_id = hashlib.sha256(public_key_bytes).hexdigest()

print(f"Key ID: {key_id}")

# Write agent's private key (for signing)
agent_key_dir = Path("/opt/ransomeye-agent/config/keys")
agent_key_dir.mkdir(parents=True, exist_ok=True)
private_key_path = agent_key_dir / "telemetry.key"
private_key_path.write_bytes(private_key_bytes)
private_key_path.chmod(0o600)
print(f"✓ Agent private key: {private_key_path}")

# Write Core's public key (for verification)
core_key_dir = Path("/opt/ransomeye/config/component-keys")
core_key_dir.mkdir(parents=True, exist_ok=True)
public_key_path = core_key_dir / f"{key_id}.pub"
public_key_path.write_bytes(public_key_bytes)
public_key_path.chmod(0o644)
print(f"✓ Core public key: {public_key_path}")

# Write key_id to agent config for reference
key_id_path = agent_key_dir / "telemetry.key_id"
key_id_path.write_text(key_id)
key_id_path.chmod(0o644)
print(f"✓ Key ID file: {key_id_path}")
