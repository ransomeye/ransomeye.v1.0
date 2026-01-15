#!/usr/bin/env python3
"""
RansomEye v1.0 Validation Harness - Component Supervision Guard Tests
AUTHORITATIVE: Phase 2 supervised-only enforcement
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any

from validation.harness.phase_c_executor import ValidationStatus


def _project_root() -> Path:
    return Path(__file__).parent.parent.parent


def _run_component(path: Path) -> int:
    env = os.environ.copy()
    env.pop("RANSOMEYE_SUPERVISED", None)
    env.pop("RANSOMEYE_CORE_PID", None)
    env.pop("RANSOMEYE_CORE_TOKEN", None)
    return subprocess.run(
        [os.environ.get("PYTHON", "python3"), str(path)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode


def test_manual_component_start_blocked() -> Dict[str, Any]:
    """
    ORCH-003: Manual component execution fails hard.
    """
    root = _project_root()
    components = {
        "ingest": root / "services" / "ingest" / "app" / "main.py",
        "correlation-engine": root / "services" / "correlation-engine" / "app" / "main.py",
        "ai-core": root / "services" / "ai-core" / "app" / "main.py",
        "policy-engine": root / "services" / "policy-engine" / "app" / "main.py",
        "ui-backend": root / "services" / "ui" / "backend" / "main.py",
        "dpi-probe": root / "dpi" / "probe" / "main.py"
    }
    failures = {}
    for name, path in components.items():
        failures[name] = _run_component(path) != 0
    passed = all(failures.values())
    return {
        "status": ValidationStatus.PASSED.value if passed else ValidationStatus.FAILED.value,
        "blocked": failures
    }
