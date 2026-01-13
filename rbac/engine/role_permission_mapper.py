#!/usr/bin/env python3
"""
RansomEye v1.0 RBAC Role-Permission Mapper
AUTHORITATIVE: Defines role-permission mappings (exactly five roles)
Python 3.10+ only
"""

from typing import Dict, Set, List

# ============================================================================
# ROLE-PERMISSION MAPPINGS
# ============================================================================
# Exactly five roles with explicit permission assignments

# ============================================================================
# ROLE-PERMISSION MAPPINGS (FROZEN - EXACT MATCH REQUIRED)
# ============================================================================
# Exactly five roles with explicit permission assignments per specification

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    'SUPER_ADMIN': {
        # All permissions - absolute authority
        'incident:view',
        'incident:view_all',
        'incident:acknowledge',
        'incident:resolve',
        'incident:close',
        'incident:export',
        'incident:assign',
        'policy:view',
        'policy:create',
        'policy:update',
        'policy:delete',
        'policy:execute',
        'policy:simulate',
        'tre:view',
        'tre:execute',
        'tre:rollback',
        'tre:view_all',
        'haf:view',
        'haf:create_override',
        'haf:approve',
        'haf:reject',
        'forensics:view',
        'forensics:export',
        'report:view',
        'report:generate',
        'report:export',
        'report:view_all',
        'agent:install',
        'agent:uninstall',
        'agent:update',
        'agent:view',
        'user:create',
        'user:delete',
        'user:role_assign',
        'system:view_config',
        'system:modify_config',
        'system:view_logs',
        'system:manage_users',
        'system:manage_roles',
        'billing:view',
        'billing:manage',
        'audit:view',
        'audit:view_all',
        'audit:export'
    },
    
    'SECURITY_ANALYST': {
        # Incident management
        'incident:view',
        'incident:view_all',
        'incident:acknowledge',
        'incident:resolve',
        'incident:close',
        'incident:export',
        'incident:assign',
        # Threat Response (execute actions)
        'tre:view',
        'tre:execute',
        'tre:rollback',
        'tre:view_all',
        # Human Authority
        'haf:view',
        'haf:create_override',
        'haf:approve',
        # Forensics
        'forensics:view',
        'forensics:export',
        # Reporting
        'report:view',
        'report:generate',
        'report:export',
        # Audit
        'audit:view',
        'audit:view_all',
        'audit:export'
        # EXPLICITLY FORBIDDEN: policy:edit, user:*, agent:*, billing:*
    },
    
    'POLICY_MANAGER': {
        # Policy management
        'policy:view',
        'policy:create',
        'policy:update',
        'policy:delete',
        'policy:execute',
        'policy:simulate',
        # Incident viewing (for context only)
        'incident:view',
        'incident:view_all',
        # Threat Response viewing (no execute)
        'tre:view',
        'tre:view_all',
        # Human Authority
        'haf:view',
        'haf:create_override',
        'haf:approve',
        # Reporting
        'report:view',
        'report:generate',
        'report:export',
        # Audit
        'audit:view',
        'audit:view_all'
        # EXPLICITLY FORBIDDEN: tre:execute, forensics:*, user:*, agent:*, billing:*
    },
    
    'IT_ADMIN': {
        # Agent management
        'agent:install',
        'agent:uninstall',
        'agent:update',
        'agent:view',
        # System management
        'system:view_config',
        'system:modify_config',
        'system:view_logs',
        # Incident viewing (for context only)
        'incident:view',
        'incident:view_all',
        # Threat Response viewing (no execute)
        'tre:view',
        'tre:view_all',
        # Reporting (view only)
        'report:view',
        'report:export',
        # Audit (view only)
        'audit:view'
        # EXPLICITLY FORBIDDEN: incident:*, tre:execute, forensics:*, policy:*, user:*, billing:*
    },
    
    'AUDITOR': {
        # Read-only access to everything
        'incident:view',
        'incident:view_all',
        'incident:export',
        'policy:view',
        'tre:view',
        'tre:view_all',
        'haf:view',
        'forensics:view',
        'forensics:export',
        'report:view',
        'report:export',
        'report:view_all',
        'audit:view',
        'audit:view_all',
        'audit:export'
        # EXPLICITLY FORBIDDEN: ALL action buttons, ALL editing, user:*, agent:*, billing:*
    }
}


def get_role_permissions(role: str) -> Set[str]:
    """
    Get permissions for role.
    
    Args:
        role: Role name
    
    Returns:
        Set of permission names
    """
    return ROLE_PERMISSIONS.get(role, set())


def get_all_roles() -> List[str]:
    """
    Get all role names.
    
    Returns:
        List of role names (exactly five)
    """
    return list(ROLE_PERMISSIONS.keys())


def get_all_permissions() -> Set[str]:
    """
    Get all permission names.
    
    Returns:
        Set of all permission names
    """
    all_perms = set()
    for perms in ROLE_PERMISSIONS.values():
        all_perms.update(perms)
    return all_perms
