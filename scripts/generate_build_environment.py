#!/usr/bin/env python3
"""
RansomEye v1.0 Build Environment Generator
Generates build-environment.json with complete build environment documentation
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List


def get_system_info() -> Dict[str, str]:
    """Get system information."""
    return {
        "os": platform.system(),
        "os_version": platform.release(),
        "os_version_full": platform.version(),
        "arch": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node()
    }


def get_python_info() -> Dict[str, Any]:
    """Get Python environment information."""
    return {
        "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "version_full": sys.version,
        "executable": sys.executable,
        "platform": sys.platform,
        "hash_seed": os.environ.get('PYTHONHASHSEED', 'not_set')
    }


def get_rust_info() -> Dict[str, str]:
    """Get Rust toolchain information."""
    info = {}
    
    try:
        result = subprocess.run(
            ['rustc', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        info['rustc_version'] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        info['rustc_version'] = "not_available"
    
    try:
        result = subprocess.run(
            ['cargo', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        info['cargo_version'] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        info['cargo_version'] = "not_available"
    
    try:
        result = subprocess.run(
            ['rustup', 'show'],
            capture_output=True,
            text=True,
            check=True
        )
        info['rustup_info'] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        info['rustup_info'] = "not_available"
    
    return info


def get_environment_variables() -> Dict[str, str]:
    """Get relevant environment variables."""
    relevant_vars = [
        'SOURCE_DATE_EPOCH',
        'PYTHONHASHSEED',
        'RUSTFLAGS',
        'CARGO_TARGET_DIR',
        'PATH',
        'HOME',
        'USER',
        'GITHUB_ACTIONS',
        'GITHUB_RUN_ID',
        'GITHUB_SHA',
        'GITHUB_REF'
    ]
    
    env_vars = {}
    for var in relevant_vars:
        value = os.environ.get(var, 'not_set')
        # Don't expose full PATH for security
        if var == 'PATH':
            env_vars[var] = f"{len(value.split(':'))} entries"
        else:
            env_vars[var] = value
    
    return env_vars


def get_pip_packages(venv_path: Path = None) -> List[Dict[str, str]]:
    """Get installed pip packages and versions."""
    packages = []
    try:
        pip_cmd = [sys.executable, '-m', 'pip', 'list', '--format=json']
        if venv_path:
            pip_cmd[0] = str(venv_path / 'bin' / 'python3')
        
        result = subprocess.run(
            pip_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        packages = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        pass
    
    return packages


def generate_build_environment(output_path: Path) -> None:
    """Generate build-environment.json file."""
    build_env = {
        "system": get_system_info(),
        "python": get_python_info(),
        "rust": get_rust_info(),
        "environment_variables": get_environment_variables(),
        "generated_at": subprocess.run(
            ['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(build_env, f, indent=2)
    
    print(f"✅ Generated build-environment.json at {output_path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate build-environment.json')
    parser.add_argument('--output', type=Path, required=True, help='Output path for build-environment.json')
    args = parser.parse_args()
    
    generate_build_environment(args.output)
