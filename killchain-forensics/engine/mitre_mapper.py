#!/usr/bin/env python3
"""
RansomEye KillChain & Forensics - MITRE ATT&CK Mapper
AUTHORITATIVE: Deterministic mapping of events to MITRE ATT&CK techniques
"""

from typing import Dict, Any, Optional


class MITREMappingError(Exception):
    """Base exception for MITRE mapping errors."""
    pass


class AmbiguousMappingError(MITREMappingError):
    """Raised when MITRE mapping is ambiguous."""
    pass


class MITREMapper:
    """
    Deterministic mapping of security events to MITRE ATT&CK techniques.
    
    All mappings are deterministic (no randomness).
    Same inputs always produce same outputs.
    """
    
    # MITRE technique mapping (deterministic rules)
    TECHNIQUE_MAPPING = {
        'process_creation': {
            'default': 'T1055',  # Process Injection
            'suspicious_parent': 'T1055.001',
            'scheduled_task': 'T1053',
            'service_creation': 'T1543.003'
        },
        'file_access': {
            'default': 'T1005',  # Data from Local System
            'sensitive_file': 'T1005',
            'credential_file': 'T1003.001'
        },
        'network_connection': {
            'default': 'T1071',  # Application Layer Protocol
            'c2_communication': 'T1071.001',
            'dns_query': 'T1071.004'
        },
        'registry_modification': {
            'default': 'T1112',  # Modify Registry
            'persistence': 'T1547.001'
        },
        'service_creation': {
            'default': 'T1543.003'  # Windows Service
        },
        'scheduled_task': {
            'default': 'T1053.005'  # Scheduled Task
        },
        'user_activity': {
            'default': 'T1078',  # Valid Accounts
            'privilege_escalation': 'T1078.002'
        },
        'memory_access': {
            'default': 'T1005',  # Data from Local System
            'credential_dump': 'T1003.001'
        },
        'credential_access': {
            'default': 'T1003',  # OS Credential Dumping
            'lsass': 'T1003.001',
            'sam': 'T1003.002'
        },
        'lateral_movement': {
            'default': 'T1021',  # Remote Services
            'rdp': 'T1021.001',
            'smb': 'T1021.002'
        },
        'data_exfiltration': {
            'default': 'T1041'  # Exfiltration Over C2 Channel
        }
    }
    
    # Tactic mapping
    TACTIC_MAPPING = {
        'T1055': 'Execution',
        'T1055.001': 'Execution',
        'T1053': 'Execution',
        'T1543.003': 'Persistence',
        'T1005': 'Collection',
        'T1003.001': 'Credential Access',
        'T1071': 'Command and Control',
        'T1071.001': 'Command and Control',
        'T1071.004': 'Command and Control',
        'T1112': 'Defense Evasion',
        'T1053.005': 'Execution',
        'T1078': 'Defense Evasion',
        'T1078.002': 'Privilege Escalation',
        'T1003': 'Credential Access',
        'T1003.002': 'Credential Access',
        'T1021': 'Lateral Movement',
        'T1021.001': 'Lateral Movement',
        'T1021.002': 'Lateral Movement',
        'T1041': 'Exfiltration'
    }
    
    # Stage mapping
    STAGE_MAPPING = {
        'Reconnaissance': 'reconnaissance',
        'Resource Development': 'resource_development',
        'Initial Access': 'initial_access',
        'Execution': 'execution',
        'Persistence': 'persistence',
        'Privilege Escalation': 'privilege_escalation',
        'Defense Evasion': 'defense_evasion',
        'Credential Access': 'credential_access',
        'Discovery': 'discovery',
        'Lateral Movement': 'lateral_movement',
        'Collection': 'collection',
        'Command and Control': 'command_and_control',
        'Exfiltration': 'exfiltration',
        'Impact': 'impact'
    }
    
    @staticmethod
    def map_event(event: Dict[str, Any]) -> Dict[str, str]:
        """
        Map security event to MITRE ATT&CK technique.
        
        Args:
            event: Security event dictionary
        
        Returns:
            Dictionary with mitre_technique_id, mitre_tactic, mitre_stage
        
        Raises:
            AmbiguousMappingError: If mapping is ambiguous
            MITREMappingError: If mapping fails
        """
        event_type = event.get('event_type', 'other')
        
        # Get technique mapping for event type
        type_mapping = MITREMapper.TECHNIQUE_MAPPING.get(event_type, {})
        
        if not type_mapping:
            raise MITREMappingError(f"No MITRE mapping for event type: {event_type}")
        
        # Determine specific technique based on event metadata
        technique_id = type_mapping.get('default')
        
        # Check for specific indicators
        metadata = event.get('metadata', {})
        if event_type == 'process_creation':
            if metadata.get('scheduled_task'):
                technique_id = type_mapping.get('scheduled_task', technique_id)
            elif metadata.get('service_creation'):
                technique_id = type_mapping.get('service_creation', technique_id)
            elif metadata.get('suspicious_parent'):
                technique_id = type_mapping.get('suspicious_parent', technique_id)
        elif event_type == 'file_access':
            if metadata.get('credential_file'):
                technique_id = type_mapping.get('credential_file', technique_id)
        elif event_type == 'network_connection':
            if metadata.get('c2_communication'):
                technique_id = type_mapping.get('c2_communication', technique_id)
            elif metadata.get('dns_query'):
                technique_id = type_mapping.get('dns_query', technique_id)
        elif event_type == 'credential_access':
            if metadata.get('lsass'):
                technique_id = type_mapping.get('lsass', technique_id)
            elif metadata.get('sam'):
                technique_id = type_mapping.get('sam', technique_id)
        elif event_type == 'lateral_movement':
            if metadata.get('rdp'):
                technique_id = type_mapping.get('rdp', technique_id)
            elif metadata.get('smb'):
                technique_id = type_mapping.get('smb', technique_id)
        
        if not technique_id:
            raise AmbiguousMappingError(f"Ambiguous MITRE mapping for event type: {event_type}")
        
        # Get tactic
        tactic = MITREMapper.TACTIC_MAPPING.get(technique_id)
        if not tactic:
            raise MITREMappingError(f"No tactic mapping for technique: {technique_id}")
        
        # Get stage
        stage = MITREMapper.STAGE_MAPPING.get(tactic)
        if not stage:
            raise MITREMappingError(f"No stage mapping for tactic: {tactic}")
        
        return {
            'mitre_technique_id': technique_id,
            'mitre_tactic': tactic,
            'mitre_stage': stage
        }
