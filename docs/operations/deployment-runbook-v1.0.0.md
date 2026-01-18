# RansomEye — Deployment Runbook

**Production Deployment Procedure**
**Version:** v1.0.0
**Status:** OPERATIONAL · AUDITABLE

---

## 1. PRECONDITIONS (MANDATORY)

* Signed release bundle present:
  ```
  ransomeye-v1.0.0/
  ```

* Files present:
  * `manifest.json`
  * `manifest.json.sig`
  * `SHA256SUMS`
  * `SHA256SUMS.sig`

* Public Release Signing Key available

* Target host:
  * systemd-based Linux
  * ≥8GB RAM recommended
  * ≥50GB free disk
  * No conflicting services on required ports

❌ If any precondition fails → **STOP**

---

## 2. VERIFICATION (REQUIRED, OFFLINE OK)

```bash
ed25519-verify manifest.json.sig manifest.json release.pub
ed25519-verify SHA256SUMS.sig SHA256SUMS release.pub
sha256sum -c SHA256SUMS
```

❌ Any failure → **DO NOT INSTALL**

---

## 3. INSTALLATION

```bash
cd ransomeye-v1.0.0
sudo ./installer/install.sh
```

Installer guarantees:

* Transactional install
* Rollback on failure
* Idempotency

---

## 4. POST-INSTALL VALIDATION

```bash
systemctl status ransomeye.target
```

Expected:

* `secure-bus.service` → ACTIVE
* `ingest.service` → ACTIVE + READY
* `core-runtime.service` → ACTIVE + WATCHDOG
* `correlation-engine.service` → ACTIVE + WATCHDOG
* `NRestarts=0`

❌ Any deviation → escalate to Incident Runbook

---

## 5. HEALTH CHECKS

### Watchdog Validation

```bash
systemctl show core-runtime.service | grep WatchdogTimestamp
systemctl show correlation-engine.service | grep WatchdogTimestamp
```

Expected: WatchdogTimestamp updates every 10–20s

### Log Inspection

```bash
journalctl -u secure-bus.service -n 50
journalctl -u ingest.service -n 50
journalctl -u core-runtime.service -n 50
journalctl -u correlation-engine.service -n 50
```

Normal: INFO / WARNING messages
Abnormal: CONFIG_ERROR, watchdog timeout, EPERM/seccomp denials

---

## 6. CONFIGURATION VALIDATION

* Secrets via env only (`/opt/ransomeye/config/environment`, **600 perms**)
* No default passwords
* Network binds default to `127.0.0.1`
* systemd hardening in place

---

## 7. ROLLBACK

If deployment fails:

```bash
sudo ./installer/uninstall.sh
```

Then deploy previous signed release.

---

## STATUS

* **Runbook:** OPERATIONAL
* **Version:** v1.0.0
* **Last Updated:** 2026-01-18
