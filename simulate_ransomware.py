#!/usr/bin/env python3
"""Synthetic Ransomware Simulator for Phase B Testing"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class RansomwareSimulator:
    def __init__(self, target_dir, output_dir):
        self.target_dir = Path(target_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.key = os.urandom(32)
        self.stats = {'files': 0, 'bytes': 0, 'start': None, 'end': None}
    
    def encrypt_file(self, file_path):
        plaintext = file_path.read_bytes()
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        pad = 16 - (len(plaintext) % 16)
        padded = plaintext + bytes([pad] * pad)
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        encrypted_path = self.output_dir / f"{file_path.name}.encrypted"
        encrypted_path.write_bytes(iv + ciphertext)
        return encrypted_path
    
    def run(self):
        print("=" * 60)
        print("RANSOMWARE SIMULATION STARTING")
        print("=" * 60)
        self.stats['start'] = datetime.now()
        
        files = list(self.target_dir.glob("*.txt"))
        print(f"Target files: {len(files)}\n")
        
        for idx, f in enumerate(files, 1):
            enc = self.encrypt_file(f)
            size = f.stat().st_size
            self.stats['files'] += 1
            self.stats['bytes'] += size
            print(f"[{idx}/{len(files)}] {f.name} → {enc.name} ({size} bytes)")
        
        self.stats['end'] = datetime.now()
        dur = (self.stats['end'] - self.stats['start']).total_seconds()
        
        print("\n" + "=" * 60)
        print(f"Files: {self.stats['files']}")
        print(f"Bytes: {self.stats['bytes']:,}")
        print(f"Duration: {dur:.2f}s")
        print(f"Rate: {self.stats['files']/dur:.1f} files/s, {self.stats['bytes']/dur/1024:.1f} KB/s")
        
        note = self.output_dir / "README_DECRYPT.txt"
        note.write_text(f"SIMULATION - Key: {self.key.hex()}\nFiles: {self.stats['files']}\n")
        print(f"Ransom note: {note}")
        return True

if __name__ == "__main__":
    sim = RansomwareSimulator(
        "/tmp/ransomware-test/victim-files",
        "/tmp/ransomware-test/encrypted-output"
    )
    sys.exit(0 if sim.run() else 1)
