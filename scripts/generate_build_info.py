#!/usr/bin/env python3
"""
RansomEye v1.0 Build Info Generator
Generates build-info.json with deterministic build metadata
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


def get_git_commit_sha() -> str:
    """Get exact git commit SHA."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def get_git_tag() -> str:
    """Get current git tag if available."""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--exact-match', 'HEAD'],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def get_build_timestamp() -> str:
    """Get build timestamp in RFC3339 UTC format."""
    # Use SOURCE_DATE_EPOCH if set for reproducibility
    source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH')
    if source_date_epoch:
        timestamp = int(source_date_epoch)
    else:
        timestamp = int(datetime.now(timezone.utc).timestamp())
    
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.isoformat().replace('+00:00', 'Z')


def get_toolchain_versions() -> Dict[str, str]:
    """Get versions of all toolchain components."""
    versions = {}
    
    # Python version
    versions['python'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # Rust version (if available)
    try:
        result = subprocess.run(
            ['rustc', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        versions['rust'] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        versions['rust'] = "not_available"
    
    # Cargo version (if available)
    try:
        result = subprocess.run(
            ['cargo', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        versions['cargo'] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        versions['cargo'] = "not_available"
    
    return versions


def get_build_environment() -> Dict[str, str]:
    """Get build environment information."""
    env = {}
    env['os'] = os.uname().sysname if hasattr(os, 'uname') else os.name
    env['os_version'] = os.uname().release if hasattr(os, 'uname') else "unknown"
    env['arch'] = os.uname().machine if hasattr(os, 'uname') else "unknown"
    env['source_date_epoch'] = os.environ.get('SOURCE_DATE_EPOCH', 'not_set')
    env['python_hash_seed'] = os.environ.get('PYTHONHASHSEED', 'not_set')
    return env


def generate_build_info(output_path: Path, build_id: str = None) -> None:
    """Generate build-info.json file."""
    build_info = {
        "git_commit": get_git_commit_sha(),
        "git_tag": get_git_tag(),
        "build_timestamp": get_build_timestamp(),
        "build_runner": os.environ.get('GITHUB_ACTIONS', 'false') == 'true' and 'github-actions' or 'local',
        "build_id": build_id or os.environ.get('GITHUB_RUN_ID', 'local'),
        "toolchain_versions": get_toolchain_versions(),
        "build_environment": get_build_environment()
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(build_info, f, indent=2)
    
    print(f"✅ Generated build-info.json at {output_path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate build-info.json')
    parser.add_argument('--output', type=Path, required=True, help='Output path for build-info.json')
    parser.add_argument('--build-id', type=str, help='Build ID (e.g., GitHub run ID)')
    args = parser.parse_args()
    
    generate_build_info(args.output, args.build_id)
