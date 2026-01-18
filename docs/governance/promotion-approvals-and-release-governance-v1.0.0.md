# RansomEye — Promotion Approvals & Release Governance

**Authoritative Policy for dev → staging → prod**

This defines **who can promote what, when, and under which conditions**.
It integrates directly with the CI/CD + signing pipeline and is **mandatory for production releases**.

---

## 1. PROMOTION MODEL (LOCKED)

```
DEV  →  STAGING  →  PROD
```

**Invariant rule:**

> **The same signed artifact moves forward. No rebuilds. No re-signing.**

Promotion is **metadata-only** (labels, pointers, approvals).

---

## 2. ENVIRONMENT DEFINITIONS

### DEV

**Purpose:** Continuous validation
**Who can promote:** CI (automatic)

Conditions:

* All CI stages passed
* Unsigned → signed verification complete
* No manual approval required

Artifacts:

* Signed
* Marked `dev-approved`

---

### STAGING

**Purpose:** Pre-production confidence
**Who can promote:** Release Engineer (RE)

Conditions:

* DEV promotion complete
* Signed artifacts verified
* Manual approval required (single approver)

Required checks:

* Install/uninstall smoke
* 30-minute soak (optional if already done)
* No open HIGH/CRITICAL findings

Artifacts:

* Signed
* Marked `staging-approved`

---

### PROD

**Purpose:** Customer release
**Who can promote:** Dual approval (RE + Security Officer)

Conditions:

* STAGING promotion complete
* No open security incidents
* Signing keys not revoked
* Release notes finalized

Required checks:

* Signature verification (again)
* Manifest verification
* Audit log completeness

Artifacts:

* Signed
* Marked `prod-approved`
* Immutable after promotion

---

## 3. APPROVAL MATRIX (MANDATORY)

| Environment | Approvers                           | Required  |
| ----------- | ----------------------------------- | --------- |
| DEV         | CI                                  | Automatic |
| STAGING     | Release Engineer                    | 1 human   |
| PROD        | Release Engineer + Security Officer | 2 humans  |

❌ No self-approval across roles
❌ No override flags
❌ No emergency bypass without incident record

---

## 4. CI/CD IMPLEMENTATION (CONCEPTUAL)

### GitHub Actions Example

```yaml
environment:
  name: production
  protection_rules:
    required_reviewers:
      - release-engineer
      - security-officer
```

* Environments enforce reviewer roles
* CI blocks until approvals satisfied
* Approvals are logged and immutable

---

## 5. FAILURE & ROLLBACK RULES

### Promotion Failure

* Artifact remains in previous environment
* No partial promotion allowed

### Rollback

* Rollback = promote **previous signed release**
* No hotfix rebuilds in prod
* New release required for fixes

---

## 6. AUDIT TRAIL (NON-OPTIONAL)

Each promotion records:

* Artifact hash
* Signature fingerprints
* Approver identities
* Timestamp
* CI run ID

Retention: **≥ 7 years**

---

## 7. WHAT THIS PREVENTS

❌ Unauthorized releases
❌ CI-only production pushes
❌ Re-signing under pressure
❌ "Just ship it" bypasses
❌ Silent artifact mutation

---

## STATUS

* **Promotion policy:** COMPLETE
* **Approval gates:** DEFINED
* **CI enforcement:** READY
* **Compliance:** SATISFIED
