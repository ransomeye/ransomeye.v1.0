# PHASE D — BACKUP → CLEAN INSTALL → REVALIDATION

**Status**: IN PROGRESS  
**Date**: 2026-01-18  
**Lead Decision**: Proceed with production validation after Phase B success

---

## EXECUTIVE SUMMARY

Phase B validation **PASSED** with no gaps:
- Core stability under hostile conditions (586 files/s encryption burst)
- Integrity-over-availability trade-offs working correctly
- Detection pipeline operational

Phase D validates that the system works **without development artifacts** in a production-like clean install.

---

## PHASE D STRUCTURE

### D.1 — FULL BACKUP
**Script**: `scripts/phase_d_backup.sh`  
**Purpose**: Create authoritative backup of production components only

**What is backed up**:
- `/opt/ransomeye/` (core services)
- `/opt/ransomeye-agent/` (linux agent)
- `/etc/systemd/system/ransomeye*` (systemd units)
- PostgreSQL database (logical dump + schema)
- System state snapshot (services, users, groups)

**What is excluded**:
- CI files
- Documentation
- Test scripts
- Temporary artifacts
- Development tools

**Output**: Compressed tar.gz with manifest and SHA256 checksum

---

### D.2 — CLEAN REMOVAL
**Script**: `scripts/phase_d_uninstall.sh`  
**Purpose**: Complete removal of all RansomEye components

**Actions**:
1. Stop all services
2. Disable systemd units
3. Remove unit files
4. Remove `/opt/ransomeye*` directories
5. Drop PostgreSQL database (with confirmation)
6. Remove system users/groups
7. Verify clean state

**Safety**: Interactive confirmations before destructive operations

---

### D.3 — CLEAN INSTALL
**Script**: `scripts/phase_d_reinstall.sh`  
**Purpose**: Fresh installation from installers only

**Components**:
- Core services (ingest, correlation, policy, ai-core)
- Linux Agent
- **DPI deferred** (by design, will be Phase C)

**Verification**: Checks for existing installation, aborts if found

---

### D.4 — BASIC VALIDATION
**Script**: `scripts/phase_d_validation.sh`  
**Purpose**: Confirm basic functionality without CI/internet

**Checks**:
- ✅ Services reach READY state
- ✅ Watchdogs active and configured
- ✅ Agent → Core telemetry flow
- ✅ Database connectivity
- ✅ No internet dependency

**Success Criteria**: All checks pass, no critical errors

---

### D.5 — MINIMAL PHASE B REPLAY
**Script**: `scripts/phase_d_simulation.sh`  
**Purpose**: Small-scale ransomware simulation

**Test Scenario**:
- 50 test files (~500KB total)
- Encryption burst at controlled rate
- Minimal C2-like traffic
- 30s correlation window

**Expected Outcomes** (matching Phase B):
- Events ingested and stored
- Services remain stable (no restarts)
- Detection pipeline processes data
- Fail-closed behavior maintained

**Success Criteria**: Same behavior as Phase B, smaller scale

---

## EXECUTION SEQUENCE

```bash
# Step 1: Create backup
./scripts/phase_d_backup.sh

# Verify backup created successfully
# Check: /tmp/ransomeye_phase_d_backup_*.tar.gz exists

# Step 2: Clean removal (DESTRUCTIVE)
./scripts/phase_d_uninstall.sh
# Requires: "yes" + "REMOVE" confirmations

# Step 3: Clean install
./scripts/phase_d_reinstall.sh

# Step 4: Basic validation
./scripts/phase_d_validation.sh

# Step 5: Minimal Phase B replay
./scripts/phase_d_simulation.sh
```

---

## SUCCESS CRITERIA (PHASE D COMPLETE)

Phase D passes if:

1. ✅ Backup created with manifest and checksum
2. ✅ Clean removal verified (no artifacts remain)
3. ✅ Clean install succeeds from installers
4. ✅ All services reach READY state
5. ✅ Agent telemetry flows to core
6. ✅ Minimal simulation shows same Phase B behavior:
   - Events detected and stored
   - Services stable (no restarts)
   - Fail-closed guarantees maintained
7. ✅ No dependency on CI/GitHub/internet

---

## WHAT PHASE D PROVES

If Phase D succeeds, we have demonstrated:

### Production Readiness Indicators
- System can be installed cleanly on any target
- No hidden dependencies on development environment
- Installers are complete and functional
- Services are self-contained and stable

### Operational Validation
- Detection pipeline works in isolation
- Telemetry flow is reliable
- Fail-closed behavior is inherent
- Watchdogs and monitoring operational

### Chain of Evidence
- Phase B validated capabilities under stress
- Phase D validates clean deployment
- Combined: proves system is **production-ready for limited deployment**

---

## AFTER PHASE D

Only after Phase D passes:

### Immediate Next Steps
1. Document Phase D results
2. Archive backup safely
3. **DECISION POINT**: Keep clean install or restore backup

### Deferred Work (Post-Phase D)
- DPI full integration (Phase C)
- Detection tuning and rule refinement
- Alerting layer implementation
- Multi-machine rollout planning
- Production monitoring configuration

---

## ROLLBACK PLAN

If Phase D fails at any step:

### Before D.3 (Reinstall)
- Restore from backup: `tar -xzf /tmp/ransomeye_phase_d_backup_*.tar.gz -C /`
- Restore database: `sudo -u postgres psql ransomeye < backup/database/*.sql`
- Reload systemd: `sudo systemctl daemon-reload`
- Start services: `sudo systemctl start ransomeye.target`

### After D.3 (Reinstall)
- Investigate failure cause
- Fix installer or configuration issue
- Re-run from D.2 (clean removal)

**DO NOT** proceed to production if Phase D fails. Fix root cause first.

---

## VALIDATION ARTIFACTS

All Phase D scripts generate logs and artifacts:

- **Backup manifest**: `/tmp/ransomeye_phase_d_backup_*/BACKUP_MANIFEST.txt`
- **System state**: `/tmp/ransomeye_phase_d_backup_*/system_state/`
- **Service logs**: `journalctl -u ransomeye-*`
- **Simulation results**: Database event/alert counts

Archive these for compliance and audit purposes.

---

## PHASE D TIMELINE

Expected execution time (manual):
- D.1 Backup: ~5 minutes
- D.2 Uninstall: ~2 minutes
- D.3 Reinstall: ~10 minutes (depending on installers)
- D.4 Validation: ~5 minutes
- D.5 Simulation: ~2 minutes (30s correlation window)

**Total**: ~25-30 minutes for complete Phase D cycle

---

## CONTACT & DECISIONS

**Lead Authority**: System Owner  
**No Feature Additions**: Phase D is validation only  
**Scope Lock**: No tuning, no DPI expansion, no alerting yet  

Phase D completes the validation cycle. After this, we have a **production-grade baseline** ready for limited deployment.

---

**END OF PHASE D EXECUTION GUIDE**
