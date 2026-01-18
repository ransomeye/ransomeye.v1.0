#!/usr/bin/env python3
"""Generate Ed25519 service auth keys for DPI → Core"""

from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

# Generate keypair
private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Serialize private key (PEM format)
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Serialize public key (PEM format)
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Write keys to Core keys directory (shared)
key_dir = Path("/opt/ransomeye/config/keys")
private_key_path = key_dir / "dpi.key"
public_key_path = key_dir / "dpi.pub"

private_key_path.write_bytes(private_pem)
public_key_path.write_bytes(public_pem)

# Set permissions
private_key_path.chmod(0o640)
public_key_path.chmod(0o644)

print(f"✓ Generated: {private_key_path}")
print(f"✓ Generated: {public_key_path}")
