# Phase A: Trust & Credential Hardening - Implementation Status

**AUTHORITATIVE:** Implementation of Phase A fixes per FIX MASTER PLAN

## Phase A1: Database Bootstrap Validator ✅

### Status: Enhanced

**File**: `validation/harness/db_bootstrap_validator.py`

**Enhancements Applied**:
- ✅ Enhanced PEER authentication detection
- ✅ Explicit instructions for pg_hba.conf changes
- ✅ OS-aware guidance (Ubuntu/Debian vs RHEL/CentOS)
- ✅ Clear step-by-step instructions
- ✅ No auto-editing (diagnostic-only)
- ✅ No security downgrade
- ✅ Fail-closed on detection

**Behavior**:
- Detects PostgreSQL authentication failure reasons
- If PEER auth detected: Prints explicit instruction with pg_hba.conf location
- Provides exact commands to fix (user must execute manually)
- Does NOT continue execution on failure

## Phase A2: Credential Scoping ✅

### Status: Implemented

**File**: `schemas/08_db_users_roles.sql`

**Implementation**:
- ✅ Separate DB users per service:
  - `ransomeye_ingest` - Ingest Service
  - `ransomeye_correlation` - Correlation Engine
  - `ransomeye_ai_core` - AI Core Service
  - `ransomeye_policy_engine` - Policy Engine (read-only)
  - `ransomeye_ui` - UI Backend (read-only)

- ✅ Explicit GRANT statements:
  - Ingest: Write to raw_events, machines, component_instances, event_validation_log
  - Correlation: Write to incidents, incident_stages, evidence
  - AI Core: Write to AI metadata tables
  - Policy Engine: Read-only (no write access)
  - UI: Read-only (no write access)

- ✅ Explicit REVOKE statements:
  - Revoke ALL from PUBLIC role
  - Default deny enforcement

- ✅ No shared super-user pattern:
  - Removed shared `ransomeye` user pattern
  - Each service has dedicated role

**Next Steps**:
- Update service code to use service-specific users
- Remove hardcoded defaults from service code
- Update installer to create roles and set passwords

## Implementation Notes

### Database Role Creation
Roles are created with `PASSWORD NULL` - passwords MUST be set via:
```sql
ALTER ROLE ransomeye_ingest PASSWORD 'secure_password';
```

This enforces:
- No default passwords
- Explicit password setting required
- Fail-closed if password not set

### Service Code Updates Required
Each service must be updated to use its specific role:
- `services/ingest/app/main.py` → `RANSOMEYE_DB_USER=ransomeye_ingest`
- `services/correlation-engine/app/db.py` → `RANSOMEYE_DB_USER=ransomeye_correlation`
- `services/ai-core/app/db.py` → `RANSOMEYE_DB_USER=ransomeye_ai_core`
- `services/policy-engine/app/db.py` → `RANSOMEYE_DB_USER=ransomeye_policy_engine`
- `services/ui/backend/main.py` → `RANSOMEYE_DB_USER=ransomeye_ui`

### Installer Updates Required
Installer must:
- Create roles from `08_db_users_roles.sql`
- Prompt for passwords (no defaults)
- Set passwords via ALTER ROLE
- Fail if passwords not provided

## Validation

Phase A implementation:
- ✅ A1: Database bootstrap validator enhanced
- ✅ A2: Credential scoping schema created

**Ready for**: Phase B (Installer & Bootstrap Correction)
