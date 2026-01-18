# PHASE D — QUICK REFERENCE CARD

---

## ONE-LINE SUMMARY
**Backup → Remove → Reinstall → Validate → Simulate**

---

## EXECUTION ORDER

```bash
# 1. BACKUP (5 min)
./scripts/phase_d_backup.sh

# 2. UNINSTALL (2 min) — REQUIRES CONFIRMATION
./scripts/phase_d_uninstall.sh

# 3. REINSTALL (10 min)
./scripts/phase_d_reinstall.sh

# 4. VALIDATE (5 min)
./scripts/phase_d_validation.sh

# 5. SIMULATE (2 min)
./scripts/phase_d_simulation.sh
```

---

## WHAT EACH SCRIPT DOES

| Script | Purpose | Safety | Output |
|--------|---------|--------|--------|
| `phase_d_backup.sh` | Backup prod components | ✅ Safe | `.tar.gz` in `/tmp/` |
| `phase_d_uninstall.sh` | Remove all traces | ⚠️ DESTRUCTIVE | Clean system |
| `phase_d_reinstall.sh` | Fresh install | ✅ Safe | Services running |
| `phase_d_validation.sh` | Basic health checks | ✅ Safe | PASS/FAIL report |
| `phase_d_simulation.sh` | Mini Phase B test | ✅ Safe | Detection proof |

---

## CRITICAL SAFETY RULES

1. **ALWAYS run backup first** — No exceptions
2. **Verify backup created** — Check `/tmp/` for `.tar.gz`
3. **Uninstall requires 2 confirmations** — "yes" + "REMOVE"
4. **Stop if validation fails** — Don't proceed to simulation
5. **Archive backup offsite** — Before uninstall

---

## SUCCESS = GREEN LIGHTS

Phase D passes when:
- ✅ Backup has manifest + SHA256
- ✅ Uninstall leaves clean system
- ✅ Reinstall completes without errors
- ✅ All services reach READY
- ✅ Agent telemetry flows
- ✅ Simulation matches Phase B behavior

---

## FAILURE = RED LIGHTS

Stop and investigate if:
- ❌ Backup missing components
- ❌ Uninstall leaves artifacts
- ❌ Reinstall fails
- ❌ Services don't start
- ❌ No telemetry flow
- ❌ Simulation crashes services

---

## ROLLBACK (IF NEEDED)

```bash
# Extract backup
cd /tmp
tar -xzf ransomeye_phase_d_backup_*.tar.gz

# Restore files
sudo cp -a ransomeye_phase_d_backup_*/opt/* /opt/
sudo cp -a ransomeye_phase_d_backup_*/etc/systemd/system/* /etc/systemd/system/

# Restore database
sudo -u postgres psql -c "CREATE DATABASE ransomeye;"
sudo -u postgres psql ransomeye < ransomeye_phase_d_backup_*/database/*.sql

# Reload and start
sudo systemctl daemon-reload
sudo systemctl start ransomeye.target
```

---

## LOGS TO CHECK

```bash
# Service logs (last 100 lines each)
journalctl -u ransomeye-ingest -n 100
journalctl -u ransomeye-correlation -n 100
journalctl -u ransomeye-policy -n 100
journalctl -u ransomeye-ai-core -n 100
journalctl -u ransomeye-linux-agent -n 100

# Database event count
sudo -u postgres psql ransomeye -c "SELECT COUNT(*) FROM events;"

# Service status
systemctl status 'ransomeye*'
```

---

## EXPECTED TIMELINE

| Phase | Time | Critical? |
|-------|------|-----------|
| D.1 Backup | 5 min | ✅ Must succeed |
| D.2 Uninstall | 2 min | ⚠️ Destructive |
| D.3 Reinstall | 10 min | ✅ Must succeed |
| D.4 Validation | 5 min | ✅ Must pass |
| D.5 Simulation | 2 min | ✅ Must pass |
| **TOTAL** | **~25 min** | Manual execution |

---

## DECISION POINTS

### Before Uninstall
- "Have you verified the backup?" → Check `/tmp/*.tar.gz`
- "Are you sure?" → Type "REMOVE"

### After Validation Failure
- **STOP** — Don't proceed to simulation
- Check logs, fix issues, re-run from D.2

### After Simulation Failure
- **STOP** — Don't declare Phase D complete
- Investigate detection pipeline, fix, retry

---

## WHAT SUCCESS PROVES

**Phase D PASS = Production Ready**

You have demonstrated:
- ✅ Clean installation from installers (no dev dependencies)
- ✅ Services self-contained and stable
- ✅ Detection pipeline works in isolation
- ✅ Fail-closed guarantees maintained
- ✅ Agent telemetry reliable

**This is the validation milestone.**

---

## AFTER PHASE D

### If PASS:
1. Archive Phase D results
2. Document findings
3. **DECISION**: Keep clean install OR restore backup
4. Begin Phase C (DPI) or production planning

### If FAIL:
1. **DO NOT** proceed to production
2. Fix root cause
3. Re-run from D.2
4. Document what was fixed

---

## CONTACT

**Phase Owner**: System Lead  
**Scope**: Validation only (no features)  
**Duration**: Single execution cycle  

---

**Keep this card visible during Phase D execution.**
