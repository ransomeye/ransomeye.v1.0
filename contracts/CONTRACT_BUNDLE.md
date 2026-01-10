# RansomEye v1.0 Contract Bundle
**Canonical System Contracts – Phase 1**

**AUTHORITATIVE**: This bundle contains the immutable system contracts for RansomEye v1.0. These contracts define the canonical, non-negotiable specifications that all future components MUST conform to.

---

## Contract Bundle Metadata

### Version
**Version**: `1.0.0`  
**Release Date**: [PLACEHOLDER - Date will be inserted here after bundle finalization]  
**Phase**: Phase 1 – System Contracts

### Integrity Hash
**SHA256 Hash**: `[PLACEHOLDER - SHA256 hash will be inserted here after bundle finalization]`

**Hash Computation Method**:
1. Concatenate all contract files in this bundle in lexicographic order:
   - `event-envelope.schema.json`
   - `event-envelope.proto`
   - `time-semantics.md`
   - `time-semantics.policy.json`
   - `failure-semantics.md`
   - `failure-semantics.policy.json`
   - `CONTRACT_BUNDLE.md` (this file, excluding this hash field)
2. Compute SHA256 hash of the concatenated content
3. Insert hash in this field (replacing `[PLACEHOLDER]`)
4. Recompute hash of updated `CONTRACT_BUNDLE.md`
5. Insert final hash in this field

**Note**: After hash insertion, this bundle is FROZEN and MUST NOT be modified.

---

## Bundle Contents

This bundle contains the following canonical contracts:

### 1. Event Envelope Contract
- **JSON Schema**: `event-envelope.schema.json` (JSON Schema Draft 2020-12)
- **Protobuf Definition**: `event-envelope.proto`
- **Purpose**: Defines the canonical, immutable structure for all event envelopes in RansomEye v1.0

### 2. Time Semantics Contract
- **Human-Readable Spec**: `time-semantics.md`
- **Machine-Readable Policy**: `time-semantics.policy.json`
- **Purpose**: Defines explicit, enforceable rules for timestamp handling, clock skew, out-of-order arrival, late arrival, and duplicates

### 3. Failure Semantics Contract
- **Structured Failure Matrix**: `failure-semantics.md`
- **Machine-Readable Policy**: `failure-semantics.policy.json`
- **Purpose**: Defines explicit behavior for all failure scenarios with mandatory state emission, log classification, and downstream behavior

---

## Compatibility Rules

### Breaking vs Non-Breaking Changes

**CRITICAL**: This contract bundle is **IMMUTABLE** and **FROZEN**. No changes are permitted after finalization and hash insertion.

**Hypothetical Future Compatibility Rules** (for reference only – not applicable to v1.0):

#### Breaking Changes (Require New Major Version)
- Adding required fields to event envelope
- Removing required fields from event envelope
- Changing field types (e.g., string → integer)
- Changing enum values or removing enum values
- Changing validation rules (e.g., increasing strictness, removing allowed values)
- Changing failure semantics (e.g., changing REJECT to ACCEPT, or vice versa)
- Changing timeout thresholds or tolerance values
- Changing component states or state transitions
- Modifying integrity chain requirements

#### Non-Breaking Changes (Allow Minor/Patch Version Increment)
- Adding optional fields (NOT APPLICABLE – no optional fields allowed)
- Adding new enum values (NOT APPLICABLE – enum is frozen)
- Clarifying documentation without changing behavior
- Adding examples or use cases
- Fixing typos in documentation that do not affect semantics

**Note**: For RansomEye v1.0, the above rules are academic only. This bundle is **FROZEN** and will never change. Any modifications require creating a new version (v2.0.0) with a new bundle.

---

## Freeze Statement

**FROZEN AS OF**: [PLACEHOLDER - Date will be inserted here after bundle finalization]

This contract bundle is **IMMUTABLE** and **CANONICAL**. 

### Immutability Rules

1. **NO MODIFICATIONS ALLOWED**: After finalization and hash insertion, these contracts MUST NOT be modified under any circumstances.

2. **NO EXTENSIONS ALLOWED**: Components MUST NOT extend these contracts. Any additional fields or behaviors are violations and will result in rejection.

3. **NO INTERPRETATION VARIANCE**: All components MUST implement these contracts exactly as specified. No deviation, no "interpretation", no "convenience" modifications.

4. **CONFORMANCE IS MANDATORY**: All future code in RansomEye v1.0 MUST conform to these contracts. Any code that violates these contracts MUST be rejected and deleted.

5. **VALIDATION IS REQUIRED**: All components MUST validate inputs against these contracts before processing. Validation failures MUST result in explicit rejection as defined in the Failure Semantics Contract.

### Enforcement

- **Schema Validation**: All events MUST be validated against `event-envelope.schema.json` before processing.
- **Time Policy Enforcement**: All timestamp handling MUST follow `time-semantics.policy.json` exactly.
- **Failure Policy Enforcement**: All failure handling MUST follow `failure-semantics.policy.json` exactly.

### Consequences of Violation

Any component, service, or system that violates these contracts:

1. **WILL BE REJECTED** during code review
2. **WILL BE DELETED** if discovered post-deployment
3. **WILL NOT BE SUPPORTED** as part of RansomEye v1.0

### Approval Process

This bundle requires explicit approval before finalization:

- [ ] Contract bundle reviewed and approved
- [ ] All contracts validated for completeness and correctness
- [ ] SHA256 hash computed and inserted
- [ ] Freeze date recorded
- [ ] Bundle declared FROZEN

**Current Status**: `PENDING_FINALIZATION`

---

## Contract References

### Canonical URIs

All contracts in this bundle have canonical identifiers:

- Event Envelope JSON Schema: `https://ransomeye.v1.0/contracts/event-envelope`
- Event Envelope Protobuf: `ransomeye.v1.EventEnvelope`
- Time Semantics Policy: `https://ransomeye.v1.0/contracts/time-semantics-policy`
- Failure Semantics Policy: `https://ransomeye.v1.0/contracts/failure-semantics-policy`

### Versioning

- **Contract Bundle Version**: `1.0.0` (semantic versioning)
- **JSON Schema Version**: Draft 2020-12 (fixed, cannot change)
- **Protobuf Version**: proto3 (fixed, cannot change)
- **Time Semantics Version**: `1.0.0` (must match bundle version)
- **Failure Semantics Version**: `1.0.0` (must match bundle version)

---

## Implementation Requirements

All implementations MUST:

1. **Validate Against Schemas**: Use `event-envelope.schema.json` for JSON validation and `event-envelope.proto` for Protobuf validation
2. **Enforce Time Policies**: Implement all validation rules from `time-semantics.policy.json`
3. **Enforce Failure Policies**: Implement all failure handling from `failure-semantics.policy.json`
4. **Emit Required States**: Emit all states as defined in the failure matrix
5. **Classify Logs Correctly**: Use log classifications (INFO/WARN/ERROR/FATAL) exactly as specified
6. **Return Error Codes**: Use error codes exactly as defined in the failure matrix
7. **Never Silence Failures**: Every failure MUST result in explicit state and log entry

---

## Scope Limitations

**IMPORTANT**: This bundle contains **ONLY** system contracts. It does NOT contain:

- ❌ Service implementation code
- ❌ Installer scripts or configurations
- ❌ Database schemas or migrations
- ❌ Deployment configurations
- ❌ Testing code
- ❌ Documentation beyond contract specifications

This is **Phase 1 – System Contracts ONLY**.

---

## Legal and Status

**Contract Bundle Status**: `AUTHORITATIVE`  
**Contract Bundle Version**: `1.0.0`  
**Contract Bundle Phase**: `Phase 1 – System Contracts`  
**Immutable After**: `[PLACEHOLDER - Date after finalization]`  
**SHA256 Hash**: `[PLACEHOLDER - Hash after finalization]`

**THIS BUNDLE IS FROZEN AND CANNOT BE MODIFIED.**

---

**END OF CONTRACT BUNDLE**
