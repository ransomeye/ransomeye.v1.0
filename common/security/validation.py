#!/usr/bin/env python3
"""
RansomEye v1.0 Common Security - Input Validation
AUTHORITATIVE: Validate untrusted input to prevent injection and malformed data
"""

import re
import sys
import uuid
from typing import Any, Dict, List, Optional


def validate_incident_id(incident_id: str) -> str:
    """
    Validate incident ID format.
    
    Security: Prevents injection and malformed IDs.
    Terminates Core immediately if ID is invalid.
    
    Args:
        incident_id: Incident ID to validate
        
    Returns:
        Validated incident ID
        
    Raises:
        SystemExit: Terminates Core immediately if ID is invalid
    """
    if not incident_id:
        error_msg = "SECURITY VIOLATION: Empty incident ID"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    # Validate UUID format (incident IDs should be UUIDs)
    try:
        uuid.UUID(incident_id)
    except ValueError:
        error_msg = f"SECURITY VIOLATION: Invalid incident ID format: {incident_id[:50]}"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    # Check for injection patterns
    if re.search(r'[;"\'\\]|--|\/\*|\*\/|xp_|sp_', incident_id, re.IGNORECASE):
        error_msg = "SECURITY VIOLATION: Incident ID contains injection patterns"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    # Limit length
    if len(incident_id) > 100:
        error_msg = "SECURITY VIOLATION: Incident ID too long"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    return incident_id


def validate_incident_structure(incident: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate incident data structure from database.
    
    Security: Validates types and bounds before processing.
    Terminates Core immediately if structure is malformed.
    
    Args:
        incident: Incident dictionary to validate
        
    Returns:
        Validated incident dictionary
        
    Raises:
        SystemExit: Terminates Core immediately if structure is invalid
    """
    if not isinstance(incident, dict):
        error_msg = "SECURITY VIOLATION: Incident data is not a dictionary"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    # Required fields
    required_fields = ['incident_id', 'machine_id', 'current_stage', 'confidence_score']
    for field in required_fields:
        if field not in incident:
            error_msg = f"SECURITY VIOLATION: Incident missing required field: {field}"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(3)  # RUNTIME_ERROR
    
    # Validate incident_id format
    validate_incident_id(str(incident['incident_id']))
    
    # Validate machine_id
    if not isinstance(incident['machine_id'], str) or len(incident['machine_id']) > 100:
        error_msg = "SECURITY VIOLATION: Invalid machine_id format"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    # Validate current_stage
    valid_stages = ['CLEAN', 'SUSPICIOUS', 'PROBABLE', 'CONFIRMED']
    if incident['current_stage'] not in valid_stages:
        error_msg = f"SECURITY VIOLATION: Invalid current_stage: {incident['current_stage']}"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    # Validate confidence_score bounds
    if not isinstance(incident['confidence_score'], (int, float)):
        error_msg = "SECURITY VIOLATION: confidence_score is not numeric"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    confidence = float(incident['confidence_score'])
    if confidence < 0.0 or confidence > 100.0:
        error_msg = f"SECURITY VIOLATION: confidence_score out of bounds: {confidence}"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    # Validate optional fields if present
    if 'total_evidence_count' in incident:
        if not isinstance(incident['total_evidence_count'], int) or incident['total_evidence_count'] < 0:
            error_msg = "SECURITY VIOLATION: Invalid total_evidence_count"
            print(f"FATAL: {error_msg}", file=sys.stderr)
            sys.exit(3)  # RUNTIME_ERROR
    
    return incident


def validate_incidents_list(incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate list of incidents.
    
    Security: Validates all incidents in list.
    Terminates Core immediately if any incident is invalid.
    
    Args:
        incidents: List of incident dictionaries
        
    Returns:
        Validated list of incident dictionaries
        
    Raises:
        SystemExit: Terminates Core immediately if any incident is invalid
    """
    if not isinstance(incidents, list):
        error_msg = "SECURITY VIOLATION: Incidents data is not a list"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    # Limit list size to prevent DoS
    MAX_INCIDENTS = 10000
    if len(incidents) > MAX_INCIDENTS:
        error_msg = f"SECURITY VIOLATION: Incidents list too large: {len(incidents)} > {MAX_INCIDENTS}"
        print(f"FATAL: {error_msg}", file=sys.stderr)
        sys.exit(3)  # RUNTIME_ERROR
    
    # Validate each incident
    validated_incidents = []
    for incident in incidents:
        validated_incidents.append(validate_incident_structure(incident))
    
    return validated_incidents
