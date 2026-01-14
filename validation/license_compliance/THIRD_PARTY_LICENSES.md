# RansomEye Third-Party License Inventory and Policy

**Document Status:** Authoritative Legal Document  
**Last Updated:** 2024-01-10  
**Purpose:** Complete inventory of all third-party dependencies, their licenses, and RansomEye license compliance policy.

---

## Executive Summary

This document provides a complete inventory of all third-party software dependencies used in RansomEye, their license classifications, and the policies governing their use. This document is intended for:

- Legal and compliance review
- Customer license audits
- Commercial licensing verification
- Regulatory compliance documentation

**Critical Policy:** RansomEye prohibits the use of GPL, AGPL, and other strong copyleft licenses that would require RansomEye source code to be disclosed or licensed under copyleft terms.

---

## License Summary Table

| License | Type | Status | Count | Notes |
|---------|------|--------|-------|-------|
| MIT | Permissive | ✅ ALLOWED | 20 | Most permissive, no restrictions |
| Apache-2.0 | Permissive | ✅ ALLOWED | 12 | Patent grant included |
| BSD-3-Clause | Permissive | ✅ ALLOWED | 7 | Minimal restrictions |
| BSD-2-Clause | Permissive | ✅ ALLOWED | 1 | Minimal restrictions |
| MPL-2.0 | Permissive | ✅ ALLOWED | 1 | File-level copyleft only |
| LGPL-3.0 | Weak Copyleft | ⚠️ CONDITIONAL | 1 | Dynamic linking only (psycopg2-binary) |
| GPL-2.0 | Strong Copyleft | ❌ FORBIDDEN | 0 | Not used |
| GPL-3.0 | Strong Copyleft | ❌ FORBIDDEN | 0 | Not used |
| AGPL-3.0 | Strong Copyleft | ❌ FORBIDDEN | 0 | Not used |

**Total Dependencies:** 42  
**Forbidden Dependencies:** 0  
**Conditionally Allowed:** 1 (LGPL-3.0, dynamic linking only)

---

## Explicitly ALLOWED Licenses

The following licenses are explicitly allowed for use in RansomEye without restriction:

### MIT License
- **Status:** ✅ ALLOWED
- **Rationale:** Most permissive license. Allows commercial use, modification, distribution, and private use without restrictions.
- **Dependencies:** react, react-dom, vite, vitejs-plugin-react, bitsandbytes (see binary redistribution note), jsonlines, pyyaml, python-dotenv, llama-cpp-python, beautifulsoup4, fastapi, fastapi-cors, pydantic, pydantic-settings, jsonschema, sha2, hostname

### Apache License 2.0
- **Status:** ✅ ALLOWED
- **Rationale:** Permissive license with explicit patent grant. Allows commercial use without copyleft requirements.
- **Dependencies:** transformers, peft, accelerate, datasets, rouge-score, requests, cryptography, python-dateutil

### BSD-3-Clause License
- **Status:** ✅ ALLOWED
- **Rationale:** Permissive license with minimal restrictions (attribution, no endorsement). Compatible with commercial licensing.
- **Dependencies:** torch (primary license, includes Apache-2.0 components), pandas, numpy, scikit-learn, python-dotenv, uvicorn

### BSD-2-Clause License
- **Status:** ✅ ALLOWED
- **Rationale:** Permissive license with minimal restrictions. Compatible with commercial licensing.
- **Dependencies:** uuid (Python)

### Mozilla Public License 2.0 (MPL-2.0)
- **Status:** ✅ ALLOWED
- **Rationale:** File-level copyleft only. Does not require disclosure of entire codebase. Compatible with commercial licensing.
- **Dependencies:** tqdm

### Dual-Licensed (Apache-2.0 OR MIT)
- **Status:** ✅ ALLOWED
- **Rationale:** RansomEye may choose either license term. Defaults to MIT (more permissive).
- **Dependencies:** reqwest, uuid (Rust), serde, serde_json, chrono, anyhow

---

## Explicitly FORBIDDEN Licenses

The following licenses are explicitly forbidden and must not be used in RansomEye:

### GNU General Public License (GPL) - All Versions
- **GPL-2.0:** ❌ FORBIDDEN
- **GPL-3.0:** ❌ FORBIDDEN
- **GPL-2.0+:** ❌ FORBIDDEN
- **GPL-3.0+:** ❌ FORBIDDEN
- **Rationale:** GPL requires all derivative works to be licensed under GPL, which would require RansomEye source code to be disclosed and licensed under GPL. This is incompatible with RansomEye commercial licensing model.

### GNU Affero General Public License (AGPL) - All Versions
- **AGPL-1.0:** ❌ FORBIDDEN
- **AGPL-3.0:** ❌ FORBIDDEN
- **AGPL-3.0+:** ❌ FORBIDDEN
- **Rationale:** AGPL extends GPL copyleft to network services. Any service using AGPL code must provide source code to all network users. This is incompatible with RansomEye commercial licensing and would require complete source disclosure.

### Enforcement
- CI/CD pipelines automatically reject any dependency with GPL or AGPL licenses
- Manual code reviews must verify no GPL/AGPL dependencies are introduced
- Legal review required for any exception requests (exceptions are not expected)

---

## Conditionally ALLOWED Licenses

### GNU Lesser General Public License (LGPL-3.0)
- **Status:** ⚠️ CONDITIONAL - Dynamic Linking Only
- **Dependency:** psycopg2-binary (PostgreSQL adapter)
- **Condition:** Must be used via dynamic linking only. **Static bundling is FORBIDDEN.**
- **Rationale:** LGPL-3.0 allows dynamic linking without copyleft contamination. The library is used as a dynamically linked Python extension, which is explicitly allowed under LGPL-3.0.
- **Verification:** CI validates that psycopg2-binary is used as a dynamically linked library only (standard Python package installation method).

**Legal Analysis:**
- LGPL-3.0 Section 4(d) allows linking with a "work that uses the Library" via dynamic linking
- Python's import mechanism uses dynamic linking
- No static linking occurs
- RansomEye code is not a derivative work of psycopg2-binary
- **CRITICAL:** Static bundling (including psycopg2-binary in a single executable) would violate LGPL-3.0 and is explicitly prohibited

---

## Special License Handling Rules

### LLM / ML Model Licenses

**Rule:** LLM models used in RansomEye (via llama-cpp-python, transformers, etc.) may have separate licensing terms for model weights. Model licenses are distinct from code licenses.

**Handling:**
- Model code libraries (transformers, llama-cpp-python) use permissive licenses (Apache-2.0, MIT) - ✅ ALLOWED
- Model weights may have separate licenses (e.g., Llama 2 Community License, proprietary licenses)
- All model licenses must be documented in THIRD_PARTY_INVENTORY.json notes field
- Proprietary models require explicit customer agreement
- Model licenses do not affect RansomEye code licensing (models are data, not code)

**Current Models:**
- Models loaded via transformers library: License depends on specific model
- Models loaded via llama-cpp-python (GGUF format): License depends on specific model
- All model licenses must be verified before deployment

### Transitive Dependencies

**Rule:** Transitive dependencies (dependencies of dependencies) are not individually inventoried unless they pose license risk.

**Handling:**
- Only direct dependencies are inventoried in THIRD_PARTY_INVENTORY.json
- Transitive dependencies with permissive licenses (MIT, Apache-2.0, BSD) are acceptable and not individually tracked
- Transitive dependencies with copyleft licenses must be flagged during dependency selection
- Example: transformers library has transitive dependencies (filelock, huggingface-hub, numpy, packaging, pyyaml, regex, requests, tokenizers, safetensors, tqdm) - all permissively licensed, not individually inventoried

### Binary Redistribution

**Rule:** Libraries that include binary components may have additional redistribution requirements beyond code licenses.

**Handling:**
- Binary redistribution must comply with all applicable EULAs (e.g., NVIDIA CUDA Toolkit EULA for CUDA binaries)
- Source code redistribution follows code license terms (e.g., MIT for bitsandbytes source)
- Binary redistribution risks are documented in inventory notes field
- Risk level may be elevated for libraries with binary components (e.g., bitsandbytes marked as medium risk due to CUDA binary redistribution requirements)

### Grafana / AGPL Handling

**Rule:** Grafana uses AGPL-3.0. If Grafana is required, it MUST be deployed as a separate service with clear boundaries. Direct code integration is FORBIDDEN.

**Current Status:** Grafana is NOT used in RansomEye core components.

**If Required:**
- Must be deployed as separate service (not integrated into RansomEye codebase)
- Must be documented as `customer_supplied` distribution_scope
- Requires legal review and customer agreement
- Clear service boundaries must be maintained

### Kernel / Syscall Clarification

**Rule:** Use of Linux kernel syscalls via standard library (libc, Rust std, Python stdlib) does NOT constitute GPL contamination.

**Legal Basis:**
- Syscalls are interfaces, not derived works
- Standard library usage is explicitly allowed
- No GPL code is linked or included
- This is standard practice and legally sound

**Enforcement:** No enforcement needed - syscall usage is standard and legal.

---

## Component-Level License Inventory

### Core Platform Components

#### Python Dependencies (Core Services)
- **ingest:** fastapi (MIT), uvicorn (BSD-3-Clause), psycopg2-binary (LGPL-3.0, dynamic linking only), jsonschema (MIT), python-dateutil (Apache-2.0), pydantic (MIT), pydantic-settings (MIT)
- **correlation-engine:** psycopg2-binary (LGPL-3.0, dynamic linking only), uuid (BSD-2-Clause, Python package), pydantic (MIT), pydantic-settings (MIT)
- **ai-core:** psycopg2-binary (LGPL-3.0, dynamic linking only), uuid (BSD-2-Clause, Python package), scikit-learn (BSD-3-Clause), numpy (BSD-3-Clause), python-dateutil (Apache-2.0), pydantic (MIT), pydantic-settings (MIT)
- **policy-engine:** psycopg2-binary (LGPL-3.0, dynamic linking only), cryptography (Apache-2.0), python-dateutil (Apache-2.0), pydantic (MIT), pydantic-settings (MIT)
- **ui-backend:** fastapi (MIT), uvicorn (BSD-3-Clause), psycopg2-binary (LGPL-3.0, dynamic linking only), fastapi-cors (MIT), pydantic (MIT), pydantic-settings (MIT)

#### Rust Dependencies (Linux Agent)
- **linux-agent:** reqwest (Apache-2.0 OR MIT), uuid (Apache-2.0 OR MIT), serde (Apache-2.0 OR MIT), serde_json (Apache-2.0 OR MIT), sha2 (MIT), chrono (MIT OR Apache-2.0), anyhow (MIT OR Apache-2.0), hostname (MIT)

#### JavaScript Dependencies (UI Frontend)
- **ui-frontend:** react (MIT), react-dom (MIT), vitejs-plugin-react (MIT), vite (MIT)

#### Python Dependencies (ML Training - mishka)
- **mishka:** torch (BSD-3-Clause), transformers (Apache-2.0), peft (Apache-2.0), accelerate (Apache-2.0), bitsandbytes (MIT), datasets (Apache-2.0), pandas (BSD-3-Clause), numpy (BSD-3-Clause), jsonlines (MIT), scikit-learn (BSD-3-Clause), rouge-score (Apache-2.0), tqdm (MPL-2.0), pyyaml (MIT), python-dotenv (BSD-3-Clause), llama-cpp-python (MIT), requests (Apache-2.0), beautifulsoup4 (MIT)

---

## Distribution Scope Definitions

### Core
Components distributed as part of the main RansomEye platform. All dependencies must use allowed licenses or conditionally allowed licenses with explicit approval.

### Agent
Endpoint agent components (Linux, Windows agents). Distributed separately but part of core product. Same license requirements as core.

### DPI
Deep Packet Inspection components. Strict security requirements. Must use allowed licenses only.

### Optional
Optional components that may not be deployed in all installations. Customer must explicitly opt-in. Must use allowed licenses only.

### Customer Supplied
Components supplied by customer, not by RansomEye. Customer responsibility for license compliance. Must be documented but not validated by RansomEye.

---

## Risk Assessment

### Low Risk (Permissive Licenses)
- **Count:** 41 dependencies
- **Licenses:** MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, MPL-2.0, dual-licensed (Apache-2.0 OR MIT)
- **Risk Level:** Low
- **Rationale:** No copyleft requirements, no source disclosure requirements, compatible with commercial licensing

### Medium Risk (Conditionally Allowed)
- **Count:** 1 dependency
- **License:** LGPL-3.0 (psycopg2-binary)
- **Risk Level:** Medium
- **Rationale:** Requires dynamic linking only. Properly used via Python's dynamic import mechanism. Risk is mitigated by proper usage pattern.

### High Risk (Forbidden)
- **Count:** 0 dependencies
- **Licenses:** GPL, AGPL
- **Risk Level:** High
- **Rationale:** Would require RansomEye source code disclosure. Not used.

---

## Compliance Verification

### Automated Verification
- **CI/CD Integration:** All dependencies are validated in CI/CD pipeline
- **Tools:** license_scan.py, validate_licenses.py, ci_license_gate.sh
- **Frequency:** Every commit, every build
- **Failure Mode:** Build fails immediately on license violation

### Manual Verification
- **Frequency:** Quarterly full audit
- **Scope:** All dependencies across all components
- **Process:** Legal review of new dependencies, verification of license accuracy
- **Documentation:** All decisions documented in this file

### Customer Verification
- **Inventory Access:** Customers may review THIRD_PARTY_INVENTORY.json and THIRD_PARTY_INVENTORY.csv
- **Policy Access:** Customers may review LICENSE_POLICY.json and this document
- **Verification Tools:** Customers may run validate_licenses.py independently
- **Audit Support:** RansomEye provides license compliance documentation for customer audits

---

## Legal Review Process

### New Dependency Approval
1. Developer identifies need for new dependency
2. Developer checks LICENSE_POLICY.json for allowed/forbidden status
3. If allowed: Add to inventory, proceed
4. If conditionally allowed: Legal review required, document rationale
5. If forbidden: Find alternative or request exception (exceptions require C-level approval)

### Exception Process
1. Submit exception request with business justification
2. Legal review of exception request
3. C-level approval required
4. Document exception in LICENSE_POLICY.json conditionally_allowed section
5. Update THIRD_PARTY_LICENSES.md with rationale

---

## Change Log

- **2024-01-10:** Initial license compliance bundle created. All 42 dependencies inventoried. Zero forbidden licenses. One conditionally allowed license (LGPL-3.0, psycopg2-binary, dynamic linking only).

---

## Contact

For license compliance questions or exception requests, contact:
- Legal: [Legal contact information]
- Engineering: [Engineering contact information]

---

**Document Authority:** This document is authoritative for RansomEye license compliance. All license decisions must be documented here. No exceptions may be granted without updating this document.
