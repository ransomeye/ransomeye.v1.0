# RansomEye Orchestrator & Workflow Engine

**AUTHORITATIVE:** Deterministic, authority-bound workflow orchestration

## Overview

The RansomEye Orchestrator & Workflow Engine coordinates **when and how subsystems run**, **in what order**, and **under what authority**, without embedding any detection, policy, or enforcement logic. The Orchestrator is **not intelligence** - it is **deterministic workflow control**.

## Core Principles

### Deterministic Workflow Control

**CRITICAL**: Orchestrator is deterministic workflow control:

- ✅ **No hidden schedulers**: No cron-like behavior
- ✅ **No background autonomy**: No background execution
- ✅ **No ML / heuristics**: No intelligent decision-making
- ✅ **No retries with implicit state**: No hidden retry logic
- ✅ **No execution without authority proof**: Authority validation required
- ✅ **No workflow without explanation reference**: Explanation bundle required

### Explicit Execution

**CRITICAL**: All execution is explicit:

- ✅ **Pull-based**: Execution is pull-based, never push
- ✅ **Job records**: Each step produces immutable job record
- ✅ **Fail-closed**: Failures are explicit and terminal
- ✅ **No dynamic branching**: No runtime branching logic

### Authority-Bound

**CRITICAL**: All workflows are authority-bound:

- ✅ **Authority validation**: Execution requires authority validation
- ✅ **Explanation-anchored**: Execution requires explanation bundle
- ✅ **Replayable**: Entire workflows are replayable
- ✅ **Audit-anchored**: All operations are audit-anchored

## Workflow Definition

### Required Fields

Each workflow MUST define:

- **workflow_id**: Unique identifier (UUID)
- **version**: Semantic version (semver)
- **allowed_triggers**: Allowed trigger types (manual | alert | validator)
- **required_authority**: Required authority level (NONE | HUMAN | ROLE)
- **required_explanation_type**: Required explanation bundle type (SEE)
- **steps**: Ordered workflow steps
- **failure_policy**: Failure handling policy (STOP | ROLLBACK | RECORD_ONLY)

### Workflow Step Requirements

Each step MUST include:

- **step_id**: Unique identifier (UUID)
- **step_type**: Step type (ALERT_DELIVERY | IR_EXECUTION | VALIDATION | REPORT_GEN)
- **input_refs**: Explicit data dependencies
- **output_refs**: Output references
- **authority_required**: Required authority level (NONE | HUMAN | ROLE)
- **explanation_required**: Whether explanation bundle is required
- **deterministic_timeout**: Timeout in seconds

## Execution Rules

### Execution Flow

1. **Load workflow**: Load workflow from registry
2. **Validate trigger**: Validate trigger type is allowed
3. **Validate authority**: Validate authority state
4. **Validate explanation**: Validate explanation bundle
5. **Resolve dependencies**: Resolve execution order (DAG)
6. **Execute steps**: Execute steps in order
7. **Store job records**: Store immutable job records
8. **Emit audit entries**: Emit audit ledger entries

### Failure Handling

- **STOP**: Stop execution on failure
- **ROLLBACK**: Rollback on failure (requires explicit rollback steps)
- **RECORD_ONLY**: Record failure but continue

### Dependency Resolution

- **DAG validation**: Workflow must be valid DAG
- **Topological sort**: Execution order determined by dependencies
- **No cycles**: Cyclic dependencies are rejected
- **Deterministic**: Same workflow = same execution order

## Replay & Rehydration

### Replay Requirements

Entire workflows must be replayable from:

- **Audit Ledger**: All workflow operations
- **Job records**: All job executions
- **Explanation bundles**: All explanation references
- **Authority actions**: All authority validations

### Replay Guarantees

Replay must produce:

- ✅ **Identical job order**: Same execution order
- ✅ **Identical outputs**: Same step outputs
- ✅ **Identical hashes**: Same job record hashes

## Required Integrations

Orchestrator integrates with:

- **Audit Ledger**: Every job start/finish/failure
- **System Explanation Engine (SEE)**: Pre-execution checks
- **Human Authority Framework (HAF)**: Execution permission
- **Incident Response Engine**: Execution handoff only
- **Global Validator**: Workflow replay & assurance

## Usage

### Register Workflow

```python
from api.orchestrator_api import OrchestratorAPI

api = OrchestratorAPI(
    workflows_store_path=Path('/var/lib/ransomeye/workflows/workflows.jsonl'),
    jobs_store_path=Path('/var/lib/ransomeye/workflows/jobs.jsonl'),
    ledger_path=Path('/var/lib/ransomeye/audit/ledger.jsonl'),
    ledger_key_dir=Path('/var/lib/ransomeye/audit/keys')
)

workflow = {
    'workflow_id': 'workflow-uuid',
    'version': '1.0.0',
    'allowed_triggers': ['manual', 'alert'],
    'required_authority': 'HUMAN',
    'required_explanation_type': 'alert_explanation',
    'steps': [...],
    'failure_policy': 'STOP'
}

api.register_workflow(workflow)
```

### Execute Workflow

```bash
python3 orchestrator/cli/run_workflow.py \
    --workflow /path/to/workflow.json \
    --trigger-type manual \
    --input-data /path/to/input.json \
    --authority-state VERIFIED \
    --explanation-bundle-id <bundle-uuid> \
    --workflows-store /var/lib/ransomeye/workflows/workflows.jsonl \
    --jobs-store /var/lib/ransomeye/workflows/jobs.jsonl \
    --ledger /var/lib/ransomeye/audit/ledger.jsonl \
    --ledger-key-dir /var/lib/ransomeye/audit/keys \
    --output jobs.json
```

### Replay Workflow

```bash
python3 orchestrator/cli/replay_workflow.py \
    --workflow-id <workflow-uuid> \
    --jobs-store /var/lib/ransomeye/workflows/jobs.jsonl \
    --output replay.json
```

## File Structure

```
orchestrator/
├── schema/
│   ├── workflow.schema.json          # Frozen JSON schema for workflows
│   ├── workflow-step.schema.json    # Frozen JSON schema for steps
│   └── job-record.schema.json       # Frozen JSON schema for job records
├── engine/
│   ├── __init__.py
│   ├── workflow_registry.py         # Immutable workflow storage
│   ├── dependency_resolver.py      # DAG validation and ordering
│   ├── job_executor.py             # Deterministic job execution
│   └── replay_engine.py            # Full workflow rehydration
├── api/
│   ├── __init__.py
│   └── orchestrator_api.py        # Orchestrator API with audit integration
├── cli/
│   ├── __init__.py
│   ├── run_workflow.py             # Execute workflow CLI
│   └── replay_workflow.py          # Replay workflow CLI
└── README.md                        # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **Audit Ledger**: Required for audit trail (separate subsystem)

## Security Considerations

1. **No Implicit Execution**: All execution is explicit
2. **Authority-Bound**: Execution requires authority validation
3. **Explanation-Anchored**: Execution requires explanation bundle
4. **Deterministic**: Same inputs always produce same outputs
5. **Replayable**: Entire workflows are replayable

## Limitations

1. **No Background Execution**: No cron-like behavior
2. **No Dynamic Branching**: No runtime branching logic
3. **No Implicit Retries**: No hidden retry logic
4. **No ML / Heuristics**: No intelligent decision-making
5. **Pull-Based Only**: Execution is pull-based, never push

## Future Enhancements

- Advanced rollback mechanisms
- Workflow versioning and migration
- Workflow templates
- Workflow scheduling (explicit)
- Workflow monitoring and observability

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Orchestrator & Workflow Engine documentation.
