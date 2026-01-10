# RansomEye v1.0 Installer Bundle
**Authoritative Installer Specification – Phase 3**

**AUTHORITATIVE**: This bundle contains the immutable installer specification for RansomEye v1.0. This specification defines the canonical, non-negotiable installer behavior that all future installer implementations MUST conform to.

---

## Installer Bundle Metadata

### Version
**Version**: `1.0.0`  
**Release Date**: [PLACEHOLDER - Date will be inserted here after bundle finalization]  
**Phase**: Phase 3 – Installer Before Services  
**Allowed Languages**: Bash, Python 3.10+ (NO other languages permitted)

### Integrity Hash
**SHA256 Hash**: `[PLACEHOLDER - SHA256 hash will be inserted here after bundle finalization]`

**Hash Computation Method**:
1. Concatenate all installer specification files in this bundle in lexicographic order:
   - `install.manifest.schema.json`
   - `install.manifest.json`
   - `env.contract.md`
   - `env.contract.json`
   - `privilege-model.md`
   - `installer-failure-policy.md`
   - `installer-failure-policy.json`
   - `INSTALLER_BUNDLE.md` (this file, excluding this hash field)
2. Compute SHA256 hash of the concatenated content
3. Insert hash in this field (replacing `[PLACEHOLDER]`)
4. Recompute hash of updated `INSTALLER_BUNDLE.md`
5. Insert final hash in this field

**Note**: After hash insertion, this bundle is FROZEN and MUST NOT be modified.

---

## Bundle Contents

This bundle contains the following authoritative installer specifications:

### 1. Installation Manifest (`install.manifest.schema.json`, `install.manifest.json`)
- **Schema**: JSON Schema (Draft 2020-12) defining canonical manifest structure
- **Example**: Example manifest with placeholders (NO path assumptions)
- **Purpose**: Machine-readable manifest containing complete installation state. Single source of truth for runtime configuration.

### 2. Environment Variable Contract (`env.contract.md`, `env.contract.json`)
- **Human-Readable Spec**: Complete environment variable specification (Markdown)
- **Machine-Readable Policy**: Machine-readable environment variable contract (JSON)
- **Purpose**: Defines exact environment variables that all services MUST read. No path computation allowed.

### 3. Privilege Model (`privilege-model.md`)
- **Specification**: Complete privilege model for installer and runtime
- **Purpose**: Defines installer privilege requirements, runtime privilege drop rules, and agent/DPI exception boundaries

### 4. Installer Failure Semantics (`installer-failure-policy.md`, `installer-failure-policy.json`)
- **Human-Readable Policy**: Complete failure semantics specification (Markdown)
- **Machine-Readable Policy**: Machine-readable failure policy (JSON)
- **Purpose**: Defines installer failure behavior, rollback rules, idempotency requirements, and recovery procedures

---

## Installer Design Principles

### Fail-Closed Philosophy
- **Zero Partial State**: Installer MUST leave zero partial state on failure
- **Immediate Abort**: Installation failures MUST abort installation immediately
- **Complete Rollback**: All changes MUST be rolled back on failure

### Idempotency Philosophy
- **Same Input, Same Output**: Running installer with same parameters multiple times MUST produce identical result
- **No Duplicate Operations**: Running installer on already-installed system MUST skip operations that are already complete
- **No Errors on Re-run**: Running installer on already-installed system MUST NOT produce errors

### Path Injection Philosophy
- **NO PATH COMPUTATION**: Services MUST read all paths from environment variables
- **NO HARDCODED PATHS**: All paths MUST be absolute and injected via environment variables
- **NO PATH ASSUMPTIONS**: Installer MUST support installation at any path (commercial self-installation)

### Manifest as Single Source of Truth
- **Authoritative Manifest**: Installation manifest is the single source of truth for runtime configuration
- **Environment Variable Injection**: Environment variables are injected from manifest at service startup
- **No Path Computation**: Services MUST NOT compute paths internally

---

## Compatibility Rules

### Breaking vs Non-Breaking Changes

**CRITICAL**: This installer bundle is **IMMUTABLE** and **FROZEN**. No changes are permitted after finalization and hash insertion.

**Hypothetical Future Compatibility Rules** (for reference only – not applicable to v1.0):

#### Breaking Changes (Require New Major Version)
- Adding required fields to manifest schema
- Removing required fields from manifest schema
- Changing field types (e.g., string → integer)
- Changing environment variable names
- Removing environment variables
- Changing privilege requirements
- Changing failure semantics (e.g., changing ABORT to CONTINUE, or vice versa)
- Modifying rollback rules
- Removing idempotency guarantees

#### Non-Breaking Changes (Allow Minor/Patch Version Increment)
- Adding optional fields to manifest schema
- Adding optional environment variables
- Clarifying documentation without changing behavior
- Adding examples or use cases
- Fixing typos in documentation that do not affect semantics

**Note**: For RansomEye v1.0, the above rules are academic only. This bundle is **FROZEN** and will never change. Any modifications require creating a new version (v2.0.0) with a new bundle.

---

## Freeze Statement

**FROZEN AS OF**: [PLACEHOLDER - Date will be inserted here after bundle finalization]

This installer bundle is **IMMUTABLE** and **CANONICAL**.

### Immutability Rules

1. **NO MODIFICATIONS ALLOWED**: After finalization and hash insertion, this specification MUST NOT be modified under any circumstances.

2. **NO EXTENSIONS ALLOWED**: Installer implementations MUST NOT extend this specification. Any additional fields or behaviors are violations and will result in rejection.

3. **NO INTERPRETATION VARIANCE**: All installer implementations MUST implement this specification exactly as specified. No deviation, no "interpretation", no "convenience" modifications.

4. **CONFORMANCE IS MANDATORY**: All future installer implementations in RansomEye v1.0 MUST conform to this specification. Any installer that violates this specification MUST be rejected and deleted.

5. **VALIDATION IS REQUIRED**: All installer implementations MUST validate against manifest schema and environment variable contract. Validation failures MUST result in explicit rejection.

### Enforcement

- **Manifest Validation**: All installer implementations MUST validate generated manifest against `install.manifest.schema.json`
- **Environment Variable Enforcement**: All services MUST read paths from environment variables as defined in `env.contract.json`
- **Failure Policy Enforcement**: All installer implementations MUST follow failure semantics from `installer-failure-policy.json` exactly
- **Privilege Model Enforcement**: All installer implementations MUST follow privilege model from `privilege-model.md` exactly

### Consequences of Violation

Any installer implementation that violates this specification:

1. **WILL BE REJECTED** during code review
2. **WILL BE DELETED** if discovered post-deployment
3. **WILL NOT BE SUPPORTED** as part of RansomEye v1.0

### Approval Process

This bundle requires explicit approval before finalization:

- [ ] Installer bundle reviewed and approved
- [ ] All specifications validated for completeness and correctness
- [ ] Manifest schema validated (JSON Schema Draft 2020-12)
- [ ] Environment variable contract validated
- [ ] Privilege model validated
- [ ] Failure semantics validated
- [ ] SHA256 hash computed and inserted
- [ ] Freeze date recorded
- [ ] Bundle declared FROZEN

**Current Status**: `PENDING_FINALIZATION`

---

## Installer Specification Alignment

This installer specification is **exactly aligned** with the frozen system contracts from Phase 1 and database schema from Phase 2:

### Phase 1: System Contracts
- **Event Envelope Contract**: Component enum matches installer enabled components exactly (`linux_agent`, `windows_agent`, `dpi`, `core`)
- **Time Semantics Contract**: Installer timestamps MUST use RFC3339 UTC format (matches `installed_at` in manifest)
- **Failure Semantics Contract**: Installer failure behavior aligns with system failure semantics (fail-closed, explicit state)

### Phase 2: Database Schema
- **Schema Bundle Hash**: Installer MUST verify schema bundle hash matches Phase 2 schema bundle (stored in manifest)
- **Contract Bundle Hash**: Installer MUST verify contract bundle hash matches Phase 1 contract bundle (stored in manifest)
- **Manifest Integrity**: Manifest schema and validation ensure compatibility with database schema requirements

---

## Installer Implementation Requirements

All installer implementations MUST:

1. **Be Idempotent**: Running installer multiple times with same parameters MUST produce identical result
2. **Be Fail-Closed**: Installation failures MUST abort immediately, rollback all changes
3. **Support Any Path**: Installer MUST support installation at any absolute path (no path assumptions)
4. **Validate Manifest**: Generated manifest MUST validate against `install.manifest.schema.json`
5. **Inject Environment Variables**: Services MUST receive all paths via environment variables (no path computation)
6. **Follow Privilege Model**: Installer MUST run as root/Administrator, runtime MUST drop to dedicated user/group
7. **Follow Failure Semantics**: Installer MUST follow failure semantics from `installer-failure-policy.json` exactly
8. **Log All Operations**: Installer MUST log all operations to file and stderr
9. **Exit with Explicit Codes**: Installer MUST use defined exit codes (0=success, 1=fatal, 2=rollback failure, 3=invalid args, 4=insufficient privileges)

---

## Allowed Languages

**ONLY** the following languages are permitted for installer implementation:

- **Bash**: Shell scripts (POSIX-compliant, bash-specific features allowed)
- **Python 3.10+**: Python scripts (minimum Python 3.10 required)

**NO other languages are permitted**. This restriction ensures:
- Portability across POSIX systems
- Minimal dependencies
- Ease of maintenance and review
- Security (no compiled binaries, source code is readable)

---

## Installer Responsibilities

The installer is responsible for:

1. **Discovering Install Root**: Installer MUST accept install root as parameter or environment variable. No assumptions about install location.

2. **Creating System User**: Installer MUST create runtime user/group with appropriate UID/GID. User/group MUST be created before any files are installed.

3. **Generating Manifest**: Installer MUST generate `install.manifest.json` conforming to `install.manifest.schema.json`. Manifest MUST contain all required fields with valid values.

4. **Injecting Paths via ENV**: Installer MUST ensure services receive all paths via environment variables. No service may compute paths internally.

5. **Enforcing Fail-Closed Startup**: Installer MUST ensure services fail-closed on startup (missing environment variables, invalid paths, insufficient permissions MUST cause startup failure).

---

## Scope Limitations

**IMPORTANT**: This bundle contains **ONLY** installer specification. It does NOT contain:

- ❌ Service implementation code
- ❌ Agent code
- ❌ DPI code
- ❌ Database schema changes
- ❌ Systemd unit files (not yet)
- ❌ Installer implementation code (only specification)

This is **Phase 3 – Installer Specification ONLY**.

---

## Legal and Status

**Installer Bundle Status**: `AUTHORITATIVE`  
**Installer Bundle Version**: `1.0.0`  
**Installer Bundle Phase**: `Phase 3 – Installer Before Services`  
**Immutable After**: `[PLACEHOLDER - Date after finalization]`  
**SHA256 Hash**: `[PLACEHOLDER - Hash after finalization]`  
**Allowed Languages**: `Bash, Python 3.10+`

**THIS BUNDLE IS FROZEN AND CANNOT BE MODIFIED.**

---

**END OF INSTALLER BUNDLE**
