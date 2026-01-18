# RansomEye — Signing Ceremony & Key Custody SOP

**Authoritative Operational Procedure (Trust Root / Stage-7 Enablement)**
**Applies to:** RansomEye v1.0.x and all future releases
**Status:** REQUIRED · NON-OPTIONAL · AUDITABLE

This SOP operationalizes **Stage-7 (Signing)** of the release pipeline and defines **exact human procedures** for key generation, custody, signing, handoff, emergency response, and audit.
No CI/CD implementation is valid without this SOP.

---

## 1. PURPOSE & SCOPE

This SOP governs:

* Root & Release key generation
* Private key custody and access
* Human-executed signing operations
* CI ↔ Signing handoff protocols
* Emergency and compromise response
* Audit, logging, and compliance evidence

It applies to **all personnel** involved in release engineering or security oversight.

---

## 2. ROLES & AUTHORITY (MANDATORY)

| Role                      | Responsibility                                  |
| ------------------------- | ----------------------------------------------- |
| **Release Engineer (RE)** | Coordinates releases, prepares unsigned bundles |
| **Security Officer (SO)** | Controls signing authority, key custody         |
| **Witness (W1/W2)**       | Independent observers for ceremonies            |
| **Auditor**               | Post-facto review only                          |

**Dual-control rule:**
No single individual may both *prepare* and *sign* a release.

---

## 3. KEY HIERARCHY (REFERENCE)

* **Root Signing Key (RSK)** — Trust anchor (offline, never signs artifacts)
* **Release Signing Key (LSK)** — Signs manifests & checksums
* **Emergency Revocation Key (ERK)** — Revocation only

---

## 4. KEY GENERATION CEREMONY (ONE-TIME / RARE)

### 4.1 Preconditions

* Air-gapped machine (no NIC, Wi-Fi, Bluetooth disabled)
* Fresh OS install
* Verified hashing tools
* Two witnesses physically present
* Video/audio recording (if policy allows)

### 4.2 Steps

1. Boot air-gapped machine
2. Verify entropy source
3. Generate **Root Signing Key**
4. Generate **Release Signing Key**
5. Root key signs Release key public material
6. Compute and record:
   * Fingerprints
   * Creation timestamp
   * Algorithms used
7. Print ceremony record
8. Witnesses sign ceremony record
9. Encrypt private keys
10. Store keys on **separate physical media**
11. Power off machine
12. Securely wipe temporary storage

### 4.3 Artifacts Produced

* `root.pub`
* `release.pub`
* Signed ceremony record
* Fingerprint registry (immutable)

---

## 5. KEY CUSTODY & STORAGE

### 5.1 Private Keys

* Stored **offline only**
* Encrypted removable media (or HSM)
* Stored in physically separate locations
* No cloud storage
* No network-connected systems

### 5.2 Access Control

* 2-person rule enforced
* Access log required:
  * Who
  * When
  * Purpose
* Physical presence mandatory

---

## 6. STAGE-6 HANDOFF (CI → SIGNING)

### 6.1 Input

Unsigned bundle:

```
ransomeye-vX.Y.Z-unsigned/
```

### 6.2 Transfer Methods (choose one, document choice)

* Secure removable media
* Secure internal artifact vault
* Air-gap transfer workstation

### 6.3 Verification Before Acceptance

Signer must:

1. Verify bundle hash matches CI record
2. Verify manifest completeness
3. Confirm version/tag

If mismatch → **REJECT BUNDLE**

---

## 7. STAGE-7 SIGNING PROCEDURE (CORE SOP)

### 7.1 Preconditions

* Two authorized individuals present
* Release Signing Key available
* Offline signing workstation

### 7.2 Signing Steps

1. Verify unsigned bundle checksums locally
2. Sign:
   * `SHA256SUMS → SHA256SUMS.sig`
   * `manifest.json → manifest.json.sig`
3. Verify signatures locally
4. Record:
   * Signer identity
   * Key fingerprint
   * Timestamp
   * Bundle hash

### 7.3 Prohibitions

❌ Do NOT sign if any check fails
❌ Do NOT modify bundle contents
❌ Do NOT connect signing system to network

---

## 8. STAGE-8 HANDOFF (SIGNING → CI)

### 8.1 Output

Signed bundle:

```
ransomeye-vX.Y.Z/
```

Includes:

* `.sig` files
* Original artifacts unchanged

### 8.2 Transfer

Same secure mechanism as Stage-6 (reverse direction)

### 8.3 CI Intake Rule

CI must **verify signatures before any promotion**.
Failure = permanent block.

---

## 9. EMERGENCY PROCEDURES

### 9.1 Release Key Compromise

1. Stop all releases
2. Revoke key immediately
3. Publish revocation notice
4. Generate new Release key
5. Root signs new key
6. Re-sign affected releases

### 9.2 Root Key Compromise

1. Activate Emergency Revocation Key
2. Declare trust reset
3. Generate new Root & Release keys
4. Re-sign all supported releases

### 9.3 Lost Key Media

* Treat as compromise unless proven otherwise

---

## 10. AUDIT & LOGGING (NON-OPTIONAL)

For each release:

* CI run ID
* Unsigned bundle hash
* Signing log
* Signer identities
* Key fingerprints
* Verification logs

Retention: **≥ 7 years**

---

## 11. COMPLIANCE ALIGNMENT

This SOP satisfies:

* SOC2 (CC6, CC7)
* ISO-27001 (A.10, A.12)
* Supply-chain security controls

---

## 12. NON-NEGOTIABLE RULES (LOCKED)

❌ CI/CD never holds private keys
❌ Signing never happens online
❌ No signature = NO SHIP
❌ No witness = INVALID CEREMONY
❌ SOP deviation requires incident report

---

## STATUS

* **SOP:** COMPLETE
* **Stage-7:** OPERATIONAL
* **Pipeline implementation:** UNBLOCKED
