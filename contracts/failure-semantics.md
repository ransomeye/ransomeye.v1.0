# Failure Semantics Contract
**RansomEye v1.0 – Canonical Failure Semantics**

**AUTHORITATIVE**: This contract defines immutable failure behavior for all components in RansomEye v1.0.

**PRINCIPLE**: Silence is forbidden. Every failure must result in explicit state, explicit log classification, and explicit downstream behavior.

---

## Failure Matrix

| Failure Scenario | Component | Detection Method | Action | Emit State | Log Classification | Downstream Behavior | Error Code |
|-----------------|-----------|------------------|--------|------------|-------------------|---------------------|------------|
| **No events received** | All | Timeout threshold exceeded | Emit heartbeat/health event | `NO_EVENTS_RECEIVED` | `WARN` | Mark component as `STALE` | `EVENT_STREAM_STALLED` |
| **Events arrive late** | Core | `ingested_at - observed_at > 1 hour` | Accept with warning | `EVENT_LATE_ARRIVAL` | `WARN` | Mark event as `LATE_ARRIVAL` in metadata | `N/A` |
| **Events are duplicated** | Core | `event_id` exists in system | Reject duplicate | `EVENT_DUPLICATE_REJECTED` | `ERROR` | Do not process, do not update sequence | `DUPLICATE_EVENT_ID` |
| **Dependencies unavailable** | All | Dependency health check fails | Emit dependency failure event | `DEPENDENCY_UNAVAILABLE` | `ERROR` | Mark component as `DEGRADED` or `FAILED` | `DEPENDENCY_UNREACHABLE` |
| **Integrity chain breaks** | Core | `prev_hash_sha256` does not match previous event's `hash_sha256` | Reject event | `INTEGRITY_CHAIN_BROKEN` | `ERROR` | Do not process, mark chain as `BROKEN` | `INTEGRITY_VIOLATION` |
| **Schema validation fails** | Core | JSON Schema validation error | Reject event | `SCHEMA_VALIDATION_FAILED` | `ERROR` | Do not process, return validation errors | `SCHEMA_VIOLATION` |
| **Timestamp validation fails** | Core | RFC3339 parse error or timezone violation | Reject event | `TIMESTAMP_VALIDATION_FAILED` | `ERROR` | Do not process | `TIMESTAMP_PARSE_ERROR` or `TIMESTAMP_TIMEZONE_VIOLATION` |
| **Clock skew exceeds tolerance** | Core | `ingested_at - observed_at < -5 seconds` | Reject event | `CLOCK_SKEW_EXCEEDED` | `ERROR` | Do not process | `TIMESTAMP_FUTURE_BEYOND_TOLERANCE` |
| **Event too old** | Core | `ingested_at - observed_at > 30 days` | Reject event | `EVENT_TOO_OLD` | `ERROR` | Do not process | `TIMESTAMP_TOO_OLD` |
| **Sequence gap detected** | Core | `incoming_sequence > last_sequence + 1` | Accept with warning | `SEQUENCE_GAP_DETECTED` | `WARN` | Mark event as `HAS_GAPS` in metadata | `N/A` |
| **Out-of-order arrival** | Core | `incoming_sequence < last_sequence` | Accept with warning | `SEQUENCE_OUT_OF_ORDER` | `WARN` | Mark event as `OUT_OF_ORDER` in metadata | `N/A` |
| **Missing required fields** | Core | Schema validation: required field missing | Reject event | `SCHEMA_MISSING_REQUIRED_FIELD` | `ERROR` | Do not process, return field list | `SCHEMA_VIOLATION` |
| **Invalid component enum** | Core | Schema validation: `component` not in enum | Reject event | `INVALID_COMPONENT_ENUM` | `ERROR` | Do not process | `SCHEMA_VIOLATION` |
| **Invalid UUID format** | Core | Schema validation: `event_id` not valid UUID | Reject event | `INVALID_EVENT_ID_FORMAT` | `ERROR` | Do not process | `SCHEMA_VIOLATION` |
| **Invalid SHA256 format** | Core | Schema validation: `hash_sha256` not 64 hex chars | Reject event | `INVALID_HASH_FORMAT` | `ERROR` | Do not process | `SCHEMA_VIOLATION` |
| **Empty string violation** | Core | Schema validation: required string field is empty | Reject event | `EMPTY_STRING_VIOLATION` | `ERROR` | Do not process | `SCHEMA_VIOLATION` |
| **Network transmission failure** | Agent/DPI | Connection timeout or network error | Retry with exponential backoff, emit failure event | `NETWORK_TRANSMISSION_FAILED` | `ERROR` | Mark transmission as `FAILED`, retry | `NETWORK_ERROR` |
| **Component crash** | All | Process exit, unhandled exception | Emit crash event before exit, external monitoring detects | `COMPONENT_CRASHED` | `FATAL` | Mark component as `FAILED`, trigger recovery | `COMPONENT_CRASH` |
| **Resource exhaustion** | All | Memory/disk/CPU limits exceeded | Emit resource exhaustion event | `RESOURCE_EXHAUSTION` | `ERROR` | Mark component as `DEGRADED`, throttle processing | `RESOURCE_LIMIT_EXCEEDED` |
| **Configuration invalid** | All | Configuration validation fails at startup | Fail to start | `CONFIGURATION_INVALID` | `ERROR` | Do not start, exit with error code | `CONFIG_INVALID` |
| **Authentication failure** | All | Authentication/authorization check fails | Reject request, emit auth failure event | `AUTHENTICATION_FAILED` | `ERROR` | Do not process, increment failure counter | `AUTH_ERROR` |
| **Serialization failure** | All | JSON/Protobuf serialization error | Emit serialization failure event | `SERIALIZATION_FAILED` | `ERROR` | Do not transmit, log payload | `SERIALIZATION_ERROR` |
| **Deserialization failure** | Core | JSON/Protobuf deserialization error | Reject event | `DESERIALIZATION_FAILED` | `ERROR` | Do not process | `DESERIALIZATION_ERROR` |
| **Payload corruption** | Core | Payload structure invalid (not valid JSON object) | Reject event | `PAYLOAD_CORRUPTION` | `ERROR` | Do not process | `SCHEMA_VIOLATION` |
| **First event prev_hash not null** | Core | `sequence == 0` but `prev_hash_sha256` is not null | Reject event | `FIRST_EVENT_HASH_VIOLATION` | `ERROR` | Do not process | `SCHEMA_VIOLATION` |
| **Non-first event prev_hash null** | Core | `sequence > 0` but `prev_hash_sha256` is null | Reject event | `MISSING_PREV_HASH` | `ERROR` | Do not process | `SCHEMA_VIOLATION` |
| **Hash computation mismatch** | Core | Computed `hash_sha256` does not match provided `hash_sha256` | Reject event | `HASH_MISMATCH` | `ERROR` | Do not process | `INTEGRITY_VIOLATION` |

---

## Detailed Failure Behaviors

### 1. No Events Received

**Scenario**: A component that should be emitting events has not produced any events within a defined timeout period.

**Components Affected**: All components that generate events (linux_agent, windows_agent, dpi)

**Detection**:
- Monitor last event timestamp per `component_instance_id`
- If `current_time - last_event_time > TIMEOUT_THRESHOLD`, trigger detection
- TIMEOUT_THRESHOLD: 5 minutes for agents, 1 minute for DPI

**Action**:
- Emit a synthetic heartbeat/health event with component-specific metadata
- Event MUST follow canonical envelope schema
- Event MUST have `event_id` as UUID v4
- Event MUST have `payload.type = "health_check"`

**Emit State**: `NO_EVENTS_RECEIVED`

**Log Classification**: `WARN`

**Downstream Behavior**:
- Mark the `component_instance_id` as `STALE` in component registry
- Emit monitoring alert for stale component
- Continue processing other events normally

**Error Code**: `EVENT_STREAM_STALLED`

---

### 2. Events Arrive Late

**Scenario**: Event arrives with `ingested_at` that is significantly later than `observed_at`, beyond normal transmission delay.

**Components Affected**: Core (ingestion layer)

**Detection**: See Time Semantics Contract Section 4

**Action**: Accept the event but emit warning state

**Emit State**: `EVENT_LATE_ARRIVAL`

**Log Classification**: `WARN`

**Downstream Behavior**:
- Mark event metadata with `late_arrival: true`
- Store latency: `ingested_at - observed_at`
- Process event normally but flag for investigation

**Error Code**: `N/A` (accepted with warning)

---

### 3. Events Are Duplicated

**Scenario**: Event with identical `event_id` is received more than once.

**Components Affected**: Core (ingestion layer)

**Detection**: Exact match of `event_id` against in-memory or persistent set of processed event IDs

**Action**: Reject the duplicate event immediately

**Emit State**: `EVENT_DUPLICATE_REJECTED`

**Log Classification**: `ERROR`

**Downstream Behavior**:
- Do NOT process the duplicate event
- Do NOT update sequence tracking
- Do NOT modify integrity chain
- Do NOT increment counters
- Return explicit error response to sender (if applicable)

**Error Code**: `DUPLICATE_EVENT_ID`

---

### 4. Dependencies Unavailable

**Scenario**: A required dependency (service, database, API, network resource) is unreachable or failing health checks.

**Components Affected**: All components

**Detection**: Dependency health check returns failure or timeout

**Action**: Emit dependency failure event, degrade component operation

**Emit State**: `DEPENDENCY_UNAVAILABLE`

**Log Classification**: `ERROR`

**Downstream Behavior**:
- Mark component as `DEGRADED` if operation can continue with reduced functionality
- Mark component as `FAILED` if operation cannot continue
- Emit monitoring alert
- Implement circuit breaker pattern for repeated failures
- Retry with exponential backoff

**Error Code**: `DEPENDENCY_UNREACHABLE`

**Component-Specific Behavior**:
- **Agent**: If core is unavailable, buffer events locally until core is reachable (up to buffer limit)
- **Core**: If storage is unavailable, reject events until storage is available (do not buffer indefinitely)
- **DPI**: If agent is unavailable, log and continue processing

---

### 5. Integrity Chain Breaks

**Scenario**: `prev_hash_sha256` of incoming event does not match the `hash_sha256` of the previous event in the sequence for the same `component_instance_id`.

**Components Affected**: Core (validation layer)

**Detection**:
1. Retrieve last event for `component_instance_id`
2. Compare `incoming_event.integrity.prev_hash_sha256` with `last_event.integrity.hash_sha256`
3. If mismatch, integrity chain is broken

**Action**: Reject the event immediately

**Emit State**: `INTEGRITY_CHAIN_BROKEN`

**Log Classification**: `ERROR`

**Downstream Behavior**:
- Do NOT process the event
- Mark integrity chain for `component_instance_id` as `BROKEN`
- Emit security alert
- Log both hashes for forensic analysis
- Mark all subsequent events from this `component_instance_id` as `CHAIN_BROKEN` until manual intervention

**Error Code**: `INTEGRITY_VIOLATION`

---

### 6. Schema Validation Fails

**Scenario**: Event envelope does not conform to canonical JSON Schema.

**Components Affected**: Core (validation layer)

**Detection**: JSON Schema validation returns validation errors

**Action**: Reject the event immediately

**Emit State**: `SCHEMA_VALIDATION_FAILED`

**Log Classification**: `ERROR`

**Downstream Behavior**:
- Do NOT process the event
- Return detailed validation error messages (field path, error type, expected vs actual)
- Log the invalid event payload for debugging (truncated if too large)
- Increment validation failure counter per component

**Error Code**: `SCHEMA_VIOLATION`

**Common Validation Failures**:
- Missing required fields → `SCHEMA_MISSING_REQUIRED_FIELD`
- Invalid enum value → `INVALID_COMPONENT_ENUM`
- Invalid UUID format → `INVALID_EVENT_ID_FORMAT`
- Invalid SHA256 format → `INVALID_HASH_FORMAT`
- Empty string in required field → `EMPTY_STRING_VIOLATION`
- Wrong data type → `SCHEMA_TYPE_MISMATCH`
- Additional properties (schema has `additionalProperties: false`) → `SCHEMA_EXTRA_PROPERTY`

---

## Failure State Machine

**Component States**:
- `HEALTHY`: Normal operation, all dependencies available
- `DEGRADED`: Operating with reduced functionality, some dependencies unavailable
- `STALE`: No events received within timeout threshold
- `FAILED`: Critical failure, cannot continue operation
- `BROKEN`: Integrity chain broken, manual intervention required

**State Transitions**:
- `HEALTHY` → `DEGRADED`: Dependency unavailable (non-critical)
- `HEALTHY` → `STALE`: No events received (timeout)
- `HEALTHY` → `FAILED`: Critical dependency unavailable or component crash
- `HEALTHY` → `BROKEN`: Integrity chain broken
- `DEGRADED` → `HEALTHY`: All dependencies restored
- `DEGRADED` → `FAILED`: Critical dependency unavailable
- `STALE` → `HEALTHY`: Events received again
- `STALE` → `FAILED`: Extended staleness (configurable threshold)
- `FAILED` → `HEALTHY`: Recovery successful (requires manual intervention or automated recovery)
- `BROKEN` → `HEALTHY`: Manual intervention and chain repair

---

## Log Classification Levels

**INFO**: Normal operation, expected events, successful processing

**WARN**: Anomalies that do not prevent operation but require attention:
- Late arrival
- Sequence gaps
- Out-of-order arrival
- Clock skew within tolerance
- Component degraded

**ERROR**: Failures that prevent processing of specific events or degrade component functionality:
- Schema validation failures
- Integrity violations
- Duplicate events
- Dependency unavailability
- Timestamp violations

**FATAL**: Critical failures that cause component to exit or require immediate intervention:
- Component crash
- Resource exhaustion (if unrecoverable)
- Security violations (if critical)

---

## Implementation Requirements

All components implementing failure semantics MUST:

1. **Never silently fail**: Every failure MUST result in explicit state and log entry
2. **Never discard events silently**: Rejected events MUST be logged with full context
3. **Emit state for all conditions**: Use failure matrix states exactly as defined
4. **Classify logs correctly**: Use INFO/WARN/ERROR/FATAL as specified in failure matrix
5. **Return explicit error codes**: Use error codes exactly as defined in failure matrix
6. **Track component state**: Maintain component state machine as defined
7. **Implement timeout detection**: Monitor for "no events received" scenarios
8. **Validate all inputs**: Apply schema validation before any processing
9. **Check integrity chain**: Validate `prev_hash_sha256` for all non-first events
10. **Handle dependencies gracefully**: Emit dependency failure events, do not crash on dependency unavailability

---

**CONTRACT STATUS**: FROZEN  
**VERSION**: 1.0.0  
**HASH**: [PLACEHOLDER - SHA256 will be inserted here after bundle finalization]
