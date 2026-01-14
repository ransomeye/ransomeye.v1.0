# Phase-9 Step 3: Credential & Secret Inventory

**Inventory Date:** 2024-01-15  
**Status:** Complete Audit

---

## Hardcoded Credential Inventory

### Critical Findings

| File | Line | Variable | Type | Severity | Status |
|------|------|----------|------|----------|--------|
| `.github/workflows/ci-validation-reusable.yml` | 49 | `RANSOMEYE_DB_PASSWORD` | Test DB | **CRITICAL** | Hardcoded: `'test_password_change_in_production'` |
| `.github/workflows/ci-validation-reusable.yml` | 47 | `RANSOMEYE_DB_NAME` | Test DB | **HIGH** | Hardcoded: `'ransomeye_test'` |
| `.github/workflows/ci-validation-reusable.yml` | 48 | `RANSOMEYE_DB_USER` | Test DB | **HIGH** | Hardcoded: `'ransomeye_test'` |
| `signed-reporting/api/reporting_api.py` | 316 | `RANSOMEYE_DB_USER` | DB | **CRITICAL** | Default: `'gagan'` |
| `signed-reporting/api/reporting_api.py` | 317 | `RANSOMEYE_DB_PASSWORD` | DB | **CRITICAL** | Default: `'gagan'` |
| `validation/harness/test_helpers.py` | 26 | `RANSOMEYE_DB_USER` | Test DB | **HIGH** | Default: `'gagan'` |
| `validation/harness/test_helpers.py` | 27 | `RANSOMEYE_DB_PASSWORD` | Test DB | **HIGH** | Default: `'gagan'` |
| `services/correlation-engine/app/db.py` | 71 | `RANSOMEYE_DB_PASSWORD` | DB | **MEDIUM** | Default: `''` (empty string) |
| `services/policy-engine/app/db.py` | 68 | `RANSOMEYE_DB_PASSWORD` | DB | **MEDIUM** | Default: `''` (empty string) |
| `services/ai-core/app/db.py` | 65 | `RANSOMEYE_DB_PASSWORD` | DB | **MEDIUM** | Default: `''` (empty string) |
| `services/ai-core/app/db.py` | 77 | `RANSOMEYE_DB_PASSWORD` | DB | **MEDIUM** | Default: `''` (empty string) |

### Documentation References (Not Code)

The following files contain references to credentials in documentation/comments but do NOT contain hardcoded values in executable code:

- `installer/core/README.md` - Documentation only (prerequisites section)
- `installer/linux-agent/README.md` - Documentation only
- `installer/dpi-probe/README.md` - Documentation only
- `installer/windows-agent/README.md` - Documentation only
- `release/ransomeye-v1.0/core/install.sh` - Old release bundle (not active code)
- `release/ransomeye-v1.0/linux-agent/install.sh` - Old release bundle (not active code)
- `release/ransomeye-v1.0/dpi-probe/install.sh` - Old release bundle (not active code)
- `validation/**/*.md` - Validation reports documenting issues (not executable code)

**Note:** These documentation references will be updated to remove credential examples, but they are not executable code vulnerabilities.

---

## Exposure Severity Classification

### CRITICAL
- Credentials in CI workflows (exposed in repository)
- Default credentials in production code paths
- Credentials with weak values (`'gagan'`, `'test_password_change_in_production'`)

### HIGH
- Test credentials in validation code
- Database names/users in CI (less sensitive but still exposure)

### MEDIUM
- Empty string defaults (fail-fast behavior, but should be explicit)

---

## Remediation Priority

1. **Priority 1 (Immediate):**
   - CI workflow credentials (`.github/workflows/ci-validation-reusable.yml`)
   - Production code defaults (`signed-reporting/api/reporting_api.py`)

2. **Priority 2 (High):**
   - Test helper defaults (`validation/harness/test_helpers.py`)

3. **Priority 3 (Medium):**
   - Empty string defaults (make explicit fail-fast)

---

## Git History Exposure

**Files with credential exposure in git history:**
- All files listed above have been committed with credentials
- Historical commits may contain additional exposed credentials
- Full git history scan required (see Git History Audit section)

---

**End of Inventory**
