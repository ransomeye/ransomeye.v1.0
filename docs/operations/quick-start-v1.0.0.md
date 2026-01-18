# RansomEye v1.0 — Operator Quick-Start (1-Page)

**Audience:** On-call operators, SOC engineers
**Scope:** Day-0 deploy · Day-1 checks · Day-2 incidents
**Assumption:** Signed v1.0.0 release bundle

---

## 1) Verify & Install (Offline OK)

```bash
cd ransomeye-v1.0.0
ed25519-verify manifest.json.sig manifest.json release.pub
ed25519-verify SHA256SUMS.sig SHA256SUMS release.pub
sha256sum -c SHA256SUMS
sudo ./installer/install.sh
```

**If any verify step fails → STOP.**

---

## 2) Start & Check Health

```bash
systemctl status ransomeye.target
```

**Expected (all ACTIVE, NRestarts=0):**

* `secure-bus.service`
* `ingest.service` (READY)
* `core-runtime.service` (WATCHDOG updating)
* `correlation-engine.service` (WATCHDOG updating)

Quick checks:

```bash
systemctl show core-runtime.service | grep WatchdogTimestamp
systemctl show correlation-engine.service | grep WatchdogTimestamp
```

---

## 3) Where to Look (Logs)

```bash
journalctl -u secure-bus.service
journalctl -u ingest.service
journalctl -u core-runtime.service
journalctl -u correlation-engine.service
```

**Normal:** INFO/WARNING
**Investigate immediately:** `CONFIG_ERROR`, `Result=watchdog`, `EPERM/seccomp`

---

## 4) Configuration Rules (Do Not Break)

* Secrets via env only (`/opt/ransomeye/config/environment`, **600 perms**)
* No default passwords (missing secret = fail-fast)
* Network binds default to `127.0.0.1`
* Do **not** relax systemd hardening

---

## 5) Common Incidents & Actions

**Service won't start / CONFIG_ERROR**

1. Check missing env vars / permissions
2. Fix root cause
3. `systemctl restart ransomeye.target`

**Watchdog timeout / restarts**

1. Inspect logs for disk full, dependency failure
2. Fix cause (free disk, restore dependency)
3. Restart target

**Disk full**

* Free space → restart target
* Do not disable disk checks

**Suspected tampering**

* Stop
* Re-verify signatures offline
* Escalate to Security Officer

---

## 6) Stop / Uninstall / Rollback

```bash
sudo ./installer/uninstall.sh
```

**Rollback:** Install previous **signed** bundle; run DB downgrade only if documented.

---

## 7) Absolute Rules

* No unsigned artifacts
* No hotfixes in prod
* systemd is source of truth
* Fail-fast is correct behavior

---

**Status:** Quick-Start COMPLETE · v1.0.0 OPS READY
