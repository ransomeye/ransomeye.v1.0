#!/usr/bin/env python3
"""
RansomEye v1.0 Core Status Schema
AUTHORITATIVE: Validation for core_status.json
"""

from typing import Dict, Any, Tuple, List


REQUIRED_TOP_LEVEL = {
    "schema_version",
    "state",
    "timestamp",
    "global_state",
    "failure_reason_code",
    "failure_reason",
    "security_events",
    "components",
    "start_order",
    "core_pid",
    "core_token"
}


REQUIRED_COMPONENT_FIELDS = {
    "state",
    "pid",
    "last_health",
    "last_error",
    "started_at",
    "last_successful_cycle",
    "failure_reason"
}


VALID_STATES = {
    "INIT",
    "STARTING",
    "RUNNING",
    "DEGRADED",
    "FAILED",
    "STOPPING",
    "STOPPED"
}


def validate_status(status: Dict[str, Any]) -> Tuple[bool, str]:
    missing = REQUIRED_TOP_LEVEL - set(status.keys())
    if missing:
        return False, f"Missing required fields: {sorted(missing)}"

    if status.get("state") not in VALID_STATES:
        return False, "Invalid state value"
    if status.get("global_state") not in VALID_STATES and status.get("global_state") != "SECURITY_DEGRADED":
        return False, "Invalid global_state value"

    components = status.get("components", {})
    if not isinstance(components, dict) or not components:
        return False, "components must be a non-empty object"

    for name, component in components.items():
        if not isinstance(component, dict):
            return False, f"Component {name} is not an object"
        missing_fields = REQUIRED_COMPONENT_FIELDS - set(component.keys())
        if missing_fields:
            return False, f"Component {name} missing fields: {sorted(missing_fields)}"
        if component.get("state") not in VALID_STATES:
            return False, f"Component {name} has invalid state"

    if not isinstance(status.get("security_events"), list):
        return False, "security_events must be a list"
    if not isinstance(status.get("start_order"), list):
        return False, "start_order must be a list"

    return True, ""
