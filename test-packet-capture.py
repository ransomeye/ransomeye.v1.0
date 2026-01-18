#!/usr/bin/env python3
"""Minimal DPI packet capture test for A.3 validation"""

import socket
import struct
import sys
import time
from datetime import datetime

def test_packet_capture(interface, duration=5):
    """Test raw packet capture on interface"""
    print(f"STARTUP: Testing packet capture on {interface} for {duration}s")
    print(f"INFO: Binding to interface: {interface}")
    
    try:
        # Create raw socket (requires CAP_NET_RAW or root)
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
        sock.bind((interface, 0))
        sock.settimeout(1.0)
        
        print(f"INFO: Socket created successfully")
        print(f"INFO: Capturing packets...")
        
        packet_count = 0
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                packet = sock.recvfrom(65565)
                packet_count += 1
                
                # Extract Ethernet header
                eth_header = packet[0][0:14]
                eth = struct.unpack('!6s6s2s', eth_header)
                eth_protocol = socket.ntohs(struct.unpack('H', eth[2])[0])
                
                if packet_count <= 5:  # Show first 5 packets
                    print(f"  Packet {packet_count}: proto=0x{eth_protocol:04x}, len={len(packet[0])}")
                    
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break
        
        sock.close()
        
        print(f"\nRESULT: Captured {packet_count} packets in {duration}s")
        print(f"INFO: Packet capture test PASSED")
        return packet_count
        
    except PermissionError:
        print("ERROR: Insufficient permissions for raw socket (need CAP_NET_RAW or root)")
        sys.exit(1)
    except OSError as e:
        print(f"ERROR: Failed to bind to interface {interface}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Packet capture failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    interface = sys.argv[1] if len(sys.argv) > 1 else "wlp5s0"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    packet_count = test_packet_capture(interface, duration)
    
    if packet_count > 0:
        print("\n✓ Packet capture validation: PASS")
        sys.exit(0)
    else:
        print("\n✗ Packet capture validation: FAIL (no packets captured)")
        sys.exit(1)
