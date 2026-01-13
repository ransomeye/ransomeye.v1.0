#!/usr/bin/env python3
"""
MISHKA Training - Training with Session Limits
AUTHORITATIVE: Training with 5-hour session limit and daily tracking
"""

import json
import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, date
import argparse
import subprocess
import sys
import signal
import os

class TrainingSessionManager:
    """Manage training sessions with time limits."""
    
    def __init__(self, session_file: Path):
        self.session_file = Path(session_file)
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.max_session_hours = 1.0  # 1 hour per session
        self.max_daily_hours = 5.0  # Still 5 hours per day max
    
    def load_data(self) -> Dict[str, Any]:
        """Load session data."""
        if self.session_file.exists():
            with open(self.session_file, 'r') as f:
                return json.load(f)
        return {
            'sessions': [],
            'daily_totals': {},
            'total_hours': 0.0
        }
    
    def save_data(self, data: Dict[str, Any]):
        """Save session data."""
        with open(self.session_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_today_total(self) -> float:
        """Get today's training hours."""
        data = self.load_data()
        today = date.today().isoformat()
        return data['daily_totals'].get(today, 0.0)
    
    def can_start(self) -> tuple[bool, str]:
        """Check if can start session."""
        today_total = self.get_today_total()
        
        if today_total >= self.max_daily_hours:
            return False, f"Daily limit reached: {today_total:.2f}/{self.max_daily_hours} hours"
        
        remaining = self.max_daily_hours - today_total
        session_limit = min(self.max_session_hours, remaining)
        
        if session_limit < 0.5:
            return False, f"Less than 30 minutes remaining: {remaining:.2f} hours"
        
        return True, f"Can start. Session limit: {session_limit:.2f} hours, Remaining today: {remaining:.2f} hours"
    
    def start_session(self) -> Dict[str, Any]:
        """Start new session."""
        can_start, reason = self.can_start()
        if not can_start:
            raise ValueError(f"Cannot start: {reason}")
        
        today_total = self.get_today_total()
        remaining = self.max_daily_hours - today_total
        session_limit = min(self.max_session_hours, remaining)
        
        session = {
            'session_id': f"session_{int(time.time())}",
            'start_time': datetime.now().isoformat(),
            'start_timestamp': time.time(),
            'max_hours': session_limit,
            'status': 'running'
        }
        
        data = self.load_data()
        data['sessions'].append(session)
        self.save_data(data)
        
        return session
    
    def end_session(self, session_id: str, elapsed_hours: float):
        """End session."""
        data = self.load_data()
        today = date.today().isoformat()
        
        for session in data['sessions']:
            if session['session_id'] == session_id:
                session['elapsed_hours'] = elapsed_hours
                session['status'] = 'completed'
                session['end_time'] = datetime.now().isoformat()
                
                if today not in data['daily_totals']:
                    data['daily_totals'][today] = 0.0
                data['daily_totals'][today] += elapsed_hours
                data['total_hours'] += elapsed_hours
                break
        
        self.save_data(data)
    
    def get_status(self) -> Dict[str, Any]:
        """Get training status."""
        data = self.load_data()
        today = date.today().isoformat()
        today_total = data['daily_totals'].get(today, 0.0)
        
        return {
            'today_total': today_total,
            'daily_limit': self.max_daily_hours,
            'remaining_today': self.max_daily_hours - today_total,
            'total_hours': data['total_hours'],
            'total_sessions': len(data['sessions'])
        }


def run_training_with_limits(config_path: Path, session_manager: TrainingSessionManager):
    """Run training with time limits."""
    # Check if can start
    can_start, reason = session_manager.can_start()
    if not can_start:
        print(f"❌ {reason}")
        return 1
    
    # Start session
    session = session_manager.start_session()
    start_time = time.time()
    
    status = session_manager.get_status()
    
    print("="*60)
    print("MISHKA Training Session")
    print("="*60)
    print(f"Session ID: {session['session_id']}")
    print(f"Session Limit: {session['max_hours']:.2f} hours")
    print(f"Today's Total: {status['today_total']:.2f}/{status['daily_limit']:.2f} hours")
    print(f"Remaining Today: {status['remaining_today']:.2f} hours")
    print("="*60)
    print()
    
    # Run training in subprocess with time monitoring
    training_process = None
    
    def timeout_handler(signum, frame):
        """Handle timeout."""
        if training_process:
            print("\n⏰ Time limit reached. Stopping training gracefully...")
            training_process.terminate()
            training_process.wait(timeout=30)
    
    signal.signal(signal.SIGALRM, timeout_handler)
    
    try:
        # Set alarm for max session time
        max_seconds = int(session['max_hours'] * 3600)
        signal.alarm(max_seconds)
        
        # Run training
        training_process = subprocess.Popen(
            [sys.executable, 'scripts/train_phase1.py', '--config', str(config_path)],
            cwd=Path(__file__).parent.parent
        )
        
        # Wait for completion or timeout
        training_process.wait()
        
        # Cancel alarm
        signal.alarm(0)
        
        elapsed_hours = (time.time() - start_time) / 3600.0
        session_manager.end_session(session['session_id'], elapsed_hours)
        
        if training_process.returncode == 0:
            print(f"\n✅ Training completed: {elapsed_hours:.2f} hours")
            return 0
        else:
            print(f"\n⚠️  Training ended: {elapsed_hours:.2f} hours (exit code: {training_process.returncode})")
            return training_process.returncode
            
    except KeyboardInterrupt:
        signal.alarm(0)
        if training_process:
            training_process.terminate()
        elapsed_hours = (time.time() - start_time) / 3600.0
        session_manager.end_session(session['session_id'], elapsed_hours)
        print(f"\n⏸️  Training interrupted: {elapsed_hours:.2f} hours")
        return 1
    except Exception as e:
        signal.alarm(0)
        elapsed_hours = (time.time() - start_time) / 3600.0
        session_manager.end_session(session['session_id'], elapsed_hours)
        print(f"\n❌ Training error: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Training with session limits')
    parser.add_argument(
        '--config',
        type=Path,
        default=Path(__file__).parent.parent / 'configs' / 'training_config.yaml',
        help='Training config file'
    )
    parser.add_argument(
        '--session-file',
        type=Path,
        default=Path(__file__).parent.parent / 'training_sessions.json',
        help='Session tracking file'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show status and exit'
    )
    
    args = parser.parse_args()
    
    session_manager = TrainingSessionManager(args.session_file)
    
    if args.status:
        status = session_manager.get_status()
        print("Training Status:")
        print(f"  Today's Total: {status['today_total']:.2f}/{status['daily_limit']:.2f} hours")
        print(f"  Remaining Today: {status['remaining_today']:.2f} hours")
        print(f"  Total Training: {status['total_hours']:.2f} hours")
        print(f"  Total Sessions: {status['total_sessions']}")
        return 0
    
    return run_training_with_limits(args.config, session_manager)


if __name__ == '__main__':
    sys.exit(main())
