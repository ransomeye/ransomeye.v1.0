# RansomEye LLM Generative Summarizer

**AUTHORITATIVE:** Offline LLM summarizer for generating human-readable incident narratives from structured facts

## Overview

The RansomEye LLM Generative Summarizer generates human-readable incident narratives from structured facts. This module is **separate from explanation-assembly** (which only reorders existing content). This module **generates new text** using offline LLM models.

## Core Principles

### Non-Decisional, Non-Enforcing, Text-Only

**CRITICAL**: Summarizer is text-only:

- ✅ **No enforcement**: No enforcement actions
- ✅ **No decisions**: No decision logic
- ✅ **No raw packets**: No packet inspection
- ✅ **No secrets**: No secret extraction
- ✅ **Text generation only**: Generates narrative text from facts

### Deterministic and Auditable

**CRITICAL**: All operations are deterministic and auditable:

- ✅ **Deterministic prompts**: Same inputs → same prompts
- ✅ **Prompt hash logged**: Every prompt hash is logged
- ✅ **Output hash logged**: Every output hash is logged
- ✅ **Audit ledger**: All operations emit ledger entries

### PII Redaction at Generation Time

**CRITICAL**: PII is redacted before generation:

- ✅ **Pre-generation redaction**: PII redacted before prompt assembly
- ✅ **Redaction log**: Complete redaction log maintained
- ✅ **Policy modes**: STRICT | BALANCED | FORENSIC

### Air-Gapped Capable

**CRITICAL**: Summarizer works offline:

- ✅ **Offline LLM**: Uses GGUF format models
- ✅ **No online APIs**: No external API calls
- ✅ **No network**: No network access required

## Architecture

### Separation from explanation-assembly

- **explanation-assembly/**: Reorders existing explanations (no generation)
- **llm-summarizer/**: Generates new text from structured facts

These are separate subsystems with different responsibilities.

## Module Structure

```
llm-summarizer/
├── schema/
│   ├── summary-request.schema.json
│   ├── summary-output.schema.json
│   ├── prompt-template.schema.json
│   └── redaction-log.schema.json
├── redaction/
│   ├── redaction_engine.py
│   ├── pattern_detector.py
│   └── redaction_policy.py
├── prompts/
│   ├── template_registry.py
│   ├── prompt_assembler.py
│   └── prompt_hasher.py
├── llm/
│   ├── sandbox.py
│   └── token_manager.py
├── output/
│   ├── validator.py
│   ├── signer.py
│   └── renderer.py
├── storage/
│   └── summary_store.py
└── api/
    └── summarizer_api.py
```

## Implementation Status

**Phase 5.1 Foundation**: ✅ **COMPLETE**  
**Phase 5.2 Inference**: ✅ **COMPLETE**  
**Phase 5.3 Rendering**: ✅ **COMPLETE**  
**Phase 5.4 Templates**: ✅ **COMPLETE**  
**Phase 5.5 CLI Tools**: ✅ **COMPLETE**

### Implemented

1. ✅ **Schemas**: All four frozen JSON schemas
2. ✅ **PII Redaction**: Deterministic redaction engine with STRICT/BALANCED/FORENSIC modes
3. ✅ **Prompt Registry**: Immutable template registry with hash verification
4. ✅ **Prompt Assembly**: Deterministic prompt assembly from templates
5. ✅ **Model Loader**: GGUF model loading with hash verification and registry integration
6. ✅ **Token Manager**: Real tokenization using model tokenizer
7. ✅ **Inference Engine**: Deterministic LLM inference with strict limits
8. ✅ **Sandbox**: Execution sandbox with token/memory/time limits and inference integration
9. ✅ **Output Validation**: Schema-based output validation
10. ✅ **Output Signing**: ed25519 output signing
11. ✅ **Audit Integration**: All operations emit audit ledger entries

### NOT Implemented Yet

1. ❌ **None** - All core functionality complete

## Usage

### Register Template

```bash
python3 llm-summarizer/cli/register_template.py \
    --template-file prompts/templates/soc_narrative_v1.0.0.jinja2 \
    --narrative-type SOC_NARRATIVE \
    --version 1.0.0 \
    --registered-by admin@example.com \
    --registry-path /var/lib/ransomeye/llm-summarizer/templates.jsonl
```

### List Templates

```bash
python3 llm-summarizer/cli/list_templates.py \
    --registry-path /var/lib/ransomeye/llm-summarizer/templates.jsonl
```

### Generate Summary

```bash
python3 llm-summarizer/cli/generate_summary.py \
    --request-file request.json \
    --output-file summary.json
```

### Render Summary

```bash
python3 llm-summarizer/cli/render_summary.py \
    --summary-id <uuid> \
    --format PDF \
    --output-file summary.pdf
```

### Verify Model

```bash
python3 llm-summarizer/cli/verify_model.py \
    --model-id <uuid> \
    --model-version 1.0.0 \
    --model-path /path/to/model.gguf
```

## Failure Modes (Fail-Closed)

All failure modes cause explicit rejection:

- ❌ Invalid request schema → Reject
- ❌ Template not found → Reject
- ❌ Template hash mismatch → Reject
- ❌ Token limit exceeded → Reject
- ❌ Memory limit exceeded → Reject
- ❌ Timeout exceeded → Reject
- ❌ Output validation fails → Reject
- ❌ Signing fails → Reject
- ❌ Audit ledger write fails → Reject

## Next Phase

**Phase 5.2 - Inference Layer** will implement:
1. LLM model loading (GGUF format)
2. Actual text generation
3. Model registry integration
4. Output rendering (PDF/HTML/CSV)

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye LLM Generative Summarizer documentation.
