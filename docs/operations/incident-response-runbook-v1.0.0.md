# RansomEye — Incident Response Runbook

**Operational Incident Handling**
**Version:** v1.0.0
**Status:** OPERATIONAL

---

## 1. SERVICE CRASH / RESTART STORM

### Symptoms

* `NRestarts > 0`
* `Result=watchdog`
* StartLimit hit

### Actions

1. **DO NOT restart blindly**

2. Inspect logs:
   ```bash
   journalctl -xeu <service>
   ```

3. Identify:
   * Missing env vars
   * Disk full
   * Dependency failure

4. Fix root cause

5. Restart target:
   ```bash
   systemctl restart ransomeye.target
   ```

---

## 2. CONFIGURATION / SECRET FAILURE

### Symptoms

* Immediate exit
* `CONFIG_ERROR`

### Actions

1. Verify:
   ```bash
   ls -l /opt/ransomeye/config/
   ```

2. Check permissions (must be 600/700)

3. Set missing env vars

4. Restart target

Fail-fast is **expected behavior**.

---

## 3. DISK FULL / BACKPRESSURE

### Symptoms

* Fatal ENOSPC errors
* Immediate service exit

### Actions

1. Free disk space

2. Verify:
   ```bash
   df -h
   ```

3. Restart target

❌ Do NOT disable disk checks

---

## 4. SUSPECTED ARTIFACT TAMPERING

### Symptoms

* Signature verification failure
* Manifest mismatch

### Actions

1. **STOP**
2. Quarantine host
3. Re-verify artifacts offline
4. Escalate to Security Officer
5. Follow signing compromise SOP if needed

---

## 5. WATCHDOG TIMEOUT

### Symptoms

* `Result=watchdog` in service status
* Automatic restart by systemd

### Actions

1. Check logs for:
   * Blocking operations
   * Resource starvation
   * Deadlocks

2. Verify host resources:
   ```bash
   top
   iostat
   df -h
   ```

3. If persistent, escalate

---

## 6. CLEAN UNINSTALL

```bash
sudo ./installer/uninstall.sh
```

Guarantees:

* Services stopped
* Units removed
* No orphaned processes

---

## 7. ROLLBACK TO PREVIOUS RELEASE

1. Obtain **previous signed bundle**
2. Verify signatures
3. Install previous version
4. Run DB downgrade if required:
   ```bash
   ransomeye-migrate downgrade --target-version X.Y.Z
   ```

---

## STATUS

* **Runbook:** OPERATIONAL
* **Version:** v1.0.0
* **Last Updated:** 2026-01-18
