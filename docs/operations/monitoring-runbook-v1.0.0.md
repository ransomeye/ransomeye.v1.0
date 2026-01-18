# RansomEye — Monitoring Runbook

**Health Monitoring & Observability**
**Version:** v1.0.0
**Status:** OPERATIONAL

---

## 1. PRIMARY HEALTH SIGNALS

### Systemd (Authoritative)

```bash
systemctl is-active ransomeye.target
systemctl show <service> | grep WatchdogTimestamp
```

### Expected

* WatchdogTimestamp updates every 10–20s
* No StartLimit hits
* No SIGKILL except on stop/uninstall

---

## 2. SERVICE-LEVEL CHECKS

### secure-bus.service

```bash
systemctl status secure-bus.service
```

Expected: ACTIVE, NRestarts=0

### ingest.service

```bash
systemctl status ingest.service
journalctl -u ingest.service | grep READY
```

Expected: ACTIVE + READY marker in logs

### core-runtime.service

```bash
systemctl status core-runtime.service
systemctl show core-runtime.service | grep WatchdogTimestamp
```

Expected: ACTIVE + WATCHDOG updating

### correlation-engine.service

```bash
systemctl status correlation-engine.service
systemctl show correlation-engine.service | grep WatchdogTimestamp
```

Expected: ACTIVE + WATCHDOG updating

---

## 3. LOGS

```bash
journalctl -u secure-bus.service
journalctl -u ingest.service
journalctl -u core-runtime.service
journalctl -u correlation-engine.service
```

Normal:

* INFO / WARNING (expected dependency warnings)

Abnormal:

* WATCHDOG timeout
* EPERM / seccomp denial
* CONFIG_ERROR

---

## 4. RESOURCE MONITORING

* Memory enforced at 4G per service
* CPU capped at 75%
* TasksMax enforced at 2048

```bash
systemctl status <service>
```

OOM or throttling events → Incident Runbook

---

## 5. ALERT THRESHOLDS

| Metric          | Warning | Critical |
| --------------- | ------- | -------- |
| Service Restart | 1       | 3        |
| Watchdog Miss   | 1       | 2        |
| Memory (% max)  | 80%     | 95%      |
| Disk Usage      | 80%     | 90%      |

---

## STATUS

* **Runbook:** OPERATIONAL
* **Version:** v1.0.0
* **Last Updated:** 2026-01-18
