# RansomEye Mishka — SOC Assistant (Basic, Read-Only)

**AUTHORITATIVE:** Offline RAG-based assistive intelligence for SOC analysts

## Overview

**Mishka** provides **offline, read-only assistive intelligence** for SOC analysts using **Retrieval-Augmented Generation (RAG)** with **FAISS vector store** and **GGUF LLM models**. Mishka answers queries using only verifiable, immutable knowledge sources with complete citations and no hallucination.

**Mishka is not an agent. Mishka is not an authority. Mishka is not an automation surface.**

**Mishka is a read-only, citation-bound analytical assistant.**

## Core Principles

### Read-Only Assistive Intelligence

**CRITICAL**: Mishka is read-only:

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

### CPU-First Architecture

**CRITICAL**: Mishka is built for CPU-only environments:

- ✅ **CPU-optimized**: Automatically detects and uses optimal CPU threads
- ✅ **GPU-optional**: Uses GPU if available, gracefully falls back to CPU
- ✅ **No GPU dependency**: Works perfectly on CPU-only systems
- ✅ **Auto-threading**: Detects CPU cores and optimizes thread count

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

### RansomEye System Data
- **Audit Ledger**: System action history
- **KillChain Timelines**: Attack timeline events
- **Threat Graph**: Entity relationships
- **Risk Index History**: Risk score history
- **Explanation Bundles (SEE)**: System explanations
- **Playbook Metadata**: Playbook definitions (NOT execution)

### Cybersecurity Knowledge Bases
- **MITRE ATT&CK Docs**: Offline documentation snapshot
- **CVE Database**: NIST NVD vulnerability data (CVE IDs, CVSS scores, affected products, patches)
- **Threat Intelligence**: IOC databases, APT profiles, malware information
- **Security Advisories**: Vendor advisories, CERT alerts, patch information

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
- **CPU-optimized**: Uses faiss-cpu for CPU-only environments

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
- **CPU-first**: Optimized for CPU-only environments
- **GPU-optional**: Uses GPU if available, falls back to CPU
- **Auto-threading**: Automatically detects optimal CPU thread count
- **Deterministic**: Same inputs always produce same outputs
- **Template fallback**: Template responses if model not available

**CPU Configuration**:
- Automatically detects CPU cores
- Uses 75% of available cores (minimum 2, maximum 8 threads)
- Optimized for CPU-only inference

**GPU Support** (Optional):
- Uses GPU if `llama-cpp-python` was built with GPU support
- Set `LLAMA_CPP_GPU=1` environment variable to enable
- Gracefully falls back to CPU if GPU unavailable

### Prompt Builder

Builds structured prompts:

- **Structured**: Prompts are structured, not free-form
- **Deterministic**: Same inputs always produce same prompt
- **No decision language**: Prompts avoid decision-making language

## Query Engine

### Query Processing

1. **Retrieve documents**: Retrieve relevant documents from vector store
2. **Build prompt**: Build structured prompt with context
3. **Generate answer**: Generate structured answer using LLM (CPU or GPU)
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

### Query Mishka

```bash
python3 mishka/cli/ask_mishka.py \
    --query "What is the risk score for incident X?" \
    --vector-store /var/lib/ransomeye/mishka/vector_store.faiss \
    --model /var/lib/ransomeye/mishka/model.gguf \
    --feedback-store /var/lib/ransomeye/mishka/feedback.jsonl \
    --incident-id <incident-uuid> \
    --output response.json
```

### Programmatic API

```python
from api.mishka_api import MishkaAPI

api = MishkaAPI(
    vector_store_path=Path('/var/lib/ransomeye/mishka/vector_store.faiss'),
    model_path=Path('/var/lib/ransomeye/mishka/model.gguf'),
    feedback_store_path=Path('/var/lib/ransomeye/mishka/feedback.jsonl')
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
mishka/
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
│   ├── offline_model_loader.py     # GGUF model loader (CPU-first, GPU-optional)
│   └── prompt_builder.py           # Structured prompt building
├── engine/
│   ├── __init__.py
│   ├── query_engine.py             # Query processing
│   └── citation_builder.py         # Citation building
├── api/
│   ├── __init__.py
│   └── mishka_api.py               # Mishka API
├── cli/
│   ├── __init__.py
│   └── ask_mishka.py               # Query CLI
└── README.md                       # This file
```

## Dependencies

- **Python 3.8+**: Required for type hints and pathlib
- **faiss-cpu**: Required for vector store (CPU-optimized, recommended)
  ```bash
  pip install faiss-cpu
  ```
- **faiss-gpu**: Optional, only if GPU is available and needed
  ```bash
  pip install faiss-gpu  # Only if GPU available
  ```
- **llama-cpp-python**: Required for GGUF model loading
  ```bash
  # CPU-only build (recommended)
  pip install llama-cpp-python
  # Or with GPU support (optional)
  CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
  ```
- **sentence-transformers**: Optional for embeddings (pip install sentence-transformers)

## CPU-Only Operation

Mishka is designed to work efficiently on CPU-only systems:

1. **Automatic CPU Detection**: Detects available CPU cores and optimizes thread count
2. **No GPU Required**: Works perfectly without GPU
3. **Optimized Threading**: Uses 75% of CPU cores (min 2, max 8 threads)
4. **FAISS CPU**: Uses `faiss-cpu` package for CPU-optimized vector search
5. **GGUF Models**: GGUF format is optimized for CPU inference

**Performance on CPU**:
- Small models (7B parameters): ~2-5 tokens/second
- Medium models (13B parameters): ~1-3 tokens/second
- Response time: Typically 5-15 seconds per query (depending on model size)

**GPU Support** (Optional):
- If GPU is available and `llama-cpp-python` was built with GPU support, Mishka will use it
- Set environment variable `LLAMA_CPP_GPU=1` to enable GPU
- Falls back to CPU automatically if GPU unavailable

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
6. **CPU Performance**: Slower than GPU, but fully functional

## Future Enhancements

- Advanced RAG techniques
- Multi-turn conversations
- Context-aware retrieval
- Improved citation extraction
- Feedback-based model fine-tuning

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye Mishka documentation.

**Note**: The term "SOC Copilot" is deprecated. This subsystem is now authoritatively named **Mishka — SOC Assistant (Basic, Read-Only)**.
