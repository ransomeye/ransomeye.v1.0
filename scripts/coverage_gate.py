#!/usr/bin/env python3
"""
Coverage gate enforcing per-domain thresholds.
"""

import json
import sys
from pathlib import Path
from fnmatch import fnmatch
from typing import Dict, List, Tuple


THRESHOLDS = {
    "core_orchestrator": 85.0,
    "security_critical": 90.0,
    "others": 75.0,
}

GROUP_PATTERNS = {
    "core_orchestrator": [
        "core/orchestrator.py",
        "core/status_schema.py",
    ],
    "security_critical": [
        "services/ui/backend/auth.py",
        "rbac/middleware/fastapi_auth.py",
        "dpi/probe/main.py",
        "common/db/migration_runner.py",
    ],
}


def _match_group(path: str) -> str:
    for group, patterns in GROUP_PATTERNS.items():
        for pattern in patterns:
            if fnmatch(path, pattern):
                return group
    return "others"


def _load_coverage(path: Path) -> Dict[str, Dict[str, int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    files = data.get("files", {})
    summaries = {}
    for filename, payload in files.items():
        summary = payload.get("summary", {})
        summaries[filename] = {
            "covered_lines": summary.get("covered_lines", 0),
            "num_statements": summary.get("num_statements", 0),
        }
    return summaries


def _aggregate_by_group(summaries: Dict[str, Dict[str, int]]) -> Dict[str, Tuple[int, int]]:
    grouped: Dict[str, Tuple[int, int]] = {key: (0, 0) for key in THRESHOLDS}
    for filename, stats in summaries.items():
        group = _match_group(filename)
        covered, total = grouped[group]
        grouped[group] = (
            covered + stats["covered_lines"],
            total + stats["num_statements"],
        )
    return grouped


def _percent(covered: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((covered / total) * 100.0, 2)


def main() -> int:
    coverage_path = Path("coverage.json")
    if not coverage_path.exists():
        print("coverage.json not found", file=sys.stderr)
        return 2

    summaries = _load_coverage(coverage_path)
    grouped = _aggregate_by_group(summaries)

    failures: List[str] = []
    for group, (covered, total) in grouped.items():
        pct = _percent(covered, total)
        threshold = THRESHOLDS[group]
        print(f"{group}: {pct}% ({covered}/{total}) threshold={threshold}%")
        if total == 0:
            failures.append(f"{group}: no files matched")
        elif pct < threshold:
            failures.append(f"{group}: {pct}% < {threshold}%")

    if failures:
        print("Coverage gate failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
