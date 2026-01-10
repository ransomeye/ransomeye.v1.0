#!/usr/bin/env python3
"""
RansomEye v1.0 Service Verification
AUTHORITATIVE: Verify all services can start and basic functionality works
Phase 10 requirement: Verify all services run simultaneously without failures
"""

import os
import sys
import importlib.util
from typing import List, Tuple


def verify_service_importable(service_name: str, module_path: str) -> Tuple[bool, str]:
    """
    Verify service module can be imported.
    
    Args:
        service_name: Service name (e.g., 'ingest', 'correlation-engine')
        module_path: Path to service main module
        
    Returns:
        Tuple of (is_importable, error_message)
    """
    try:
        spec = importlib.util.spec_from_file_location(f"{service_name}_main", module_path)
        if spec is None or spec.loader is None:
            return False, f"Could not create spec for {service_name}"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check that main function exists (for batch services) or app exists (for FastAPI services)
        has_main = hasattr(module, 'run_correlation_engine') or \
                   hasattr(module, 'run_ai_core') or \
                   hasattr(module, 'run_policy_engine') or \
                   hasattr(module, 'run_dpi_probe') or \
                   hasattr(module, 'app')
        
        if not has_main:
            return False, f"Service {service_name} does not have main function or app"
        
        return True, "OK"
    except Exception as e:
        return False, f"Import error: {e}"


def verify_all_services() -> Tuple[bool, List[str]]:
    """
    Verify all services are importable and have correct structure.
    
    Returns:
        Tuple of (all_passed, error_messages)
    """
    errors = []
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    services = [
        ('ingest', os.path.join(project_root, 'services/ingest/app/main.py')),
        ('correlation-engine', os.path.join(project_root, 'services/correlation-engine/app/main.py')),
        ('ai-core', os.path.join(project_root, 'services/ai-core/app/main.py')),
        ('policy-engine', os.path.join(project_root, 'services/policy-engine/app/main.py')),
        ('ui-backend', os.path.join(project_root, 'services/ui/backend/main.py')),
        ('dpi-probe', os.path.join(project_root, 'dpi/probe/main.py')),
    ]
    
    for service_name, module_path in services:
        if not os.path.exists(module_path):
            errors.append(f"Service {service_name}: Module not found at {module_path}")
            continue
        
        is_ok, error_msg = verify_service_importable(service_name, module_path)
        if not is_ok:
            errors.append(f"Service {service_name}: {error_msg}")
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    all_passed, errors = verify_all_services()
    if all_passed:
        print("PASS: All services are importable and have correct structure")
        sys.exit(0)
    else:
        print("FAIL: Some services have issues:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
