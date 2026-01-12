# RansomEye SOC Copilot (Basic, Read-Only)

**AUTHORITATIVE:** Offline RAG-based assistive intelligence for SOC analysts

## Overview

The RansomEye SOC Copilot provides **offline, read-only assistive intelligence** for SOC analysts using **Retrieval-Augmented Generation (RAG)** with **FAISS vector store** and **GGUF LLM models**. It answers queries using only verifiable, immutable knowledge sources with complete citations and no hallucination.

## Core Principles

### Read-Only Assistive Intelligence

**CRITICAL**: SOC Copilot is read-only:

- ✅ **No enforcement**: Cannot execute enforcement actions
- ✅ **No policy changes**: Cannot modify policies
- ✅ **No playbook execution**: Cannot execute playbooks
- ✅ **No automation**: No automated actions
- ✅ **No internet access**: Fully offline operation
- ✅ **No external LLM APIs**: Uses only offline models

### Offline-Only Operation

**CRITICAL**: All operations are offline:

- ✅ **No internet access**: No network connections required
- ✅ **FAISS vector store**: Local vector search
- ✅ **GGUF models**: Offline LLM inference
- ✅ **Deterministic**: Same inputs always produce same outputs

### No Hallucination

**CRITICAL**: All answers are grounded in sources:

- ✅ **All claims cited**: Every fact has citation
- ✅ **Source references**: Explicit list of all sources
- ✅ **Explicit uncertainty**: "Insufficient data" when appropriate
- ✅ **No hidden inference**: All reasoning is explicit

### Structured Responses

**CRITICAL**: Responses are structured, not free prose:

- ✅ **Structured format**: Summary, facts, data points
- ✅ **Confidence levels**: High, medium, low, insufficient_data
- ✅ **No decision language**: No recommendations as commands
- ✅ **No implicit recommendations**: All recommendations explicit

## Knowledge Sources (Read-Only)

All knowledge sources are read-only and immutable:

- **Audit Ledger**: System action history
- **KillChain Timelines**: Attack timeline events
- **Threat Graph**: Entity relationships
- **Risk Index History**: Risk score history
- **Explanation Bundles (SEE)**: System explanations
- **Playbook Metadata**: Playbook definitions (NOT execution)
- **MITRE ATT&CK Docs**: Offline documentation snapshot

## RAG Architecture

### Document Ingestion

Documents are ingested from knowledge sources:

- **Read-only**: Only reads from sources, never mutates
- **Immutable**: All documents are immutable
- **Verifiable**: All sources are verifiable
- **Deterministic**: Same sources always produce same documents

### Vector Store (FAISS)

FAISS-backed vector store for document embeddings:

- **Offline**: No internet access required
- **Deterministic**: Same documents always produce same embeddings
- **Immutable**: Documents cannot be modified after indexing
- **Fast retrieval**: Efficient similarity search

### Retriever

Deterministic retrieval of relevant documents:

- **Deterministic**: Same query always produces same results
- **Verifiable**: All retrieved documents are verifiable
- **Immutable**: Retrieved documents are immutable

## LLM Integration

### Offline Model Loader (GGUF)

Loads GGUF models for offline inference:

- **GGUF format**: Supports GGUF model format
- **Offline**: No internet access required
- **Deterministic**: Same inputs always produce same outputs
- **Template fallback**: Template responses if model not available

### Prompt Builder

Builds structured prompts:

- **Structured**: Prompts are structured, not free-form
- **Deterministic**: Same inputs always produce same prompt
- **No decision language**: Prompts avoid decision-making language

## Query Engine

### Query Processing

1. **Retrieve documents**: Retrieve relevant documents from vector store
2. **Build prompt**: Build structured prompt with context
3. **Generate answer**: Generate structured answer using LLM
4. **Build citations**: Build citations for all claims
5. **Build response**: Build complete response with citations

### Response Structure

Responses include:

- **Answer**: Structured answer (summary, facts, data points)
- **Confidence level**: High, medium, low, insufficient_data
- **Citations**: Citations for all claims
- **Source references**: Explicit list of all sources
- **Uncertainty indicators**: Indicators of uncertainty

## Feedback Loop

### Analyst Feedback

Analyst feedback is stored but:

- ✅ **Does NOT alter models**: Models remain unchanged
- ✅ **Bundled for retraining**: Feedback bundled for later retraining
- ✅ **Immutable**: Feedback records are immutable
- ✅ **Audit-safe**: All feedback is auditable

## Usage

### Query SOC Copilot

```bash
python3 soc-copilot/cli/ask_soc.py \
    --query "What is the risk score for incident X?" \
    --vector-store /var/lib/ransomeye/copilot/vector_store.faiss \
    --model /var/lib/ransomeye/copilot/model.gguf \
    --feedback-store /var/lib/ransomeye/copilot/feedback.jsonl \
    --incident-id <incident-uuid> \
    --output response.json
```

### Programmatic API

```python
from api.copilot_api import CopilotAPI

api = CopilotAPI(
    vector_store_path=Path('/var/lib/ransomeye/copilot/vector_store.faiss'),
    model_path=Path('/var/lib/ransomeye/copilot/model.gguf'),
    feedback_store_path=Path('/var/lib/ransomeye/copilot/feedback.jsonl')
)

# Query
response = api.ask(
    query_text="What is the risk score for this incident?",
    query_context={'incident_id': 'incident-uuid'}
)

# Store feedback
feedback = api.store_feedback(
    response_id=response['response_id'],
    query_id=response['query_id'],
    analyst_identifier='analyst@example.com',
    feedback_type='helpful',
    feedback_content='Response was accurate'
)
```

## File Structure

```
soc-copilot/
├── schema/
│   ├── query.schema.json           # Frozen JSON schema for queries
│   ├── response.schema.json        # Frozen JSON schema for responses
│   └── feedback.schema.json        # Frozen JSON schema for feedback
├── rag/
│   ├── __init__.py
│   ├── document_ingestor.py        # Document ingestion from knowledge sources
│   ├── vector_store.py             # FAISS vector store
│   └── retriever.py                # Document retrieval
├── llm/
│   ├── __init__.py
│   ├── offline_model_loader.py    # GGUF model loader
│   └── prompt_builder.py           # Structured prompt building
├── engine/
│   ├── __init__.py
│   ├── query_engine.py             # Query processing
│   └── citation_builder.py         # Citation building
├── api/
│   ├── __init__.py
│   └── copilot_api.py              # Copilot API
├── cli/
│   ├── __init__.py
│   └── ask_soc.py                  # Query CLI
└── README.md                       # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **faiss-cpu** or **faiss-gpu**: Required for vector store (pip install faiss-cpu)
- **llama-cpp-python**: Optional for GGUF model loading (pip install llama-cpp-python)
- **sentence-transformers**: Optional for embeddings (pip install sentence-transformers)

## Security Considerations

1. **Read-Only**: No enforcement or policy changes possible
2. **Offline**: No internet access required
3. **No Hallucination**: All claims must have citations
4. **Deterministic**: Same inputs always produce same outputs
5. **Immutable Sources**: All knowledge sources are immutable

## Limitations

1. **No Enforcement**: Cannot execute enforcement actions
2. **No Policy Changes**: Cannot modify policies
3. **No Playbook Execution**: Cannot execute playbooks
4. **No Automation**: No automated actions
5. **Offline Only**: No internet access

## Future Enhancements

- Advanced RAG techniques
- Multi-turn conversations
- Context-aware retrieval
- Improved citation extraction
- Feedback-based model fine-tuning

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye SOC Copilot documentation.
