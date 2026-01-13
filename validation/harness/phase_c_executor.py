#!/usr/bin/env python3
"""
RansomEye v1.0 Phase C Validation - Test Execution Orchestrator
AUTHORITATIVE: Main execution engine for Phase C GA validation (Multi-Host Model)

EXECUTION MODEL:
- Phase C-L (Linux): Runs Tracks 1-5 + Track 6-A (Linux Agent only)
- Phase C-W (Windows): Runs Track 6-B (Windows Agent/ETW only)
- GA verdict requires both Phase C-L and Phase C-W to pass
"""

import os
import sys
import json
import hashlib
import time
import platform
import psycopg2
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

# Add project root to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from validation.harness.test_helpers import get_test_db_connection, clean_database


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PhaseCExecutor:
    """
    Phase C validation test execution orchestrator (Multi-Host Model).
    
    Supports two execution modes:
    - Phase C-L (Linux): Tracks 1-5 + Track 6-A (Linux Agent)
    - Phase C-W (Windows): Track 6-B (Windows Agent/ETW)
    
    GA verdict requires both Phase C-L and Phase C-W results.
    """
    
    def __init__(self, output_dir: str = None, execution_mode: str = None):
        """
        Initialize Phase C executor.
        
        Args:
            output_dir: Output directory for evidence artifacts (default: validation/reports/phase_c)
            execution_mode: Execution mode ('linux', 'windows', or None for auto-detect)
        """
        if output_dir is None:
            output_dir = str(_project_root / "validation" / "reports" / "phase_c")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Detect OS and set execution mode
        if execution_mode is None:
            self.execution_mode = self._detect_execution_mode()
        else:
            self.execution_mode = execution_mode.lower()
        
        if self.execution_mode not in ['linux', 'windows']:
            raise ValueError(f"Invalid execution mode: {execution_mode}. Must be 'linux' or 'windows'")
        
        # Test execution results
        self.results: Dict[str, Any] = {
            "execution_start": datetime.now(timezone.utc).isoformat(),
            "execution_end": None,
            "execution_mode": self.execution_mode,
            "platform": platform.system(),
            "platform_release": platform.release(),
            "tracks": {}
        }
        
        # Evidence artifacts
        self.artifacts: List[str] = []
    
    def _detect_execution_mode(self) -> str:
        """
        Detect execution mode based on OS.
        
        Returns:
            'linux' or 'windows'
        """
        system = platform.system().lower()
        if system == 'linux':
            return 'linux'
        elif system == 'windows':
            return 'windows'
        else:
            raise RuntimeError(
                f"Unsupported platform: {system}. Phase C validation requires Linux or Windows."
            )
    
    def get_db_connection(self):
        """Get database connection for validation."""
        return get_test_db_connection()
    
    def calculate_hash(self, data: Any) -> str:
        """
        Calculate SHA256 hash of data.
        
        Args:
            data: Data to hash (dict, list, str, etc.)
            
        Returns:
            SHA256 hash (hex string)
        """
        if isinstance(data, (dict, list)):
            # Canonical JSON encoding
            json_str = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            data_bytes = json_str.encode('utf-8')
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = str(data).encode('utf-8')
        
        return hashlib.sha256(data_bytes).hexdigest()
    
    def save_artifact(self, filename: str, content: Any, format: str = "json") -> str:
        """
        Save evidence artifact.
        
        Args:
            filename: Artifact filename
            content: Artifact content
            format: Format ("json" or "markdown")
            
        Returns:
            Path to saved artifact
        """
        filepath = self.output_dir / filename
        
        if format == "json":
            with open(filepath, 'w') as f:
                json.dump(content, f, indent=2, sort_keys=True)
        elif format == "markdown":
            with open(filepath, 'w') as f:
                f.write(content)
        else:
            raise ValueError(f"Unknown format: {format}")
        
        self.artifacts.append(str(filepath))
        return str(filepath)
    
    def execute_track(self, track_name: str, track_executor) -> Dict[str, Any]:
        """
        Execute a validation track.
        
        Args:
            track_name: Track name (e.g., "TRACK_1_DETERMINISM")
            track_executor: Track executor function
            
        Returns:
            Track execution results
        """
        print(f"\n{'='*80}")
        print(f"Executing {track_name}")
        print(f"{'='*80}")
        
        track_start = time.time()
        
        try:
            track_results = track_executor(self)
            track_results["status"] = TestStatus.PASSED.value if track_results.get("all_passed", False) else TestStatus.FAILED.value
        except Exception as e:
            track_results = {
                "status": TestStatus.FAILED.value,
                "error": str(e),
                "all_passed": False
            }
            print(f"ERROR in {track_name}: {e}")
            import traceback
            traceback.print_exc()
        
        track_results["execution_time_seconds"] = time.time() - track_start
        track_results["execution_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        self.results["tracks"][track_name] = track_results
        
        return track_results
    
    def generate_final_report(self) -> Dict[str, Any]:
        """
        Generate final verdict for this execution mode.
        
        Note: Final GA verdict requires both Phase C-L and Phase C-W results.
        Use aggregate_ga_verdict() to compute final GA status.
        
        Returns:
            Verdict dictionary for this execution mode
        """
        self.results["execution_end"] = datetime.now(timezone.utc).isoformat()
        
        # Count test results
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        for track_name, track_results in self.results["tracks"].items():
            track_tests = track_results.get("tests", {})
            for test_name, test_result in track_tests.items():
                total_tests += 1
                status = test_result.get("status")
                if status == TestStatus.PASSED.value:
                    passed_tests += 1
                elif status == TestStatus.FAILED.value:
                    failed_tests += 1
                elif status == TestStatus.SKIPPED.value:
                    skipped_tests += 1
        
        # Determine overall status for this execution mode
        all_tracks_passed = all(
            track.get("status") == TestStatus.PASSED.value
            for track in self.results["tracks"].values()
        )
        
        # Mode-specific readiness (not final GA verdict)
        mode_ready = (
            all_tracks_passed and
            failed_tests == 0 and
            skipped_tests == 0 and  # No skipped mandatory tests
            len(self.artifacts) > 0
        )
        
        verdict = {
            "execution_mode": self.execution_mode,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "all_tracks_passed": all_tracks_passed,
            "mode_ready": mode_ready,  # This mode passed
            "artifacts": self.artifacts,
            "verdict": "PASS" if mode_ready else "FAIL",
            "verdict_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.results["verdict"] = verdict
        
        # Save mode-specific results file
        if self.execution_mode == 'linux':
            self.save_artifact("phase_c_linux_results.json", self.results)
            markdown_report = self._generate_markdown_report()
            self.save_artifact("phase_c_linux_report.md", markdown_report, format="markdown")
        else:
            self.save_artifact("phase_c_windows_results.json", self.results)
            markdown_report = self._generate_markdown_report()
            self.save_artifact("phase_c_windows_report.md", markdown_report, format="markdown")
        
        return verdict
    
    @staticmethod
    def aggregate_ga_verdict(linux_results_path: str, windows_results_path: str) -> Dict[str, Any]:
        """
        Aggregate GA verdict from Phase C-L and Phase C-W results.
        
        GA_READY = phase_c_linux_results.PASS == true AND phase_c_windows_results.PASS == true
        
        Rules:
        - Any skipped mandatory test = FAIL
        - FAIL-006 cannot be skipped
        - AGENT-002 cannot be skipped
        - No partial or provisional GA allowed
        
        Args:
            linux_results_path: Path to phase_c_linux_results.json
            windows_results_path: Path to phase_c_windows_results.json
            
        Returns:
            Final GA verdict dictionary
        """
        # Load Linux results
        with open(linux_results_path, 'r') as f:
            linux_results = json.load(f)
        
        # Load Windows results
        with open(windows_results_path, 'r') as f:
            windows_results = json.load(f)
        
        linux_verdict = linux_results.get("verdict", {})
        windows_verdict = windows_results.get("verdict", {})
        
        linux_pass = linux_verdict.get("verdict") == "PASS"
        windows_pass = windows_verdict.get("verdict") == "PASS"
        
        # Check for skipped mandatory tests
        linux_skipped = linux_verdict.get("skipped_tests", 0)
        windows_skipped = windows_verdict.get("skipped_tests", 0)
        
        # Check specific mandatory tests
        linux_tracks = linux_results.get("tracks", {})
        windows_tracks = windows_results.get("tracks", {})
        
        # Check FAIL-006 was not skipped
        fail_006_skipped = False
        if "TRACK_3_FAILURE_INJECTION" in linux_tracks:
            fail_tests = linux_tracks["TRACK_3_FAILURE_INJECTION"].get("tests", {})
            if "FAIL-006" in fail_tests:
                fail_006_status = fail_tests["FAIL-006"].get("status")
                if fail_006_status == TestStatus.SKIPPED.value:
                    fail_006_skipped = True
        
        # Check AGENT-002 was not skipped (should not be in Linux results)
        agent_002_in_linux = False
        if "TRACK_6_AGENT_LINUX" in linux_tracks:
            agent_tests = linux_tracks["TRACK_6_AGENT_LINUX"].get("tests", {})
            if "AGENT-002" in agent_tests:
                agent_002_in_linux = True
        
        # Check AGENT-002 exists in Windows results
        agent_002_in_windows = False
        if "TRACK_6_AGENT_WINDOWS" in windows_tracks:
            agent_tests = windows_tracks["TRACK_6_AGENT_WINDOWS"].get("tests", {})
            if "AGENT-002" in agent_tests:
                agent_002_status = agent_tests["AGENT-002"].get("status")
                agent_002_in_windows = True
                if agent_002_status == TestStatus.SKIPPED.value:
                    windows_pass = False  # AGENT-002 cannot be skipped
        
        # Final GA verdict
        ga_ready = (
            linux_pass and
            windows_pass and
            not fail_006_skipped and
            not agent_002_in_linux and  # AGENT-002 must not be in Linux results
            agent_002_in_windows  # AGENT-002 must be in Windows results
        )
        
        aggregate_verdict = {
            "ga_ready": ga_ready,
            "linux_pass": linux_pass,
            "windows_pass": windows_pass,
            "fail_006_skipped": fail_006_skipped,
            "agent_002_in_linux": agent_002_in_linux,
            "agent_002_in_windows": agent_002_in_windows,
            "linux_skipped_tests": linux_skipped,
            "windows_skipped_tests": windows_skipped,
            "verdict": "GA-READY" if ga_ready else "NOT GA-READY",
            "verdict_timestamp": datetime.now(timezone.utc).isoformat(),
            "linux_results": linux_verdict,
            "windows_results": windows_verdict
        }
        
        return aggregate_verdict
    
    def _generate_markdown_report(self) -> str:
        """Generate human-readable markdown report."""
        lines = []
        lines.append("# Phase C Validation Report")
        lines.append("")
        lines.append(f"**Execution Start**: {self.results['execution_start']}")
        lines.append(f"**Execution End**: {self.results.get('execution_end', 'N/A')}")
        lines.append("")
        
        # Track summary
        lines.append("## Track Summary")
        lines.append("")
        lines.append("| Track | Status | Tests Passed | Tests Failed | Execution Time |")
        lines.append("|-------|--------|--------------|--------------|-----------------|")
        
        for track_name, track_results in self.results["tracks"].items():
            status = track_results.get("status", "unknown")
            tests = track_results.get("tests", {})
            passed = sum(1 for t in tests.values() if t.get("status") == TestStatus.PASSED.value)
            failed = sum(1 for t in tests.values() if t.get("status") == TestStatus.FAILED.value)
            exec_time = track_results.get("execution_time_seconds", 0)
            
            lines.append(f"| {track_name} | {status.upper()} | {passed} | {failed} | {exec_time:.2f}s |")
        
        lines.append("")
        
        # Final verdict
        verdict = self.results.get("verdict", {})
        lines.append("## Final GA Verdict")
        lines.append("")
        lines.append(f"**Status**: {verdict.get('verdict', 'UNKNOWN')}")
        lines.append(f"**Total Tests**: {verdict.get('total_tests', 0)}")
        lines.append(f"**Passed**: {verdict.get('passed_tests', 0)}")
        lines.append(f"**Failed**: {verdict.get('failed_tests', 0)}")
        lines.append("")
        
        if verdict.get("ga_ready", False):
            lines.append("✅ **Phase C validation PASSED. RansomEye is GA-READY.**")
        else:
            lines.append("❌ **Phase C validation FAILED. GA is BLOCKED.**")
        
        lines.append("")
        
        # Evidence artifacts
        lines.append("## Evidence Artifacts")
        lines.append("")
        for artifact in self.artifacts:
            lines.append(f"- {artifact}")
        
        lines.append("")
        
        return "\n".join(lines)
    
    def run_all_tracks(self):
        """
        Execute validation tracks based on execution mode.
        
        Phase C-L (Linux): Tracks 1-5 + Track 6-A (Linux Agent)
        Phase C-W (Windows): Track 6-B (Windows Agent/ETW)
        """
        print("="*80)
        if self.execution_mode == 'linux':
            print("Phase C-L Validation - Linux Execution")
            print("Tracks: 1-5 + Track 6-A (Linux Agent)")
        else:
            print("Phase C-W Validation - Windows Execution")
            print("Track: 6-B (Windows Agent/ETW)")
        print("="*80)
        print(f"Platform: {platform.system()} {platform.release()}")
        print(f"Output directory: {self.output_dir}")
        print()
        
        if self.execution_mode == 'linux':
            self._run_linux_tracks()
        else:
            self._run_windows_tracks()
        
        # Generate final report
        verdict = self.generate_final_report()
        
        # Print final verdict
        print("\n" + "="*80)
        if self.execution_mode == 'linux':
            print("PHASE C-L VERDICT")
        else:
            print("PHASE C-W VERDICT")
        print("="*80)
        print(f"Status: {verdict['verdict']}")
        print(f"Total Tests: {verdict['total_tests']}")
        print(f"Passed: {verdict['passed_tests']}")
        print(f"Failed: {verdict['failed_tests']}")
        print()
        
        if verdict['ga_ready']:
            if self.execution_mode == 'linux':
                print("Phase C-L validation PASSED.")
            else:
                print("Phase C-W validation PASSED.")
        else:
            if self.execution_mode == 'linux':
                print("Phase C-L validation FAILED.")
            else:
                print("Phase C-W validation FAILED.")
        
        print(f"\nEvidence artifacts saved to: {self.output_dir}")
        print("="*80)
        
        return verdict
    
    def _run_linux_tracks(self):
        """Execute Phase C-L tracks (1-5 + Track 6-A)."""
        # Import track executors
        from validation.harness.track_1_determinism import execute_track_1_determinism
        from validation.harness.track_2_replay import execute_track_2_replay
        from validation.harness.track_3_failure import execute_track_3_failure
        from validation.harness.track_4_scale import execute_track_4_scale
        from validation.harness.track_5_security import execute_track_5_security
        from validation.harness.track_6_agent_linux import execute_track_6_agent_linux
        
        # Execute all tracks
        self.execute_track("TRACK_1_DETERMINISM", execute_track_1_determinism)
        self.execute_track("TRACK_2_REPLAY", execute_track_2_replay)
        self.execute_track("TRACK_3_FAILURE_INJECTION", execute_track_3_failure)
        self.execute_track("TRACK_4_SCALE_STRESS", execute_track_4_scale)
        self.execute_track("TRACK_5_SECURITY_SAFETY", execute_track_5_security)
        self.execute_track("TRACK_6_AGENT_LINUX", execute_track_6_agent_linux)
    
    def _run_windows_tracks(self):
        """Execute Phase C-W tracks (Track 6-B only)."""
        from validation.harness.track_6_agent_windows import execute_track_6_agent_windows
        
        # Execute only Track 6-B
        self.execute_track("TRACK_6_AGENT_WINDOWS", execute_track_6_agent_windows)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase C Validation Executor")
    parser.add_argument(
        "--mode",
        choices=['linux', 'windows', 'auto'],
        default='auto',
        help="Execution mode (linux, windows, or auto-detect)"
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for evidence artifacts"
    )
    
    args = parser.parse_args()
    
    execution_mode = None if args.mode == 'auto' else args.mode
    executor = PhaseCExecutor(output_dir=args.output_dir, execution_mode=execution_mode)
    verdict = executor.run_all_tracks()
    
    # Exit with appropriate code (mode-specific, not final GA)
    sys.exit(0 if verdict['verdict'] == 'PASS' else 1)
