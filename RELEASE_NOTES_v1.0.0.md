# RansomEye v1.0.0 — Release Notes

**Release Date:** 2026-01-18  
**Status:** General Availability (GA)  
**Ship Decision:** APPROVED  
**Version:** 1.0.0

---

## 1. Executive Summary (Customer-Facing)

RansomEye v1.0.0 is the **first production-grade release** of the RansomEye platform, delivering a **hardened, fail-closed, systemd-native ransomware detection and response core** designed for enterprise and security-critical environments.

This release establishes a **stable, auditable baseline** with:

* Deterministic orchestration
* Strict dependency handling
* Watchdog-verified daemon lifecycles
* Secure-by-default configuration
* Proven long-run stability

RansomEye v1.0.0 is **approved for production deployment** and intended to serve as the foundation for all future feature development.

---

## 2. What Shipped in v1.0.0

### 2.1 Core Platform Components

RansomEye v1.0.0 includes four core system services, all implemented as **systemd Type=notify daemons**:

| Service            | Role                                             |
| ------------------ | ------------------------------------------------ |
| secure-bus         | Secure inter-service communication backbone      |
| ingest             | Data ingestion and normalization                 |
| core-runtime       | Orchestration, health aggregation, supervision   |
| correlation-engine | Event correlation and ransomware detection logic |

All services:

* Run as long-lived daemons (never exit on idle)
* Emit READY notifications correctly
* Maintain continuous WATCHDOG compliance
* Fail fast on configuration or runtime errors

---

### 2.2 Orchestration & Dependency Model

* systemd-native orchestration using a dedicated `ransomeye.target`
* Explicit dependency graph with **no circular dependencies**
* Fail-closed behavior on dependency failure
* Deterministic startup and shutdown ordering
* Orchestrator operates in **supervision-only mode** under systemd

Validated failure modes include:

* Missing dependencies
* Crash loops
* Restart storms
* Orchestrator restarts mid-flight
* Split-brain readiness
* Ordered shutdown and teardown

---

### 2.3 Security Posture (Secure by Default)

#### Secrets & Credentials

* Secrets injected **env-only**
* No hardcoded credentials
* No default passwords
* Mandatory fail-fast validation for all required secrets
* File permissions strictly enforced:
  * Secrets: `600`
  * Key directories: `700`

#### Network Exposure

* All services bind to `127.0.0.1` by default
* No implicit wildcard (`0.0.0.0`) binds
* Explicit opt-in required for broader exposure
* No debug or admin endpoints exposed by default

#### System Hardening

Applied uniformly across all services:

* `NoNewPrivileges=true`
* Zero Linux capabilities (`CapabilityBoundingSet=`)
* Kernel protections enabled
* Namespace and realtime restrictions
* Seccomp syscall filtering (`@system-service` allowlist)
* Resource isolation via cgroups

---

### 2.4 Operational Resilience

* Memory isolation: `MemoryMax=4G`
* CPU throttling: `CPUQuota=75%`
* Process limits: `TasksMax=2048`
* ulimits enforced (`NOFILE=65536`, `NPROC=4096`)
* Disk backpressure handled fail-fast (ENOSPC, EROFS, EDQUOT)
* Logging via systemd journald with bounded growth

---

### 2.5 Stability & Validation

RansomEye v1.0.0 passed:

* All orchestration failure modes (FM-1 → FM-10)
* Multiple watchdog compliance validations
* Lifecycle correctness audits
* 30+ minute full-platform soak with **zero restarts**
* Post-hardening restart and stability verification

---

## 3. Installation & Lifecycle

### 3.1 Installation

* Transactional installer with rollback support
* Idempotent installs
* Manifest-driven verification
* Cryptographically signed checksums

### 3.2 Uninstallation

* Clean service shutdown
* Unit and binary removal
* Manifest verification before uninstall
* No orphaned processes

### 3.3 Database Migrations

* Versioned migrations with checksums
* Up/down migration pairs
* Advisory locking
* Fail-safe validation on startup

---

## 4. Known Limitations (v1.0.0)

The following are **intentional and documented** for the v1.0.0 baseline:

* No in-place upgrade documentation included (planned for v1.1)
* Test teardown logging produces non-fatal noise
* No external API exposure by default
* No UI enabled by default (security-first posture)

None of the above impact production correctness or security.

---

## 5. Upgrade Guidance

* v1.0.0 → v1.x upgrades are supported by the migration framework
* Operational upgrade documentation will be delivered in v1.1
* Downgrade paths are implemented and validated at the DB layer

---

## 6. Compliance & Audit Statement

RansomEye v1.0.0 provides:

* Deterministic runtime behavior
* Auditable configuration and manifests
* Reproducible builds
* Signed release artifacts
* Clear failure semantics

This release is suitable for **regulated, security-sensitive environments**.

---

## 7. Technical Appendix (Engineering Reference)

### 7.1 Daemon Guarantees

* Never exit on idle
* Exit only on SIGTERM/SIGINT or fatal error
* Watchdog thread bound to process lifetime

### 7.2 Readiness Semantics

* READY only asserted when fully initialized
* Global readiness is fail-closed
* Partial readiness never reported as healthy

### 7.3 Failure Handling

* systemd owns restarts
* Orchestrator never force-starts or force-stops services
* Restart storms bounded by StartLimit policies

### 7.4 Hardening Summary

* Capabilities: none
* Seccomp: enforced
* Kernel access: denied
* Network families: restricted
* Filesystem: read-only except explicit paths

---

## 8. Ship Declaration

**RansomEye v1.0.0 is production-ready and officially released.**

All future changes require a **version increment** and must not alter v1.0.0 semantics.

---

## Related Documentation

* [Ship Decision](RANSOMEYE_V1_FINAL_SHIP_DECISION.md)
* [Master Readiness Validation](MASTER_READINESS_VALIDATION.md)
* [Operations Manual](OPERATIONS_MANUAL.md)
* [Architecture](ARCHITECTURE.md)
* [Phase 10 Core Runtime Audit](PHASE_10_CORE_RUNTIME_AUDIT_REPORT.md)

---

**End of Release Notes v1.0.0**
