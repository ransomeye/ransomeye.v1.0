# Time Semantics Contract
**RansomEye v1.0 – Canonical Time Semantics**

**AUTHORITATIVE**: This contract defines immutable time semantics for all events in RansomEye v1.0.

---

## 1. Timestamp Fields

### 1.1 `observed_at`

**Definition**: The moment in time when the event was first observed at the source component, before any processing or transmission.

**Requirements**:
- MUST be an RFC3339-formatted timestamp string
- MUST be in UTC timezone (Z suffix or +00:00 offset)
- MUST be captured at the point of event observation, not later
- MUST NOT be modified after initial capture
- Format: `YYYY-MM-DDTHH:MM:SS.fffZ` or `YYYY-MM-DDTHH:MM:SSZ`

**Validation Rules**:
- MUST be parseable as a valid RFC3339 date-time
- MUST represent a valid point in time (no invalid dates/times)
- MUST NOT be in the future relative to system time when ingested
- Future tolerance check: `ingested_at - observed_at <= MAX_FUTURE_TOLERANCE` (see Section 2)

### 1.2 `ingested_at`

**Definition**: The moment in time when the event was ingested into the RansomEye system, after transmission and receipt.

**Requirements**:
- MUST be an RFC3339-formatted timestamp string
- MUST be in UTC timezone (Z suffix or +00:00 offset)
- MUST be captured at the point of system ingestion, immediately upon receipt
- MUST NOT be modified after capture
- Format: `YYYY-MM-DDTHH:MM:SS.fffZ` or `YYYY-MM-DDTHH:MM:SSZ`

**Validation Rules**:
- MUST be parseable as a valid RFC3339 date-time
- MUST represent a valid point in time
- MUST be set by the ingestion point, not by the source component
- MUST be >= `observed_at` for non-backdated events (see Section 3)

---

## 2. Clock Skew Tolerance

**Definition**: Maximum acceptable difference between component clock and ingestion point clock, accounting for transmission delay and clock drift.

**Policy**:
- **Maximum future tolerance**: `observed_at` MUST NOT be more than 5 seconds in the future relative to `ingested_at` when received
  - Formula: `ingested_at - observed_at <= 5 seconds`
  - Violation: Event MUST be rejected with `TIMESTAMP_FUTURE_BEYOND_TOLERANCE` error

- **Maximum past tolerance**: `observed_at` MUST NOT be more than 30 days in the past relative to `ingested_at` when received
  - Formula: `ingested_at - observed_at <= 30 days`
  - Violation: Event MUST be rejected with `TIMESTAMP_TOO_OLD` error

- **Clock skew detection**: If `ingested_at < observed_at` (future event), check if within 5-second tolerance
  - Within tolerance: Accept with warning log `CLOCK_SKEW_DETECTED`
  - Beyond tolerance: Reject with `TIMESTAMP_FUTURE_BEYOND_TOLERANCE`

**Rationale**:
- 5 seconds accounts for normal transmission delay and minor clock drift
- 30 days prevents replay attacks from very old events
- Explicit rejection prevents silent data corruption

---

## 3. Out-of-Order Arrival

**Definition**: Events arrive with `sequence` numbers that are not monotonically increasing relative to previously ingested events from the same `component_instance_id`.

**Policy**:
- **Detection**: Compare incoming `sequence` against last known `sequence` for `component_instance_id`
- **Gap detection**: If `incoming_sequence > last_sequence + 1`, gap detected
- **Reordering**: If `incoming_sequence < last_sequence`, out-of-order detected

**Behavior**:
1. **Gap (missing sequence numbers)**:
   - Accept the event (cannot reject valid data)
   - Emit state: `SEQUENCE_GAP_DETECTED`
   - Log classification: `WARN`
   - Store gap range: `(last_sequence + 1, incoming_sequence - 1)`
   - Downstream: Mark as `HAS_GAPS` in metadata

2. **Out-of-order (lower sequence than last seen)**:
   - Accept the event (cannot reject valid data)
   - Emit state: `SEQUENCE_OUT_OF_ORDER`
   - Log classification: `WARN`
   - Store out-of-order indicator for this `component_instance_id`
   - Downstream: Mark as `OUT_OF_ORDER` in metadata
   - **Note**: Out-of-order events are valid if they were delayed in transmission

3. **Duplicate sequence number**:
   - See Section 4 (Duplicate Arrival)

4. **Expected sequence**:
   - Accept the event
   - Emit state: `SEQUENCE_CONTINUOUS`
   - Log classification: `INFO`
   - Update last known sequence

**Rationale**: We cannot reject valid events due to transmission issues, but we must explicitly track and report ordering anomalies.

---

## 4. Late Arrival

**Definition**: Event arrives with `ingested_at` that is significantly later than `observed_at`, beyond normal transmission delay.

**Policy**:
- **Threshold**: `ingested_at - observed_at > 1 hour` is considered "late arrival"
- **Detection**: Compare timestamps during ingestion
- **Behavior**:
  - Accept the event (cannot reject valid data)
  - Emit state: `EVENT_LATE_ARRIVAL`
  - Log classification: `WARN`
  - Store latency: `ingested_at - observed_at`
  - Downstream: Mark as `LATE_ARRIVAL` in metadata

**Rationale**: Late arrivals may indicate network issues, component downtime, or replay attacks. Accept the data but flag it for investigation.

---

## 5. Duplicate Arrival

**Definition**: Event with identical `event_id` is received more than once.

**Policy**:
- **Detection**: Check if `event_id` exists in the system (exact match)
- **Behavior**:
  - **First occurrence**: Process normally
  - **Subsequent occurrences**: 
    - Reject the duplicate event
    - Emit state: `EVENT_DUPLICATE_REJECTED`
    - Log classification: `ERROR`
    - Do NOT update sequence tracking
    - Do NOT modify integrity chain
    - Return explicit error: `DUPLICATE_EVENT_ID`

**Rationale**: Duplicates indicate retransmission bugs or replay attacks. Explicit rejection prevents data corruption.

---

## 6. Validation Failure Scenarios

### 6.1 Invalid Timestamp Format

**Detection**: `observed_at` or `ingested_at` cannot be parsed as RFC3339
**Behavior**:
- Reject the event
- Emit state: `TIMESTAMP_INVALID_FORMAT`
- Log classification: `ERROR`
- Return error: `TIMESTAMP_PARSE_ERROR`

### 6.2 Timestamp Missing

**Detection**: `observed_at` or `ingested_at` is missing or null
**Behavior**:
- Reject the event (schema validation should catch this first)
- Emit state: `TIMESTAMP_MISSING`
- Log classification: `ERROR`
- Return error: `TIMESTAMP_MISSING`

### 6.3 Timestamp Timezone Violation

**Detection**: Timestamp is not in UTC (contains non-zero offset or non-Z suffix)
**Behavior**:
- Reject the event
- Emit state: `TIMESTAMP_NON_UTC`
- Log classification: `ERROR`
- Return error: `TIMESTAMP_TIMEZONE_VIOLATION`

---

## 7. Implementation Requirements

All components implementing time semantics MUST:

1. Use system UTC time for all timestamp generation
2. Validate timestamps immediately upon receipt
3. Emit explicit state for all conditions (see failure-semantics.md)
4. Log all violations with appropriate classification
5. Reject invalid events with explicit error codes (never silently discard)
6. Track sequence numbers per `component_instance_id`
7. Maintain last-seen sequence map for gap/out-of-order detection
8. Maintain event ID set for duplicate detection (implementation-specific retention policy)

---

**CONTRACT STATUS**: FROZEN  
**VERSION**: 1.0.0  
**HASH**: [PLACEHOLDER - SHA256 will be inserted here after bundle finalization]
