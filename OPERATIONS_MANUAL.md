# RansomEye v1.0 GA - Operations Manual

**AUTHORITATIVE:** Enterprise and military operator manual for RansomEye v1.0 GA

**Version:** 1.0.0  
**Date:** 2024-01-15  
**Audience:** Enterprise SOC, SRE, Security Operations, Military Operators, Auditors

---

## Table of Contents

1. [Installation & Supply Chain Verification](#1-installation--supply-chain-verification)
2. [Database Bootstrap Troubleshooting](#2-database-bootstrap-troubleshooting)
3. [Validation & Platform Awareness](#3-validation--platform-awareness)
4. [Operational Monitoring ("Glass Cockpit")](#4-operational-monitoring-glass-cockpit)
5. [Incident Intelligence & Confidence Scores](#5-incident-intelligence--confidence-scores)
6. [Forensics & Legal Admissibility](#6-forensics--legal-admissibility)
7. [Survivability & Agent Autonomy](#7-survivability--agent-autonomy)
8. [Audit & Compliance Notes](#8-audit--compliance-notes)

---

## 1. Installation & Supply Chain Verification

### Overview

RansomEye v1.0 GA implements mandatory supply chain verification to enable offline, cryptographic verification of all shipped artifacts. This is required for air-gapped military and government deployments where network access is prohibited during installation.

### SBOM (Software Bill of Materials)

Every RansomEye release bundle includes:

- `manifest.json`: Machine-readable SBOM listing every artifact with SHA256 hashes
- `manifest.json.sig`: ed25519 cryptographic signature of manifest.json
- `verify_sbom.py`: Standalone verification utility (air-gap ready)

### Verifying SBOM Offline

**Prerequisites:**
- Python 3.10+ installed
- `cryptography` library installed: `pip install cryptography`
- Public key file (`public_key.pem`) or key directory with signing keys

**Verification Steps:**

1. **Locate release bundle:**
   ```bash
   cd /path/to/ransomeye-v1.0
   ```

2. **Verify manifest and signature files exist:**
   ```bash
   ls -la manifest.json manifest.json.sig
   ```

3. **Run offline verification:**
   ```bash
   python3 verify_sbom.py \
     --release-root /path/to/ransomeye-v1.0 \
     --manifest manifest.json \
     --signature manifest.json.sig \
     --public-key /path/to/public_key.pem
   ```

   **Alternative (using key directory):**
   ```bash
   python3 verify_sbom.py \
     --release-root /path/to/ransomeye-v1.0 \
     --manifest manifest.json \
     --signature manifest.json.sig \
     --key-dir /path/to/keys \
     --signing-key-id vendor-release-key-1
   ```

4. **Expected Output (Success):**
   ```
   ✓ SBOM verification passed
     - Manifest signature: VALID
     - All artifact hashes: VERIFIED
   ```

### What a FAILED SBOM Verification Means

**Manifest Signature Invalid:**
- The manifest.json file has been tampered with
- The signature file (manifest.json.sig) is incorrect or corrupted
- The public key does not match the signing key used to create the signature
- **Action:** Do not proceed with installation. Contact vendor for replacement bundle.

**Artifact Hash Mismatch:**
- One or more artifacts in the release bundle do not match their expected SHA256 hashes
- Artifacts may have been corrupted during transfer or tampered with
- **Action:** Do not proceed with installation. Re-download release bundle and verify again.

**Manifest File Missing:**
- The manifest.json file is not present in the release bundle
- **Action:** Do not proceed with installation. This indicates an incomplete or invalid release bundle.

**Signature File Missing:**
- The manifest.json.sig file is not present
- **Action:** Do not proceed with installation. Installation is fail-closed by design.

### Why Installation is Fail-Closed by Design

RansomEye installers are designed with fail-closed behavior:

- **No warnings-only mode:** Installation either succeeds with full verification or fails completely
- **No override flags:** There is no way to bypass SBOM verification
- **No "best effort" installation:** Partial installation is not permitted
- **Deterministic verification:** Same bundle + same public key → same verification result

This design ensures:
- **Supply chain integrity:** Only verified, untampered artifacts are installed
- **Audit compliance:** Installation failures are explicit and logged
- **Military/government requirements:** Meets air-gapped deployment verification requirements

### Public Key Distribution

For air-gapped deployments, the public key must be distributed separately from the release bundle:

- **Distribution method:** Secure channel (e.g., separate USB drive, secure file transfer)
- **Key format:** PEM-encoded ed25519 public key
- **Key location:** Store in secure location, verify key fingerprint before use
- **Key rotation:** Contact vendor for new public keys if signing keys are rotated

---

## 2. Database Bootstrap Troubleshooting

### Overview

RansomEye v1.0 GA includes pre-flight database diagnostic validation to prevent opaque startup crashes caused by PostgreSQL authentication misconfiguration. This validator runs before any schema validation or service startup.

### PEER vs MD5 Authentication

PostgreSQL supports multiple authentication methods:

- **PEER authentication:** Uses operating system user identity (default on Debian/Ubuntu)
  - Requires database user to match system user
  - Does not accept password authentication
  - Common on local-only deployments

- **MD5 authentication:** Uses password-based authentication
  - Requires password for connection
  - Works across network boundaries
  - Required for RansomEye (uses `gagan` / `gagan` credentials)

### Database Bootstrap Validator

The validator (`core/diagnostics/db_bootstrap_validator.py`) performs:

1. **Connection attempt:** Attempts to connect using configured credentials (`gagan` / `gagan`)
2. **Error inspection:** Parses PostgreSQL error messages for authentication failures
3. **PEER detection:** Specifically detects "peer authentication failed" or "password ignored" errors
4. **Actionable guidance:** Emits clear error message with pg_hba.conf location and instructions

### Interpreting db_bootstrap_validator Errors

**Error: "PEER authentication failed" or "password ignored"**

**Meaning:** PostgreSQL is configured to use PEER authentication, but RansomEye is attempting password authentication.

**Error Message Example:**
```
FATAL: PostgreSQL is rejecting password authentication.
Detected PEER authentication in pg_hba.conf.
Please change the authentication method from peer to md5 for user gagan.
pg_hba.conf location: /etc/postgresql/14/main/pg_hba.conf
```

**Resolution Steps:**

1. **Locate pg_hba.conf:**
   - Debian/Ubuntu: `/etc/postgresql/<version>/main/pg_hba.conf`
   - Red Hat/CentOS: `/var/lib/pgsql/data/pg_hba.conf`
   - The error message will indicate the detected location

2. **Edit pg_hba.conf:**
   ```bash
   sudo nano /etc/postgresql/14/main/pg_hba.conf
   ```

3. **Find the line for user `gagan`:**
   ```
   local   all   gagan   peer
   ```

4. **Change `peer` to `md5`:**
   ```
   local   all   gagan   md5
   ```

5. **Reload PostgreSQL:**
   ```bash
   sudo systemctl reload postgresql
   ```

6. **Restart RansomEye Core:**
   ```bash
   sudo systemctl restart ransomeye-core
   ```

**Error: "Database connection failed" (generic)**

**Meaning:** Database connection failed for reasons other than PEER authentication.

**Possible Causes:**
- Database server is not running
- Network connectivity issues
- Incorrect host/port configuration
- Database does not exist
- User does not exist or password is incorrect

**Resolution:** Check database server status, network connectivity, and configuration.

### Where pg_hba.conf is Typically Located

**Debian/Ubuntu:**
- `/etc/postgresql/<version>/main/pg_hba.conf`
- Example: `/etc/postgresql/14/main/pg_hba.conf`

**Red Hat/CentOS:**
- `/var/lib/pgsql/data/pg_hba.conf`

**Detection:** The validator attempts to detect the location automatically and includes it in the error message.

### What RansomEye Will Not Auto-Fix (By Design)

RansomEye is designed with **diagnostics-only, never auto-fix** behavior:

- **No auto-editing pg_hba.conf:** The validator will not modify PostgreSQL configuration files
- **No credential rotation:** The validator will not change database credentials
- **No authentication weakening:** The validator will not suggest or implement weaker authentication methods
- **No retries with alternate modes:** The validator will not attempt alternate authentication methods
- **No fallback behavior:** The validator will not continue startup if validation fails

**Rationale:**
- **Security boundaries:** Configuration changes require operator approval
- **Audit compliance:** All configuration changes must be logged and authorized
- **Fail-closed design:** System must not proceed with misconfiguration
- **Operator control:** Operators must explicitly approve all changes

---

## 3. Validation & Platform Awareness

### Overview

RansomEye v1.0 GA implements OS-aware validation to prevent invalid or misleading validation failures caused by running platform-specific validation tracks on incompatible operating systems. This is required for audit correctness, reproducibility, and legal defensibility.

### Why Linux and Windows Validation Tracks Are Separated

**Platform-Specific Requirements:**

- **Linux tracks:** Require Linux-specific features (eBPF, systemd, Linux kernel APIs)
  - TRACK_1_DETERMINISM
  - TRACK_2_REPLAY
  - TRACK_3_FAILURE_INJECTION
  - TRACK_4_SCALE_STRESS
  - TRACK_5_SECURITY_SAFETY
  - TRACK_6_AGENT_LINUX

- **Windows tracks:** Require Windows-specific features (ETW, Windows APIs)
  - TRACK_6_AGENT_WINDOWS

**Cross-Platform Execution Issues:**

- **Linux host + Windows track:** ETW APIs do not exist on Linux → validation fails
- **Windows host + Linux track:** eBPF APIs do not exist on Windows → validation fails
- **Result:** Invalid audit evidence, false negatives, confusing failures

### How OS-Aware Validation Prevents Audit Corruption

**Validation Executor Behavior:**

1. **OS Detection:** Executor detects host OS using `platform.system()`
2. **Track Mapping:** Executor maintains explicit mapping of tracks to required OS
3. **Hard Gating:** Executor blocks incompatible tracks with fail-closed behavior
4. **Clear Errors:** Executor emits explicit error messages explaining why track is invalid

**Example Error (Linux Host + Windows Track):**
```
FATAL: Cannot run Windows-only validation tracks on Linux host.

Blocked tracks: TRACK_6_AGENT_WINDOWS
Host OS: Linux
Required OS: Windows

Windows tracks require ETW (Event Tracing for Windows) which is not available on Linux.
Please run Windows tracks on a Windows host.
```

**Example Error (Windows Host + Linux Track):**
```
FATAL: Cannot run Linux-only validation tracks on Windows host.

Blocked tracks: TRACK_1_DETERMINISM, TRACK_2_REPLAY, TRACK_3_FAILURE_INJECTION, ...
Host OS: Windows
Required OS: Linux

Linux tracks require eBPF and Linux-specific features which are not available on Windows.
Please run Linux tracks on a Linux host.
```

### Common Operator Mistakes and How They Are Blocked

**Mistake 1: Attempting to run Windows tracks on Linux**

**Operator Action:** `python3 phase_c_executor.py --execution-mode windows`

**System Response:** Hard failure with explicit error message. Installation/validation aborted.

**Rationale:** Prevents invalid audit results and false negatives.

**Mistake 2: Attempting to run Linux tracks on Windows**

**Operator Action:** `python3 phase_c_executor.py --execution-mode linux`

**System Response:** Hard failure with explicit error message. Installation/validation aborted.

**Rationale:** Prevents invalid audit results and false negatives.

**Mistake 3: Attempting to run all tracks on single host**

**Operator Action:** Attempting to run both Linux and Windows tracks on same host

**System Response:** Executor detects OS mismatch and blocks incompatible tracks.

**Rationale:** GA verdict requires both Phase C-L (Linux) and Phase C-W (Windows) results, but they must be run on appropriate hosts.

### Correct Validation Workflow

**For Linux Validation:**
1. Run on Linux host
2. Execute Phase C-L tracks (TRACK_1 through TRACK_6_AGENT_LINUX)
3. Collect results

**For Windows Validation:**
1. Run on Windows host
2. Execute Phase C-W tracks (TRACK_6_AGENT_WINDOWS)
3. Collect results

**GA Verdict:** Requires both Phase C-L and Phase C-W results from appropriate hosts.

---

## 4. Operational Monitoring ("Glass Cockpit")

### Overview

RansomEye v1.0 GA provides operational telemetry through the `/health/metrics` endpoint. This endpoint monitors the system's own health, not threats, enabling operators to detect failures before security guarantees are compromised.

### Accessing the Endpoint

**Endpoint:** `GET /health/metrics`

**Base URL:** `http://localhost:8000` (Ingest service)

**Example Request:**
```bash
curl http://localhost:8000/health/metrics
```

**Example Response:**
```json
{
  "system_status": "HEALTHY",
  "ingest_rate_eps": 45.23,
  "db_write_latency_ms": 12.5,
  "queue_depth": 0,
  "agent_heartbeat_lag_sec": 5.2
}
```

### System Status Meanings

**HEALTHY:**
- All metrics within expected bounds
- Database latency < 500ms
- Agent heartbeat lag < 120 seconds
- System operating normally
- **Operational Implication:** No action required

**DEGRADED:**
- Elevated latency or backlog detected
- Database latency between 500ms and 1000ms
- Agent heartbeat lag between 120 and 300 seconds
- System performance impacted but functional
- **Operational Implication:** Monitor closely, investigate performance issues

**CRITICAL:**
- Database unreachable or ingest stalled
- Database latency > 1000ms
- Agent heartbeat lag > 300 seconds
- System may be unable to process events
- **Operational Implication:** Immediate investigation required. System may not be processing events correctly.

### Metric Definitions

**ingest_rate_eps (Events Per Second):**
- **Definition:** 1-minute moving average of events ingested per second
- **Calculation:** Count of events in last 60 seconds / 60
- **Normal Range:** Varies by deployment (typically 10-100 EPS)
- **Interpretation:** Sudden drops may indicate agent connectivity issues or ingest pipeline problems

**db_write_latency_ms (Milliseconds):**
- **Definition:** Average latency of last ~100 database writes
- **Calculation:** Average of last 100 write operation latencies
- **Normal Range:** < 100ms (healthy), 100-500ms (degraded), > 500ms (critical)
- **Interpretation:** High latency indicates database performance issues or connection pool exhaustion

**queue_depth (Integer):**
- **Definition:** Current size of ingest/processing buffer
- **Normal Range:** 0 (no backlog)
- **Interpretation:** Non-zero values indicate backpressure or processing delays

**agent_heartbeat_lag_sec (Seconds):**
- **Definition:** Maximum time since last valid agent heartbeat
- **Calculation:** MAX(EXTRACT(EPOCH FROM (NOW() - observed_at))) from health_heartbeat table
- **Normal Range:** < 60 seconds (healthy), 60-120 seconds (degraded), > 120 seconds (critical)
- **Interpretation:** High lag indicates agent connectivity issues or agent failures

### What CRITICAL Implies Operationally

**When system_status = "CRITICAL":**

1. **Database Unreachable:**
   - RansomEye cannot write events to database
   - Events may be lost or queued
   - **Action:** Check database server status, network connectivity, connection pool

2. **High Database Latency:**
   - Database writes are taking > 1000ms
   - System may be unable to keep up with event volume
   - **Action:** Investigate database performance, check for connection pool exhaustion

3. **Agent Heartbeat Lag:**
   - No agents have reported in > 300 seconds
   - Agents may be offline or unable to reach Core
   - **Action:** Check agent connectivity, network issues, agent service status

**Operational Response:**
- **Immediate:** Check system logs, database status, network connectivity
- **Short-term:** Investigate root cause, check for resource exhaustion
- **Long-term:** Review capacity planning, consider scaling

### What Data is Intentionally NOT Exposed (Privacy Guarantees)

The `/health/metrics` endpoint is designed for operational telemetry only. It explicitly does NOT expose:

- **Hostnames:** No machine identifiers
- **IP Addresses:** No network identifiers
- **Tenant Identifiers:** No multi-tenant data
- **Incident Metadata:** No threat intelligence or incident details
- **File Paths:** No filesystem information
- **Payload Samples:** No event payload data

**Rationale:**
- **Privacy compliance:** Meets GDPR, HIPAA, and other privacy regulations
- **Security boundaries:** Prevents information leakage through monitoring endpoints
- **Operational focus:** Endpoint monitors system health, not threats

---

## 5. Incident Intelligence & Confidence Scores

### Overview

RansomEye v1.0 GA implements a correlation state machine that transforms the Correlation Engine from a signal passthrough into a true aggregator. This reduces false positives and makes the system usable by enterprise SOC teams.

### Incident Stages

**SUSPICIOUS:**
- **Definition:** Initial incident stage, created when first signal is detected
- **Confidence Range:** 0.0 to < 30.0
- **Operational Meaning:** Single signal detected, requires additional evidence
- **SOC Action:** Monitor, wait for additional signals before investigation

**PROBABLE:**
- **Definition:** Intermediate stage, reached when confidence accumulates
- **Confidence Range:** 30.0 to < 70.0
- **Operational Meaning:** Multiple corroborating signals detected, likely threat
- **SOC Action:** Begin investigation, gather additional context

**CONFIRMED:**
- **Definition:** Final stage, reached when confidence threshold met
- **Confidence Range:** 70.0 to 100.0
- **Operational Meaning:** High confidence threat confirmed by multiple evidence sources
- **SOC Action:** Escalate to incident response, execute containment procedures

### How Confidence Scores Accumulate

**Accumulation Formula:**
```
new_confidence = min(current_confidence + signal_confidence, 100.0)
```

**Signal Weights (Deterministic):**
- CORRELATION_PATTERN: 10.0
- PROCESS_ACTIVITY: 15.0
- FILE_ACTIVITY: 15.0
- NETWORK_INTENT: 12.0
- DPI_FLOW: 20.0
- DNS_QUERY: 8.0
- DECEPTION: 25.0
- AI_SIGNAL: 18.0

**Example Accumulation:**
1. Signal 1 (Linux Agent): +10.0 → Confidence: 10.0, Stage: SUSPICIOUS
2. Signal 2 (Process Activity): +15.0 → Confidence: 25.0, Stage: SUSPICIOUS
3. Signal 3 (DPI Flow): +20.0 → Confidence: 45.0, Stage: PROBABLE (transition)
4. Signal 4 (Deception): +25.0 → Confidence: 70.0, Stage: CONFIRMED (transition)

### Why Single Events Never Become Incidents

**GA-BLOCKING Rule:** Single signal → SUSPICIOUS only (no direct CONFIRMED)

**Rationale:**
- **False positive reduction:** Single signals are often noise or benign activity
- **SOC usability:** Prevents alert fatigue from low-confidence incidents
- **Correlation requirement:** Multiple signals provide stronger evidence of actual threats

**Operational Implication:**
- Operators will see SUSPICIOUS incidents from single signals
- These incidents require additional evidence to escalate
- Operators can monitor for accumulating signals before taking action

### How This Reduces Alert Fatigue

**Before (Signal Passthrough):**
- Every signal → New incident
- 1000 signals → 1000 incidents
- All incidents at same stage (SUSPICIOUS)
- SOC overwhelmed with low-confidence alerts

**After (State Machine Aggregation):**
- Multiple signals → Single incident
- 1000 signals → ~50-100 incidents (deduplicated)
- Incidents progress through stages (SUSPICIOUS → PROBABLE → CONFIRMED)
- SOC focuses on high-confidence incidents

**Deduplication:**
- Same machine + same process + within 1 hour → Single incident
- Incident ID is stable for the same entity
- New evidence added to existing incident (not new incident created)

**Result:** Dramatic reduction in alert volume, focus on actionable incidents.

---

## 6. Forensics & Legal Admissibility

### Overview

RansomEye v1.0 GA implements absolute report determinism to guarantee legal chain-of-custody. Reports generated for the same incident snapshot are bit-for-bit identical forever, regardless of when or where they are rendered.

### How Deterministic Reports Work

**Incident-Anchored Timestamps:**
- All timestamps in reports derive from Incident Snapshot Time or Incident Closure Time
- `datetime.now()` or system time is FORBIDDEN in report rendering
- Timestamps are fetched from database (`resolved_at` or `last_observed_at`)

**Evidence Content Separation:**
- Reports have two layers:
  - **Evidence layer:** Facts, timelines, hashes (defines report hash)
  - **Presentation layer:** Branding, visuals, CSS (excluded from hash)

**Deterministic Rendering:**
- Stable field ordering (sorted by display_order)
- Stable numeric formatting (fixed precision)
- Stable timestamp formatting (RFC3339 UTC)
- No random IDs in evidence content
- No environment-dependent metadata

### Why Report Hashes Never Change

**Hash Domain:**
- Report hash is computed on **evidence content only** (not full report)
- Evidence content excludes all branding elements (logo, CSS, theme)
- Evidence content uses incident-anchored timestamps (not system time)

**Result:**
- Same incident snapshot → Same evidence content → Same hash
- Logo swap → Evidence content unchanged → Hash unchanged
- Time passage → Evidence content unchanged → Hash unchanged

**Example:**
```
Report A (generated at 2024-01-15 10:00:00): SHA256 = abc123...
Report B (generated at 2024-01-15 15:00:00): SHA256 = abc123... (identical)
Report C (logo swapped, generated at 2024-01-16 10:00:00): SHA256 = abc123... (identical)
```

### How to Prove Chain-of-Custody

**Report Record Fields:**
- `content_hash`: SHA256 hash of evidence content
- `signature`: ed25519 signature of evidence content
- `generated_at`: Incident-anchored timestamp (not system time)
- `incident_id`: Links report to incident

**Verification Steps:**

1. **Verify Hash:**
   ```bash
   sha256sum report_evidence_content.bin
   # Compare with content_hash in report record
   ```

2. **Verify Signature:**
   ```bash
   # Use public key to verify signature
   python3 verify_signature.py --public-key public_key.pem --signature <signature> --content <evidence_content>
   ```

3. **Verify Timestamp:**
   - Check that `generated_at` matches incident `resolved_at` or `last_observed_at`
   - Verify timestamp is not system-generated

**Legal Admissibility:**
- **Deterministic:** Same incident → Same hash (proves report integrity)
- **Signed:** Cryptographic signature proves report authenticity
- **Timestamped:** Incident-anchored timestamp proves temporal accuracy
- **Auditable:** All report generation events logged in audit ledger

### How Logo/Branding Does NOT Affect Evidence

**Separation of Concerns:**
- **Evidence content:** Core facts, timelines, hashes (hashed and signed)
- **Presentation content:** Logo, CSS, theme (not hashed or signed)

**Implementation:**
- Reports are rendered in two steps:
  1. Generate evidence content (hashable, deterministic)
  2. Wrap with branding elements (presentation only)

**Result:**
- Replacing logo file → Evidence content unchanged → Hash unchanged
- Changing CSS theme → Evidence content unchanged → Hash unchanged
- Modifying branding → Evidence content unchanged → Hash unchanged

**Operational Implication:**
- Operators can customize branding without affecting legal admissibility
- Evidence integrity is preserved regardless of presentation changes
- Report hashes remain stable for chain-of-custody purposes

---

## 7. Survivability & Agent Autonomy

### Overview

RansomEye v1.0 GA implements agent autonomy to ensure endpoint agents remain secure, deterministic, and enforce policy even if the Core/C2 server is destroyed, unreachable, or under attack. This is mandatory for military deployments, cyber-warfare survivability, and zero-trust enforcement.

### What Happens When Core is Offline

**Agent Behavior:**

1. **Core Connectivity Check:**
   - Agent checks Core health endpoint (`http://localhost:8000/health`)
   - Timeout: 2 seconds
   - If unreachable → Core is offline

2. **Policy Cache Loading:**
   - Agent loads cached policy from disk (`/var/lib/ransomeye/agent/cached_policy.json`)
   - Policy is integrity-checked (SHA256 hash verification)
   - If policy invalid or missing → Default deny policy applied

3. **Autonomous Enforcement:**
   - Agent enforces cached policy autonomously
   - No fail-open behavior
   - All enforcement decisions are logged

### Meaning of "GA-BLOCKING" Logs

**Log Prefix:** `GA-BLOCKING:`

**Operational Meaning:**
- These logs indicate critical security enforcement decisions
- They are required for audit compliance
- They document autonomous enforcement when Core is offline

**Example Log Messages:**

```
GA-BLOCKING: Core offline — autonomous enforcement active. Action: BLOCK_PROCESS, Cached policy version: 1.0
GA-BLOCKING: Core offline — Action BLOCK_PROCESS is prohibited by cached policy. Agent enforcing autonomous fail-closed policy. Action denied.
GA-BLOCKING: Core offline — No policy available — default deny enforced. Action BLOCK_PROCESS denied (fail-closed).
```

**Auditor Interpretation:**
- These logs prove agents did not fail-open when Core was unreachable
- They document policy enforcement decisions for compliance
- They enable forensic reconstruction of agent behavior during Core outages

### How Agents Enforce Cached Policy

**Policy Cache Structure:**
```json
{
  "version": "1.0",
  "prohibited_actions": ["BLOCK_PROCESS", "QUARANTINE_FILE", "ISOLATE_HOST"],
  "allowed_actions": [],
  "last_updated": "2024-01-15T10:30:00Z",
  "integrity_hash": "sha256_hash"
}
```

**Enforcement Logic:**

1. **If Core is Online:**
   - Normal operation
   - Core verifies all commands
   - Policy cache is updated when Core provides new policy

2. **If Core is Offline:**
   - Agent loads cached policy (or defaults to deny)
   - For each command:
     - If action is prohibited → REJECT (fail-closed)
     - If action not in allow-list → REJECT (fail-closed)
     - If no allow-list exists → REJECT (default deny)
     - If action explicitly allowed → ALLOW (with logging)

**Result:** Agents continue enforcing policy autonomously without Core connectivity.

### Why Default-Deny is Intentional

**Fail-Closed Design:**
- When Core is offline and no policy exists, agent defaults to DENY
- This prevents fail-open behavior (allowing actions when policy is unknown)
- This ensures security guarantees are preserved even during Core outages

**Rationale:**
- **Security:** Unknown policy → Deny all (safer than allow all)
- **Audit compliance:** Explicit deny decisions are logged and auditable
- **Military requirements:** Meets zero-trust enforcement requirements

**Operational Implication:**
- Operators must ensure policy cache is populated when Core is online
- Agents will deny actions when Core is offline and no policy exists
- This is intentional fail-closed behavior, not a bug

---

## 8. Audit & Compliance Notes

### Overview

RansomEye v1.0 GA is designed with fail-closed behavior throughout the system. This section explains why this design exists and how it aligns with military and government expectations.

### Why Fail-Closed Behavior Exists Everywhere

**Design Principle:** System must fail securely, never fail open.

**Examples of Fail-Closed Behavior:**

1. **SBOM Verification:**
   - Invalid signature → Installation fails (no override)
   - Hash mismatch → Installation fails (no override)
   - Missing manifest → Installation fails (no override)

2. **Database Bootstrap:**
   - PEER authentication detected → Startup fails with clear error (no auto-fix)
   - Database unreachable → Startup fails (no retry indefinitely)

3. **OS-Aware Validation:**
   - Wrong OS for track → Validation fails (no best-effort execution)
   - Incompatible track → Validation fails (no warnings-only)

4. **Agent Autonomy:**
   - Core offline + no policy → Actions denied (no fail-open)
   - Policy integrity check fails → Default deny (no best-effort)

5. **Correlation Engine:**
   - Single signal → SUSPICIOUS only (no direct CONFIRMED)
   - Contradiction detected → Confidence decays (no state escalation)

**Rationale:**
- **Security:** Fail-closed prevents security boundary violations
- **Audit compliance:** Explicit failures are logged and auditable
- **Deterministic behavior:** Same conditions → Same failures (reproducible)

### Why There is No "Best Effort" Mode

**Design Principle:** System either succeeds completely or fails explicitly.

**No Best Effort Examples:**

1. **Installation:**
   - No "install with warnings" mode
   - No "continue despite errors" flag
   - No "partial installation" option

2. **Validation:**
   - No "run what you can" mode
   - No "skip incompatible tracks" option
   - No "warnings-only" execution

3. **Agent Enforcement:**
   - No "allow if uncertain" mode
   - No "best-effort policy enforcement"
   - No "graceful degradation"

**Rationale:**
- **Audit requirements:** Partial success is ambiguous and not auditable
- **Security boundaries:** Best effort can lead to security violations
- **Military/government expectations:** Explicit failures are preferred over ambiguous partial success

### How RansomEye Aligns with Military / Gov Expectations

**Air-Gapped Deployments:**
- SBOM verification works offline (no network access required)
- Public key distribution via secure channels
- Cryptographic verification of all artifacts

**Zero-Trust Enforcement:**
- Agents enforce policy autonomously (no trust in Core connectivity)
- Default deny when policy unknown (fail-closed)
- Explicit logging of all enforcement decisions

**Audit Compliance:**
- All failures are explicit and logged
- No silent degradation or best-effort modes
- Deterministic behavior (reproducible results)

**Chain-of-Custody:**
- Reports are deterministic (same incident → same hash)
- Evidence content is separated from presentation
- All report generation events are logged

**Supply Chain Integrity:**
- All artifacts are cryptographically signed
- Installation is fail-closed (no unsigned artifacts)
- Verification is offline-capable

**Operational Visibility:**
- Health metrics endpoint provides system visibility
- No PII or sensitive data exposed
- Clear operational status indicators

### Compliance Notes for Auditors

**For Auditors Reading Logs Months Later:**

1. **Log Prefixes:**
   - `GA-BLOCKING:` indicates critical security enforcement decisions
   - These logs are required for audit compliance
   - They document fail-closed behavior

2. **Failure Patterns:**
   - All failures are explicit (no silent failures)
   - Failures include clear error messages
   - Failures are logged with context

3. **Deterministic Behavior:**
   - Same inputs → Same outputs (reproducible)
   - No random behavior in security-critical paths
   - All decisions are logged

4. **Audit Trail:**
   - All security decisions are logged
   - All state transitions are logged
   - All policy enforcement is logged

**Auditor Questions:**

**Q: Why did installation fail?**  
A: Check logs for SBOM verification failures, database bootstrap errors, or other fail-closed validations. All failures are explicit and logged.

**Q: Why are there no incidents for this time period?**  
A: Check correlation engine logs. Single signals create SUSPICIOUS incidents only. Multiple signals are required for PROBABLE/CONFIRMED stages.

**Q: Why did agent deny this action?**  
A: Check agent logs for "GA-BLOCKING" messages. Agents enforce cached policy when Core is offline. Default deny is intentional fail-closed behavior.

**Q: Why is report hash different?**  
A: Report hashes should be identical for same incident snapshot. If different, check for system time usage (forbidden) or branding in hash domain (should be excluded).

---

## Appendix A: Quick Reference

### Critical Endpoints

- **Health Metrics:** `GET http://localhost:8000/health/metrics`
- **Core Health:** `GET http://localhost:8000/health`

### Critical Files

- **SBOM Manifest:** `manifest.json`
- **SBOM Signature:** `manifest.json.sig`
- **Verification Script:** `verify_sbom.py`
- **Policy Cache:** `/var/lib/ransomeye/agent/cached_policy.json`
- **Audit Logs:** `/var/log/ransomeye/audit.log`

### Critical Environment Variables

- `RANSOMEYE_DB_HOST`: Database host (default: localhost)
- `RANSOMEYE_DB_PORT`: Database port (default: 5432)
- `RANSOMEYE_DB_NAME`: Database name (default: ransomeye)
- `RANSOMEYE_DB_USER`: Database user (default: gagan)
- `RANSOMEYE_DB_PASSWORD`: Database password (required)
- `RANSOMEYE_CONFIDENCE_THRESHOLD_PROBABLE`: Confidence threshold for PROBABLE (default: 30.0)
- `RANSOMEYE_CONFIDENCE_THRESHOLD_CONFIRMED`: Confidence threshold for CONFIRMED (default: 70.0)
- `RANSOMEYE_DEDUP_TIME_WINDOW`: Deduplication time window in seconds (default: 3600)

### Critical Commands

**Verify SBOM:**
```bash
python3 verify_sbom.py --release-root /path/to/release --public-key /path/to/public_key.pem
```

**Check Health:**
```bash
curl http://localhost:8000/health/metrics
```

**Check Database Bootstrap:**
```bash
# Check logs for db_bootstrap_validator errors
journalctl -u ransomeye-core | grep "db_bootstrap"
```

**Check Agent Autonomy:**
```bash
# Check logs for GA-BLOCKING messages
journalctl -u ransomeye-linux-agent | grep "GA-BLOCKING"
```

---

## Document Control

**Version:** 1.0.0  
**Date:** 2024-01-15  
**Status:** Final  
**Classification:** Unclassified  
**Distribution:** Enterprise SOC, SRE, Security Operations, Military Operators, Auditors

**Change History:**
- 1.0.0 (2024-01-15): Initial release for RansomEye v1.0 GA

---

**END OF OPERATIONS MANUAL**
