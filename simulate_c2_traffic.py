#!/usr/bin/env python3
"""Synthetic C2 Traffic Generator for Phase B Testing"""

import time
import random
import socket
import urllib.request
import urllib.error
from datetime import datetime

class C2Simulator:
    def __init__(self, c2_server="8.8.8.8", beacon_interval=3, jitter=0.3):
        self.c2_server = c2_server
        self.beacon_interval = beacon_interval
        self.jitter = jitter
        self.beacon_count = 0
        
    def generate_beacon(self):
        """Generate single C2 beacon"""
        self.beacon_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        try:
            # Simulate HTTPS beacon (will fail, but generates network activity)
            # Real ransomware beacons to C2 over HTTPS
            req = urllib.request.Request(
                f"https://{self.c2_server}/beacon",
                data=b"infected",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            urllib.request.urlopen(req, timeout=2)
        except (urllib.error.URLError, socket.timeout):
            # Expected failure - we're simulating, not actually contacting C2
            pass
        
        print(f"[{timestamp}] Beacon #{self.beacon_count} → {self.c2_server}")
        
    def run(self, duration=15):
        """Run C2 beaconing simulation"""
        print("=" * 60)
        print("C2 TRAFFIC SIMULATION STARTING")
        print("=" * 60)
        print(f"Target: {self.c2_server}")
        print(f"Interval: {self.beacon_interval}s ± {self.jitter*100}% jitter")
        print(f"Duration: {duration}s")
        print()
        
        start = time.time()
        
        while time.time() - start < duration:
            self.generate_beacon()
            
            # Add jitter (typical C2 behavior to evade detection)
            jitter_factor = 1 + random.uniform(-self.jitter, self.jitter)
            sleep_time = self.beacon_interval * jitter_factor
            time.sleep(sleep_time)
        
        print()
        print("=" * 60)
        print("C2 SIMULATION COMPLETE")
        print("=" * 60)
        print(f"Total beacons: {self.beacon_count}")
        print(f"Actual duration: {time.time() - start:.1f}s")
        print()

if __name__ == "__main__":
    # Use Google DNS as safe target (won't respond to beacons, generates traffic)
    sim = C2Simulator(c2_server="8.8.8.8", beacon_interval=2, jitter=0.2)
    sim.run(duration=10)
