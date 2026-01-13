#!/usr/bin/env python3
"""
RansomEye v1.0 Phase C Validation - Test Execution Orchestrator
AUTHORITATIVE: Main execution engine for Phase C GA validation
"""

import os
import sys
import json
import hashlib
import time
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
    Phase C validation test execution orchestrator.
    
    Executes all 34 tests across 6 tracks and produces evidence artifacts.
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize Phase C executor.
        
        Args:
            output_dir: Output directory for evidence artifacts (default: validation/reports/phase_c)
        """
        if output_dir is None:
            output_dir = str(_project_root / "validation" / "reports" / "phase_c")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Test execution results
        self.results: Dict[str, Any] = {
            "execution_start": datetime.now(timezone.utc).isoformat(),
            "execution_end": None,
            "tracks": {}
        }
        
        # Evidence artifacts
        self.artifacts: List[str] = []
    
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
        Generate final GA readiness verdict.
        
        Returns:
            Final verdict dictionary
        """
        self.results["execution_end"] = datetime.now(timezone.utc).isoformat()
        
        # Count test results
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for track_name, track_results in self.results["tracks"].items():
            track_tests = track_results.get("tests", {})
            for test_name, test_result in track_tests.items():
                total_tests += 1
                if test_result.get("status") == TestStatus.PASSED.value:
                    passed_tests += 1
                elif test_result.get("status") == TestStatus.FAILED.value:
                    failed_tests += 1
        
        # Determine overall status
        all_tracks_passed = all(
            track.get("status") == TestStatus.PASSED.value
            for track in self.results["tracks"].values()
        )
        
        # GA readiness criteria
        ga_ready = (
            all_tracks_passed and
            failed_tests == 0 and
            len(self.artifacts) > 0
        )
        
        verdict = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "all_tracks_passed": all_tracks_passed,
            "ga_ready": ga_ready,
            "artifacts": self.artifacts,
            "verdict": "GA-READY" if ga_ready else "NOT GA-READY",
            "verdict_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.results["verdict"] = verdict
        
        # Save final report
        self.save_artifact("phase_c_validation_results.json", self.results)
        
        # Generate markdown report
        markdown_report = self._generate_markdown_report()
        self.save_artifact("phase_c_validation_report.md", markdown_report, format="markdown")
        
        return verdict
    
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
        """Execute all validation tracks."""
        print("="*80)
        print("Phase C Validation - Global GA Validation (Final Execution)")
        print("="*80)
        print(f"Output directory: {self.output_dir}")
        print()
        
        # Import track executors
        from validation.harness.track_1_determinism import execute_track_1_determinism
        from validation.harness.track_2_replay import execute_track_2_replay
        from validation.harness.track_3_failure import execute_track_3_failure
        from validation.harness.track_4_scale import execute_track_4_scale
        from validation.harness.track_5_security import execute_track_5_security
        from validation.harness.track_6_agent import execute_track_6_agent
        
        # Execute all tracks
        self.execute_track("TRACK_1_DETERMINISM", execute_track_1_determinism)
        self.execute_track("TRACK_2_REPLAY", execute_track_2_replay)
        self.execute_track("TRACK_3_FAILURE_INJECTION", execute_track_3_failure)
        self.execute_track("TRACK_4_SCALE_STRESS", execute_track_4_scale)
        self.execute_track("TRACK_5_SECURITY_SAFETY", execute_track_5_security)
        self.execute_track("TRACK_6_AGENT_REALITY_CHECK", execute_track_6_agent)
        
        # Generate final report
        verdict = self.generate_final_report()
        
        # Print final verdict
        print("\n" + "="*80)
        print("FINAL GA VERDICT")
        print("="*80)
        print(f"Status: {verdict['verdict']}")
        print(f"Total Tests: {verdict['total_tests']}")
        print(f"Passed: {verdict['passed_tests']}")
        print(f"Failed: {verdict['failed_tests']}")
        print()
        
        if verdict['ga_ready']:
            print("Phase C validation PASSED. RansomEye is GA-READY.")
        else:
            print("Phase C validation FAILED. GA is BLOCKED.")
        
        print(f"\nEvidence artifacts saved to: {self.output_dir}")
        print("="*80)
        
        return verdict


if __name__ == "__main__":
    executor = PhaseCExecutor()
    verdict = executor.run_all_tracks()
    
    # Exit with appropriate code
    sys.exit(0 if verdict['ga_ready'] else 1)
