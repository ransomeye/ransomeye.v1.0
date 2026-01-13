#!/usr/bin/env python3
"""
RansomEye v1.0 Phase C - GA Verdict Aggregator
AUTHORITATIVE: Aggregates Phase C-L and Phase C-W results into final GA verdict

GA_READY = phase_c_linux_results.PASS == true AND phase_c_windows_results.PASS == true

Rules:
- Any skipped mandatory test = FAIL
- FAIL-006 cannot be skipped
- AGENT-002 cannot be skipped
- No partial or provisional GA allowed
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

from validation.harness.phase_c_executor import PhaseCExecutor, TestStatus


def aggregate_ga_verdict(linux_results_path: str, windows_results_path: str) -> Dict[str, Any]:
    """
    Aggregate GA verdict from Phase C-L and Phase C-W results.
    
    Args:
        linux_results_path: Path to phase_c_linux_results.json
        windows_results_path: Path to phase_c_windows_results.json
        
    Returns:
        Final GA verdict dictionary
    """
    # Load Linux results
    linux_path = Path(linux_results_path)
    if not linux_path.exists():
        raise FileNotFoundError(f"Linux results file not found: {linux_results_path}")
    
    with open(linux_path, 'r') as f:
        linux_results = json.load(f)
    
    # Load Windows results
    windows_path = Path(windows_results_path)
    if not windows_path.exists():
        raise FileNotFoundError(f"Windows results file not found: {windows_results_path}")
    
    with open(windows_path, 'r') as f:
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
    
    # Check AGENT-002 was not in Linux results (should be skipped there)
    agent_002_in_linux = False
    if "TRACK_6_AGENT_LINUX" in linux_tracks:
        agent_tests = linux_tracks["TRACK_6_AGENT_LINUX"].get("tests", {})
        if "AGENT-002" in agent_tests:
            agent_002_status = agent_tests["AGENT-002"].get("status")
            if agent_002_status != TestStatus.SKIPPED.value:
                agent_002_in_linux = True  # AGENT-002 should not run on Linux
    
    # Check AGENT-002 exists and passed in Windows results
    agent_002_in_windows = False
    agent_002_passed = False
    if "TRACK_6_AGENT_WINDOWS" in windows_tracks:
        agent_tests = windows_tracks["TRACK_6_AGENT_WINDOWS"].get("tests", {})
        if "AGENT-002" in agent_tests:
            agent_002_in_windows = True
            agent_002_status = agent_tests["AGENT-002"].get("status")
            if agent_002_status == TestStatus.SKIPPED.value:
                windows_pass = False  # AGENT-002 cannot be skipped
            elif agent_002_status == TestStatus.PASSED.value:
                agent_002_passed = True
    
    # Final GA verdict
    ga_ready = (
        linux_pass and
        windows_pass and
        not fail_006_skipped and
        not agent_002_in_linux and  # AGENT-002 must not run on Linux
        agent_002_in_windows and  # AGENT-002 must be in Windows results
        agent_002_passed  # AGENT-002 must pass
    )
    
    aggregate_verdict = {
        "ga_ready": ga_ready,
        "linux_pass": linux_pass,
        "windows_pass": windows_pass,
        "fail_006_skipped": fail_006_skipped,
        "agent_002_in_linux": agent_002_in_linux,
        "agent_002_in_windows": agent_002_in_windows,
        "agent_002_passed": agent_002_passed,
        "linux_skipped_tests": linux_skipped,
        "windows_skipped_tests": windows_skipped,
        "verdict": "GA-READY" if ga_ready else "NOT GA-READY",
        "verdict_timestamp": datetime.now(timezone.utc).isoformat(),
        "linux_results_path": str(linux_path.resolve()),
        "windows_results_path": str(windows_path.resolve()),
        "linux_summary": {
            "total_tests": linux_verdict.get("total_tests", 0),
            "passed_tests": linux_verdict.get("passed_tests", 0),
            "failed_tests": linux_verdict.get("failed_tests", 0),
            "skipped_tests": linux_verdict.get("skipped_tests", 0)
        },
        "windows_summary": {
            "total_tests": windows_verdict.get("total_tests", 0),
            "passed_tests": windows_verdict.get("passed_tests", 0),
            "failed_tests": windows_verdict.get("failed_tests", 0),
            "skipped_tests": windows_verdict.get("skipped_tests", 0)
        }
    }
    
    return aggregate_verdict


def main():
    """Main entry point for GA verdict aggregation."""
    if len(sys.argv) != 3:
        print("Usage: aggregate_ga_verdict.py <linux_results.json> <windows_results.json>")
        sys.exit(1)
    
    linux_results_path = sys.argv[1]
    windows_results_path = sys.argv[2]
    
    try:
        verdict = aggregate_ga_verdict(linux_results_path, windows_results_path)
        
        # Print verdict
        print("="*80)
        print("FINAL GA VERDICT")
        print("="*80)
        print(f"Status: {verdict['verdict']}")
        print()
        print("Phase C-L (Linux):")
        print(f"  Pass: {verdict['linux_pass']}")
        print(f"  Tests: {verdict['linux_summary']['total_tests']} total, "
              f"{verdict['linux_summary']['passed_tests']} passed, "
              f"{verdict['linux_summary']['failed_tests']} failed, "
              f"{verdict['linux_summary']['skipped_tests']} skipped")
        print()
        print("Phase C-W (Windows):")
        print(f"  Pass: {verdict['windows_pass']}")
        print(f"  Tests: {verdict['windows_summary']['total_tests']} total, "
              f"{verdict['windows_summary']['passed_tests']} passed, "
              f"{verdict['windows_summary']['failed_tests']} failed, "
              f"{verdict['windows_summary']['skipped_tests']} skipped")
        print()
        print("Mandatory Test Checks:")
        print(f"  FAIL-006 skipped: {verdict['fail_006_skipped']}")
        print(f"  AGENT-002 in Linux: {verdict['agent_002_in_linux']} (should be False)")
        print(f"  AGENT-002 in Windows: {verdict['agent_002_in_windows']} (should be True)")
        print(f"  AGENT-002 passed: {verdict['agent_002_passed']}")
        print()
        
        if verdict['ga_ready']:
            print("✅ Phase C validation PASSED. RansomEye is GA-READY.")
        else:
            print("❌ Phase C validation FAILED. GA is BLOCKED.")
        
        print("="*80)
        
        # Save aggregate verdict
        output_path = Path("validation/reports/phase_c/phase_c_aggregate_verdict.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(verdict, f, indent=2, sort_keys=True)
        
        print(f"\nAggregate verdict saved to: {output_path}")
        
        sys.exit(0 if verdict['ga_ready'] else 1)
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
