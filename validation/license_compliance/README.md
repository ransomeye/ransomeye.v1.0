# RansomEye License Compliance Bundle

**Status:** Production-Grade, CI-Enforced, Auditor-Ready  
**Purpose:** Complete third-party dependency and license validation infrastructure for RansomEye

---

## Overview

This directory contains the complete license compliance infrastructure for RansomEye. This is **not documentation** - this is **legally binding, machine-verifiable, CI-enforceable infrastructure** that ensures RansomEye maintains commercial license compliance.

### Why License Compliance is Critical for RansomEye

RansomEye is an enterprise and military-grade platform with commercial licensing requirements. License compliance is critical because:

1. **Commercial Licensing Protection:** RansomEye must avoid GPL/AGPL dependencies that would require source code disclosure and force RansomEye to be licensed under copyleft terms.

2. **Customer Assurance:** Enterprise customers require license compliance documentation for their own audits and regulatory compliance.

3. **Legal Risk Mitigation:** Unauthorized use of copyleft-licensed code creates legal liability and can invalidate commercial licensing.

4. **Distribution Compliance:** RansomEye distributes software to customers. All distributed dependencies must have compatible licenses.

5. **Audit Readiness:** RansomEye must be able to demonstrate license compliance to auditors, customers, and legal counsel at any time.

**This compliance bundle ensures RansomEye never accidentally introduces forbidden licenses and maintains complete inventory of all third-party dependencies.**

---

## Directory Contents

```
license_compliance/
├── THIRD_PARTY_INVENTORY.json    # Machine-readable inventory (authoritative)
├── THIRD_PARTY_INVENTORY.csv     # CSV export of inventory
├── THIRD_PARTY_LICENSES.md       # Human-readable legal document
├── LICENSE_POLICY.json            # Enforcement policy (authoritative)
├── license_scan.py                # Dependency scanner tool
├── validate_licenses.py           # Strict validator
├── ci_license_gate.sh             # CI/CD gate script
└── README.md                      # This file
```

---

## Files

### THIRD_PARTY_INVENTORY.json

**Purpose:** Machine-readable inventory of all third-party dependencies.

**Format:** JSON array of dependency objects with fields:
- `name`: Package name
- `version`: Version constraint
- `component`: RansomEye component using this dependency
- `language`: python | rust | javascript
- `license`: License identifier (e.g., "MIT", "Apache-2.0")
- `license_type`: permissive | weak-copyleft | strong-copyleft | proprietary
- `static_or_dynamic`: static | dynamic
- `distribution_scope`: core | agent | dpi | optional | customer_supplied
- `risk_level`: low | medium | high
- `notes`: Additional context

**Usage:**
- Referenced by validation tools
- Exported to customers for audit
- Used by legal for compliance review

### THIRD_PARTY_INVENTORY.csv

**Purpose:** CSV export of inventory for spreadsheet analysis.

**Format:** Same fields as JSON, comma-separated.

**Usage:**
- Import into Excel/Google Sheets for analysis
- Customer audit submissions
- Legal review spreadsheets

### THIRD_PARTY_LICENSES.md

**Purpose:** Human-readable legal document suitable for legal review.

**Contents:**
- License summary table
- Explicitly allowed licenses
- Explicitly forbidden licenses
- Conditionally allowed licenses and handling rules
- Special rules (LLM models, Grafana/AGPL, kernel/syscalls)
- Component-level inventory
- Risk assessment
- Compliance verification process

**Usage:**
- Legal review
- Customer license documentation
- Regulatory compliance submissions
- Auditor reference

### LICENSE_POLICY.json

**Purpose:** Authoritative enforcement policy for automated validation.

**Structure:**
- `allowed_licenses`: List of explicitly allowed license identifiers
- `conditionally_allowed`: List of conditionally allowed licenses with conditions
- `forbidden_licenses`: List of explicitly forbidden license identifiers
- `special_rules`: Rules for LGPL, AGPL, GPL, LLM models, kernel syscalls, etc.
- `distribution_scopes`: Definitions of distribution scope categories
- `validation_rules`: Rules for inventory completeness, forbidden detection, etc.
- `audit_requirements`: Frequency and scope of audits

**Usage:**
- Referenced by `license_scan.py` and `validate_licenses.py`
- Authoritative source for CI/CD validation
- Legal policy reference

### license_scan.py

**Purpose:** Scans Python, Rust, and Node.js dependencies and validates against LICENSE_POLICY.json.

**Features:**
- Scans `requirements.txt` files (Python)
- Scans `Cargo.toml` files (Rust)
- Scans `package.json` files (Node.js)
- Maps dependencies to inventory
- Validates licenses against policy
- Emits JSON report
- **OFFLINE ONLY** - No network access required

**Usage:**
```bash
python3 license_scan.py > scan_report.json
```

**Exit Codes:**
- `0`: All dependencies validated, no violations
- `1`: License violations detected

### validate_licenses.py

**Purpose:** Strict validator that ensures inventory completeness and policy compliance.

**Validations:**
- Verifies all dependencies are in inventory (completeness)
- Ensures no forbidden licenses exist
- Validates all inventory entries have required fields
- Validates license_type values are valid
- Validates conditionally allowed licenses are properly documented

**Usage:**
```bash
python3 validate_licenses.py
```

**Exit Codes:**
- `0`: All validations passed
- `1`: Validation errors detected

### ci_license_gate.sh

**Purpose:** Fail-fast CI gate that blocks builds on license violations.

**Features:**
- Runs `license_scan.py`
- Runs `validate_licenses.py`
- Checks for forbidden licenses in inventory
- Prints exact offending dependency + license
- Exits non-zero on any violation

**Usage in CI/CD:**
```bash
# In CI pipeline (e.g., .github/workflows/ci.yml, GitLab CI, Jenkins, etc.)
./validation/license_compliance/ci_license_gate.sh
```

**Exit Codes:**
- `0`: All checks passed, build may proceed
- `1`: License violation detected, build blocked
- `2`: Script error (missing files, etc.)

---

## How Auditors Should Use This Folder

### For External Auditors

1. **Review THIRD_PARTY_LICENSES.md** for complete license policy and inventory summary
2. **Examine THIRD_PARTY_INVENTORY.json** or **THIRD_PARTY_INVENTORY.csv** for complete dependency list
3. **Verify LICENSE_POLICY.json** defines appropriate allowed/forbidden licenses
4. **Run validate_licenses.py** independently to verify inventory completeness:
   ```bash
   cd /path/to/rebuild/validation/license_compliance
   python3 validate_licenses.py
   ```
5. **Review CI/CD integration** to verify automated enforcement (check CI configuration files)

### For Internal Auditors

1. **Run full validation:**
   ```bash
   ./ci_license_gate.sh
   ```
2. **Generate scan report:**
   ```bash
   python3 license_scan.py > scan_report.json
   ```
3. **Verify no forbidden licenses:**
   ```bash
   python3 validate_licenses.py
   ```
4. **Review inventory for new dependencies** (quarterly audit requirement)

---

## How CI Enforces License Safety

### Automated Enforcement

1. **Pre-commit (optional):** Developers can run `ci_license_gate.sh` before committing
2. **CI Pipeline:** `ci_license_gate.sh` runs automatically on every commit
3. **Build Blocking:** Any license violation causes immediate build failure
4. **Clear Error Messages:** CI output shows exact offending dependency and license

### CI Integration Examples

#### GitHub Actions
```yaml
- name: License Compliance Check
  run: |
    cd validation/license_compliance
    ./ci_license_gate.sh
```

#### GitLab CI
```yaml
license_check:
  script:
    - cd validation/license_compliance
    - ./ci_license_gate.sh
```

#### Jenkins
```groovy
stage('License Compliance') {
    steps {
        sh './validation/license_compliance/ci_license_gate.sh'
    }
}
```

### What Gets Blocked

- **Forbidden licenses (GPL, AGPL):** Immediate failure
- **Missing dependencies:** Dependencies not in inventory cause validation failure
- **Invalid license types:** Invalid `license_type` values cause validation failure
- **Conditionally allowed violations:** Conditionally allowed licenses not properly documented cause failure

---

## How Customers Can Verify Compliance Independently

### Customer Verification Process

1. **Request Inventory:** Customer requests `THIRD_PARTY_INVENTORY.json` or `THIRD_PARTY_INVENTORY.csv`
2. **Review Policy:** Customer reviews `LICENSE_POLICY.json` and `THIRD_PARTY_LICENSES.md`
3. **Run Validation:** Customer runs validation tools independently:
   ```bash
   cd /path/to/ransomeye/validation/license_compliance
   python3 validate_licenses.py
   python3 license_scan.py > customer_scan_report.json
   ```
4. **Verify CI Integration:** Customer reviews CI configuration to verify automated enforcement

### Customer Audit Support

RansomEye provides:
- Complete inventory in machine-readable format (JSON, CSV)
- Human-readable legal documentation (THIRD_PARTY_LICENSES.md)
- Validation tools for independent verification
- CI/CD evidence of automated enforcement

---

## Adding New Dependencies

### Process

1. **Check Policy:** Verify license is in `LICENSE_POLICY.json` `allowed_licenses` or `conditionally_allowed`
2. **Add to Inventory:** Add entry to `THIRD_PARTY_INVENTORY.json` with all required fields
3. **Update CSV:** Regenerate or manually update `THIRD_PARTY_INVENTORY.csv`
4. **Run Validation:** Verify validation passes:
   ```bash
   python3 validate_licenses.py
   python3 license_scan.py
   ```
5. **Legal Review (if needed):** Conditionally allowed licenses require legal review

### Required Fields

Every inventory entry must have:
- `name`: Package name
- `version`: Version constraint
- `component`: RansomEye component
- `language`: python | rust | javascript
- `license`: License identifier
- `license_type`: permissive | weak-copyleft | strong-copyleft | proprietary
- `static_or_dynamic`: static | dynamic
- `distribution_scope`: core | agent | dpi | optional | customer_supplied
- `risk_level`: low | medium | high
- `notes`: Context and justification

---

## Maintenance

### Quarterly Audit

- Review all dependencies for license accuracy
- Verify no new forbidden licenses introduced
- Update inventory for any license changes
- Document any policy changes in `THIRD_PARTY_LICENSES.md`

### Continuous Validation

- CI/CD runs validation on every commit
- Automated tools catch violations immediately
- Manual review required for new dependencies

---

## Troubleshooting

### Validation Fails: "Dependency not in inventory"

**Solution:** Add dependency to `THIRD_PARTY_INVENTORY.json` with all required fields.

### Validation Fails: "Forbidden license detected"

**Solution:** Remove dependency or find alternative with allowed license. Do not proceed without legal approval.

### Validation Fails: "Missing required fields"

**Solution:** Complete all required fields in inventory entry. See "Adding New Dependencies" section.

### CI Gate Fails: "Script error"

**Solution:** Verify all files exist:
- `LICENSE_POLICY.json`
- `THIRD_PARTY_INVENTORY.json`
- `license_scan.py`
- `validate_licenses.py`

---

## Legal Notes

- This compliance bundle is legally binding infrastructure, not documentation
- All license decisions must be documented in `THIRD_PARTY_LICENSES.md`
- Exceptions to policy require legal review and C-level approval
- Inventory must be kept complete and accurate at all times
- CI/CD enforcement ensures no accidental violations

---

## Contact

For license compliance questions:
- **Legal:** [Legal contact]
- **Engineering:** [Engineering contact]

---

**Last Updated:** 2024-01-10  
**Version:** 1.0  
**Status:** Production-Ready
