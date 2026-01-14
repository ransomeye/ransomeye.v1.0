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
        
        # Test execution results (always initialize safely)
        phase_name = "Phase C-L" if self.execution_mode == 'linux' else "Phase C-W"
        self.results: Dict[str, Any] = {
            "schema_version": "1.0",
            "phase": phase_name,
            "status": "UNKNOWN",
            "execution_start": datetime.now(timezone.utc).isoformat(),
            "execution_end": None,
            "execution_mode": self.execution_mode,
            "platform": platform.system(),
            "platform_release": platform.release(),
            "tracks": {},
            "tests": {},  # Flattened test results
            "verdict": {
                "execution_mode": self.execution_mode,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0,
                "all_tracks_passed": False,
                "mode_ready": False,
                "verdict": "UNKNOWN",
                "verdict_timestamp": None
            }
        }
        
        # Evidence artifacts
        self.artifacts: List[str] = []
        
        # Track execution state
        self.tracks_executed = False
        
        # Preflight check state
        self.preflight_checked = False
    
    def preflight_check(self):
        """
        Preflight validation checks (explicit, not in __init__).
        
        Validates:
        - OS execution boundaries
        - Database connectivity (HARD GATE)
        
        Must be called before run_all_tracks().
        Fails fast with clear error messages.
        """
        if self.preflight_checked:
            return  # Already checked
        
        # Enforce OS execution boundaries
        self._enforce_os_boundaries()
        
        # Startup DB connectivity assertion (HARD GATE)
        self._assert_db_connectivity()
        
        self.preflight_checked = True
    
    def _enforce_os_boundaries(self):
        """
        Enforce OS execution boundaries (PHASE B1: OS-Aware Validation).
        
        Hard-blocks incompatible tracks:
        - ETW on Linux → refuse (ETW is Windows-only)
        - eBPF on Windows → refuse (eBPF is Linux-only)
        
        Linux refuses --mode windows
        Windows refuses Linux tracks
        Clear fatal errors when violated (no warnings, final errors)
        """
        current_os = platform.system().lower()
        
        # PHASE B1: Hard-block ETW on Linux (Windows-only technology)
        if current_os == 'linux' and self.execution_mode == 'windows':
            error_msg = (
                "FATAL: Cannot run Phase C-W (Windows mode) on Linux host.\n"
                "ETW (Event Tracing for Windows) is Windows-only and cannot execute on Linux.\n"
                "Windows Agent validation must be run on native Windows host.\n"
                "Use --mode linux or omit --mode to auto-detect."
            )
            print(f"❌ {error_msg}", file=sys.stderr)
            sys.exit(1)
        
        # PHASE B1: Hard-block eBPF on Windows (Linux-only technology)
        if current_os == 'windows' and self.execution_mode == 'linux':
            error_msg = (
                "FATAL: Cannot run Phase C-L (Linux mode) on Windows host.\n"
                "eBPF (extended Berkeley Packet Filter) is Linux-only and cannot execute on Windows.\n"
                "Linux tracks must be run on Linux host.\n"
                "Use --mode windows or omit --mode to auto-detect."
            )
            print(f"❌ {error_msg}", file=sys.stderr)
            sys.exit(1)
        
        # PHASE B1: Additional technology-level checks
        # Check for ETW-related imports or usage on Linux
        if current_os == 'linux':
            self._check_etw_usage()
        
        # Check for eBPF-related imports or usage on Windows
        if current_os == 'windows':
            self._check_ebpf_usage()
    
    def _check_etw_usage(self):
        """
        PHASE B1: Check for ETW usage on Linux (hard-block).
        
        ETW (Event Tracing for Windows) is Windows-only.
        Any attempt to use ETW on Linux must be refused.
        """
        # Check if Windows agent track is being imported/executed
        if self.execution_mode == 'windows':
            # This should already be caught by _enforce_os_boundaries, but double-check
            error_msg = (
                "FATAL: ETW (Event Tracing for Windows) detected on Linux host.\n"
                "ETW is Windows-only and cannot execute on Linux.\n"
                "This is a hard block for audit integrity and legal defensibility."
            )
            print(f"❌ {error_msg}", file=sys.stderr)
            sys.exit(1)
    
    def _check_ebpf_usage(self):
        """
        PHASE B1: Check for eBPF usage on Windows (hard-block).
        
        eBPF (extended Berkeley Packet Filter) is Linux-only.
        Any attempt to use eBPF on Windows must be refused.
        """
        # Check if Linux DPI track with eBPF is being imported/executed
        if self.execution_mode == 'linux':
            # This should already be caught by _enforce_os_boundaries, but double-check
            error_msg = (
                "FATAL: eBPF (extended Berkeley Packet Filter) detected on Windows host.\n"
                "eBPF is Linux-only and cannot execute on Windows.\n"
                "This is a hard block for audit integrity and legal defensibility."
            )
            print(f"❌ {error_msg}", file=sys.stderr)
            sys.exit(1)
    
    def _assert_db_connectivity(self):
        """
        Startup DB connectivity assertion (HARD GATE).
        
        Verifies PostgreSQL is correctly bootstrapped:
        - Role exists with LOGIN privilege
        - Database exists and is owned by role
        - Authentication works
        - Basic queries work
        
        If DB bootstrap verification fails → immediate fatal exit
        No tracks execute
        No partial verdict
        Clear, actionable error message (no Python tracebacks)
        """
        from validation.harness.db_bootstrap_validator import (
            verify_db_bootstrap,
            format_bootstrap_failure_message
        )
        import os
        
        # Get credentials (with defaults)
        db_user = os.getenv("RANSOMEYE_DB_USER", "gagan")
        db_password = os.getenv("RANSOMEYE_DB_PASSWORD", "gagan")
        db_host = os.getenv("RANSOMEYE_DB_HOST", "localhost")
        db_port = int(os.getenv("RANSOMEYE_DB_PORT", "5432"))
        db_name = os.getenv("RANSOMEYE_DB_NAME", "ransomeye")
        
        # Verify bootstrap
        success, failure_reason = verify_db_bootstrap(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        if not success:
            # Format clear, actionable error message
            error_msg = format_bootstrap_failure_message(
                failure_reason,
                user=db_user,
                password=db_password,
                database=db_name
            )
            print(error_msg, file=sys.stderr)
            sys.exit(1)
    
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
            self.tracks_executed = True
        except Exception as e:
            # Clear error message (no traceback for operator errors)
            error_detail = str(e).split('\n')[0] if '\n' in str(e) else str(e)
            track_results = {
                "status": TestStatus.FAILED.value,
                "error": error_detail,
                "all_passed": False
            }
            print(f"❌ ERROR in {track_name}: {error_detail}")
            # Mark that tracks were attempted (even if failed)
            self.tracks_executed = True
        
        track_results["execution_time_seconds"] = time.time() - track_start
        track_results["execution_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        self.results["tracks"][track_name] = track_results
        
        return track_results
    
    def generate_final_report(self) -> Dict[str, Any]:
        """
        Generate final verdict for this execution mode.
        
        Note: Final GA verdict requires both Phase C-L and Phase C-W results.
        Use aggregate_ga_verdict() to compute final GA status.
        
        Abort immediately if tracks didn't execute (DB failure or other fatal error).
        
        Returns:
            Verdict dictionary for this execution mode
        """
        # Abort if tracks didn't execute (DB failure or fatal error)
        if not self.tracks_executed:
            error_msg = (
                "FATAL: No tracks executed. Cannot compute verdict.\n"
                "This indicates a fatal error during execution (e.g., DB connectivity failure)."
            )
            print(f"❌ {error_msg}", file=sys.stderr)
            sys.exit(1)
        
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
        
        verdict_status = "PASS" if mode_ready else "FAIL"
        
        verdict = {
            "execution_mode": self.execution_mode,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "all_tracks_passed": all_tracks_passed,
            "mode_ready": mode_ready,  # This mode passed
            "artifacts": self.artifacts,
            "verdict": verdict_status,
            "verdict_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Update results with verdict and status
        self.results["verdict"] = verdict
        self.results["status"] = verdict_status
        
        # Flatten tests into results for easier access
        for track_name, track_results in self.results["tracks"].items():
            track_tests = track_results.get("tests", {})
            for test_name, test_result in track_tests.items():
                self.results["tests"][test_name] = test_result
        
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
        
        Preflight check must be called first.
        Abort immediately on DB failure.
        Never compute verdict if tracks didn't execute.
        """
        # Require preflight check
        if not self.preflight_checked:
            error_msg = (
                "FATAL: preflight_check() must be called before run_all_tracks().\n"
                "Call executor.preflight_check() first."
            )
            print(f"❌ {error_msg}", file=sys.stderr)
            sys.exit(1)
        
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
        
        try:
            if self.execution_mode == 'linux':
                self._run_linux_tracks()
            else:
                self._run_windows_tracks()
        except Exception as e:
            # Fatal error during track execution (clear message, no traceback)
            error_detail = str(e).split('\n')[0] if '\n' in str(e) else str(e)
            error_msg = (
                f"FATAL: Track execution failed.\n"
                f"Error: {error_detail}\n"
                f"No verdict computed. Phase C execution aborted."
            )
            print(f"❌ {error_msg}", file=sys.stderr)
            sys.exit(1)
        
        # Generate final report (aborts if tracks didn't execute)
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
        # Enforce: Windows tracks cannot run on Linux
        if self.execution_mode != 'linux':
            error_msg = "FATAL: Linux tracks can only run on Linux host."
            print(f"❌ {error_msg}", file=sys.stderr)
            sys.exit(1)
        
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
        # Enforce: Linux tracks cannot run on Windows
        if self.execution_mode != 'windows':
            error_msg = "FATAL: Windows tracks can only run on Windows host."
            print(f"❌ {error_msg}", file=sys.stderr)
            sys.exit(1)
        
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
    
    try:
        execution_mode = None if args.mode == 'auto' else args.mode
        executor = PhaseCExecutor(output_dir=args.output_dir, execution_mode=execution_mode)
        
        # Preflight check (explicit, not in __init__)
        executor.preflight_check()
        
        # Run all tracks
        verdict = executor.run_all_tracks()
        
        # Exit with appropriate code (mode-specific, not final GA)
        sys.exit(0 if verdict['verdict'] == 'PASS' else 1)
    
    except KeyboardInterrupt:
        error_msg = "FATAL: Execution interrupted by user."
        print(f"❌ {error_msg}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Clear error message (no traceback for operator errors)
        error_detail = str(e).split('\n')[0] if '\n' in str(e) else str(e)
        error_msg = (
            f"FATAL: Phase C execution failed.\n"
            f"Error: {error_detail}"
        )
        print(f"❌ {error_msg}", file=sys.stderr)
        sys.exit(1)
