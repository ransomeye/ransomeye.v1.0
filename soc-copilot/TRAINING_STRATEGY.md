# RansomEye SOC Copilot - Training & Fine-Tuning Strategy

**AUTHORITATIVE:** Comprehensive training and fine-tuning strategy for cybersecurity domain expertise and RansomEye-specific conversational understanding

## Overview

This document outlines a multi-stage training and fine-tuning strategy to ensure the SOC Copilot LLM:
1. **Deeply understands cybersecurity concepts** (threats, attacks, defenses, forensics)
2. **Comprehends RansomEye-specific terminology and workflows** (casual conversation about platform usage)
3. **Maintains deterministic, citation-based responses** (no hallucination, all claims grounded)

## Training Philosophy

### Core Principles

- **Domain-Specific Knowledge**: Deep cybersecurity expertise through curated training data
- **Platform-Specific Understanding**: RansomEye terminology, workflows, and concepts
- **Conversational Fluency**: Natural dialogue about security operations and platform usage
- **Deterministic Behavior**: Maintains structured, citable responses (no randomness in production)
- **Offline Capability**: All training produces models that work offline (GGUF format)

## Multi-Stage Training Approach

### Stage 1: Base Cybersecurity Pre-Training (Foundation)

**Objective**: Build strong cybersecurity domain knowledge foundation

**Training Data Sources**:

1. **MITRE ATT&CK Framework**
   - All techniques, tactics, procedures (TTPs)
   - Adversary behaviors and patterns
   - Detection and mitigation strategies
   - Format: Structured Q&A pairs, technique descriptions, detection rules

2. **NIST Cybersecurity Framework**
   - Identify, Protect, Detect, Respond, Recover functions
   - Security controls and best practices
   - Risk management concepts
   - Format: Framework documentation, control descriptions, implementation guides

3. **Security Incident Response Documentation**
   - SANS incident response procedures
   - NIST SP 800-61 (Computer Security Incident Handling Guide)
   - IR playbooks and runbooks
   - Format: Procedural documentation, Q&A on incident handling

4. **Threat Intelligence Sources**
   - APT group profiles and behaviors
   - Malware analysis reports
   - IOC patterns and indicators
   - Format: Threat reports, analysis summaries, indicator descriptions

5. **Forensics and Investigation**
   - Digital forensics methodologies
   - Evidence collection procedures
   - Timeline reconstruction techniques
   - Format: Forensic guides, investigation workflows, evidence analysis

**Training Format**:
```
Instruction: Explain what lateral movement is in cybersecurity.
Response: Lateral movement is a technique used by attackers after initial compromise to explore and expand their access within a network. It involves moving from one system to another, typically using legitimate credentials or exploiting trust relationships. Common methods include Pass-the-Hash, RDP, SSH, and Windows Management Instrumentation (WMI). Detection involves monitoring for unusual authentication patterns, network connections between unrelated systems, and privilege escalation activities. [Source: MITRE ATT&CK T1021]
```

**Expected Outcome**: Model understands cybersecurity terminology, attack patterns, defense strategies, and investigation techniques.

---

### Stage 2: RansomEye Platform-Specific Fine-Tuning

**Objective**: Understand RansomEye architecture, workflows, and terminology

**Training Data Sources**:

1. **RansomEye Architecture Documentation**
   - Component descriptions (agents, DPI, core, etc.)
   - Data flow and event processing
   - System capabilities and limitations
   - Format: Architecture docs, component READMEs, system overviews

2. **RansomEye Knowledge Sources (Synthetic Q&A)**
   - Audit Ledger: "What actions are recorded in the audit ledger?"
   - KillChain Timelines: "How are attack stages determined?"
   - Threat Graph: "What entities are tracked in the threat graph?"
   - Risk Index: "How is risk score calculated?"
   - Explanation Bundles (SEE): "What does the system explainer provide?"
   - Format: Q&A pairs generated from actual system documentation

3. **RansomEye Workflow Conversations**
   - Analyst queries about incidents: "What happened with incident X?"
   - Risk assessment questions: "Why did the risk score change?"
   - Threat correlation: "How are these events related?"
   - Investigation workflows: "Show me the timeline for this attack"
   - Format: Simulated analyst conversations, query-response pairs

4. **RansomEye Schema Understanding**
   - Event envelope structure
   - Incident data models
   - KillChain event formats
   - Audit ledger entries
   - Format: Schema documentation with examples, Q&A on data structures

5. **RansomEye-Specific Terminology**
   - Component names (linux-agent, windows-agent, dpi-probe)
   - Action types (detected, escalated, mitigated, etc.)
   - Incident stages (CLEAN, SUSPICIOUS, PROBABLE, CONFIRMED)
   - Entity types (host, user, process, file, network)
   - Format: Glossary with usage examples, contextual explanations

**Training Format**:
```
Instruction: How do I check the risk score for an incident in RansomEye?
Response: To check the risk score for an incident in RansomEye, you can query the Risk Index history. The risk score is stored in the incidents table with a confidence_score field (0.00 to 100.00). You can also query the Risk Index History knowledge source through the SOC Copilot, which provides historical risk score changes with timestamps. The risk score is computed from evidence confidence levels and accumulates as more evidence is added to an incident. [Source: RansomEye Risk Index, incidents schema]
```

**Expected Outcome**: Model understands RansomEye-specific concepts, can discuss platform features naturally, and knows where to find information in the system.

---

### Stage 3: Conversational Fine-Tuning (Casual Usage)

**Objective**: Enable natural, casual conversation about cybersecurity and RansomEye usage

**Training Data Sources**:

1. **Casual Security Conversations**
   - Analyst-to-analyst discussions about incidents
   - Informal explanations of security concepts
   - Real-world SOC scenarios and questions
   - Format: Simulated conversations, informal Q&A pairs

2. **RansomEye Usage Conversations**
   - "How do I use RansomEye to investigate X?"
   - "What does this alert mean?"
   - "Can RansomEye detect Y?"
   - "How do I find information about Z?"
   - Format: Natural language queries with structured responses

3. **Multi-Turn Conversations**
   - Follow-up questions
   - Clarification requests
   - Context-aware responses
   - Format: Conversation threads with context

4. **Varied Query Phrasing**
   - Formal queries: "What is the risk score for incident 123?"
   - Casual queries: "What's going on with incident 123?"
   - Implicit queries: "Tell me about that suspicious activity"
   - Format: Same intent, different phrasings

**Training Format**:
```
Instruction: Hey, what's up with incident abc-123? I saw it got escalated.
Response: Incident abc-123 was escalated from SUSPICIOUS to PROBABLE stage based on additional evidence. The risk score increased from 45.2 to 67.8 due to detection of lateral movement indicators. The killchain timeline shows progression from Initial Access (T1078) to Execution (T1059). You can review the full timeline in the KillChain Forensics module. [Source: incidents table, killchain-events, audit-ledger]
```

**Expected Outcome**: Model handles casual, conversational queries naturally while maintaining structured, cited responses.

---

### Stage 4: RAG-Optimized Fine-Tuning

**Objective**: Optimize model for RAG (Retrieval-Augmented Generation) workflows

**Training Data Sources**:

1. **Context-Aware Response Generation**
   - Responses that explicitly reference retrieved documents
   - Citation formatting and source attribution
   - Handling insufficient data scenarios
   - Format: Prompt-context-response triplets

2. **Structured Response Formatting**
   - Summary, facts, data points structure
   - Confidence level assignment
   - Uncertainty expression
   - Format: Examples of structured responses with varying confidence

3. **Source Grounding**
   - Only using information from provided sources
   - Explicitly stating when data is insufficient
   - Avoiding hallucination
   - Format: Prompts with context, responses that strictly use context

**Training Format**:
```
Prompt: You are a SOC analyst assistant. Answer using ONLY the provided sources.

Query: What is the risk score for incident xyz-789?

Available Sources:
Source 1 (incidents): {"incident_id": "xyz-789", "confidence_score": 72.5, "current_stage": "PROBABLE"}
Source 2 (audit-ledger): {"action_type": "incident_escalated", "subject": {"type": "incident", "id": "xyz-789"}}

Response: The risk score for incident xyz-789 is 72.5 (confidence score). The incident is currently in PROBABLE stage and was recently escalated according to the audit ledger. [Source: incidents, audit-ledger]
```

**Expected Outcome**: Model excels at using retrieved context, cites sources properly, and avoids hallucination.

---

## Training Data Preparation

### Data Collection Strategy

1. **Curated Cybersecurity Datasets**
   - MITRE ATT&CK: Official documentation → Q&A pairs
   - NIST: Framework docs → Structured knowledge
   - SANS: Training materials → Incident response Q&A
   - Threat reports: Public APT reports → Analysis summaries

2. **RansomEye Documentation Mining**
   - Extract all README files → Component descriptions
   - Parse schema files → Data structure explanations
   - Generate Q&A from code comments → Feature explanations
   - Create workflow examples → Usage scenarios

3. **Synthetic Conversation Generation**
   - Template-based: Fill templates with real data
   - Paraphrasing: Multiple phrasings of same query
   - Context variation: Same query with different contexts
   - Multi-turn: Build conversation threads

4. **Feedback Integration**
   - Use stored analyst feedback as training signal
   - Identify common query patterns
   - Extract preferred response formats
   - Learn from corrections

### Data Quality Assurance

- **Accuracy**: All facts verified against authoritative sources
- **Completeness**: Cover all major cybersecurity domains
- **Consistency**: Terminology consistent across datasets
- **Relevance**: Focus on SOC analyst needs
- **Diversity**: Various query styles and complexity levels

---

## Fine-Tuning Methodology

### Model Selection

**Base Model Recommendations**:
1. **Llama 2/3 7B or 13B** (pre-trained, general purpose)
2. **Mistral 7B** (strong reasoning, efficient)
3. **CodeLlama** (if code understanding needed for schemas)

**Why**: These models are:
- Open-source (offline-capable)
- Support GGUF format
- Good base for domain adaptation
- Reasonable size for deployment

### Fine-Tuning Approach

**Method**: LoRA (Low-Rank Adaptation) or QLoRA (Quantized LoRA)

**Advantages**:
- Efficient (trains only small adapter weights)
- Preserves base model knowledge
- Faster training, less memory
- Can combine multiple adapters (cybersecurity + RansomEye)

**Training Configuration**:
```python
# Pseudo-configuration
training_config = {
    "method": "qlora",
    "base_model": "mistral-7b-v0.1",
    "lora_r": 16,  # Rank
    "lora_alpha": 32,
    "lora_dropout": 0.1,
    "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
    "learning_rate": 2e-4,
    "batch_size": 4,
    "gradient_accumulation": 4,
    "epochs": 3,
    "warmup_steps": 100,
    "max_length": 2048,
    "temperature": 0.0  # Deterministic for production
}
```

### Training Stages

1. **Stage 1 Training**: Cybersecurity domain (large dataset, 3-5 epochs)
2. **Stage 2 Training**: RansomEye-specific (medium dataset, 2-3 epochs)
3. **Stage 3 Training**: Conversational (medium dataset, 2 epochs)
4. **Stage 4 Training**: RAG-optimized (focused dataset, 1-2 epochs)

**Note**: Each stage builds on previous, can be done incrementally.

---

## Evaluation Strategy

### Evaluation Metrics

1. **Domain Knowledge Accuracy**
   - Cybersecurity concept understanding
   - Correctness of security explanations
   - MITRE ATT&CK technique identification

2. **RansomEye Understanding**
   - Component knowledge accuracy
   - Schema understanding
   - Workflow comprehension

3. **Conversational Quality**
   - Natural language fluency
   - Context awareness
   - Multi-turn coherence

4. **RAG Performance**
   - Source citation accuracy
   - Hallucination rate (should be near zero)
   - Response grounding (only uses provided sources)

5. **Structured Response Quality**
   - Format compliance
   - Confidence level accuracy
   - Uncertainty handling

### Evaluation Datasets

1. **Cybersecurity Test Set**: 500 Q&A pairs on security concepts
2. **RansomEye Test Set**: 300 Q&A pairs on platform features
3. **Conversational Test Set**: 200 multi-turn conversations
4. **RAG Test Set**: 200 queries with retrieved context

### Human Evaluation

- SOC analysts rate responses (1-5 scale)
- Accuracy, helpfulness, clarity
- Compare against baseline (pre-trained model)
- Track improvement over training stages

---

## Implementation Considerations

### Training Infrastructure

**Requirements**:
- GPU cluster (A100/H100) for efficient training
- Data storage for training datasets
- Version control for training code and configs
- Experiment tracking (MLflow, Weights & Biases)

**Training Pipeline**:
1. Data preparation and validation
2. Model fine-tuning (staged approach)
3. Evaluation and metrics collection
4. Model conversion to GGUF format
5. Registry registration (via AI Model Registry)
6. Deployment testing

### Model Registry Integration

**Lifecycle Management**:
- Register fine-tuned models in AI Model Registry
- Version control (v1.0, v1.1, etc.)
- Training data provenance tracking
- Model signing and verification
- Promotion workflow (development → staging → production)

### Feedback Loop Integration

**Continuous Improvement**:
- Collect analyst feedback (already implemented)
- Periodically retrain with new feedback
- A/B testing of model versions
- Gradual rollout of improved models

### Deterministic Behavior

**Production Constraints**:
- Temperature = 0.0 (deterministic sampling)
- Fixed random seed
- Same prompt → same response
- No runtime model updates (frozen after training)

---

## Training Data Examples

### Example 1: Cybersecurity Domain

**Input**:
```
Instruction: What is a killchain in cybersecurity?
```

**Output**:
```
A killchain (or cyber kill chain) is a model that describes the stages of a cyberattack from initial reconnaissance to achieving the attacker's objective. The Lockheed Martin kill chain model includes seven stages: Reconnaissance, Weaponization, Delivery, Exploitation, Installation, Command and Control (C2), and Actions on Objectives. Understanding the killchain helps defenders identify where to detect and disrupt attacks. In RansomEye, killchain stages are automatically mapped to MITRE ATT&CK tactics and tracked through the KillChain Forensics module. [Source: Lockheed Martin Cyber Kill Chain, MITRE ATT&CK Framework]
```

### Example 2: RansomEye-Specific

**Input**:
```
Instruction: How does RansomEye detect lateral movement?
```

**Output**:
```
RansomEye detects lateral movement through multiple components: the DPI probe monitors network traffic for suspicious connections, agents track process execution and authentication events, and the Threat Graph correlates entities across hosts. When lateral movement indicators are detected (e.g., RDP/SSH connections between unrelated systems, Pass-the-Hash attempts), events are generated and correlated into incidents. The system maps these to MITRE ATT&CK techniques like T1021 (Remote Services) and T1078 (Valid Accounts). Evidence is stored in the audit ledger and killchain timelines. [Source: RansomEye Threat Graph, DPI Probe, MITRE ATT&CK T1021]
```

### Example 3: Conversational

**Input**:
```
Instruction: I'm seeing a lot of failed login attempts. Should I be worried?
```

**Output**:
```
Failed login attempts can indicate several scenarios: brute force attacks, credential stuffing, or legitimate user errors. In RansomEye, you should check: 1) The incident correlation engine for related incidents, 2) The threat graph for connections between failed logins and other suspicious activity, 3) The risk index to see if risk scores have increased, and 4) The killchain timeline to see if this is part of a larger attack pattern. If failed logins are correlated with other indicators (e.g., unusual process execution, network connections), the risk is higher. Query the SOC Copilot with the specific host or user ID for detailed analysis. [Source: RansomEye Correlation Engine, Threat Graph, Risk Index]
```

### Example 4: RAG-Optimized

**Input** (with context):
```
Query: What is the current stage of incident abc-123?

Available Sources:
Source 1 (incidents): {"incident_id": "abc-123", "current_stage": "PROBABLE", "confidence_score": 65.3}
Source 2 (killchain-events): [{"event_id": "evt-1", "tactic": "Initial Access", "technique": "T1078"}]
```

**Output**:
```
The current stage of incident abc-123 is PROBABLE with a confidence score of 65.3. The killchain timeline shows Initial Access activity using technique T1078 (Valid Accounts). [Source: incidents, killchain-events]
```

---

## Training Schedule & Milestones

### Phase 1: Foundation (Weeks 1-4)
- Collect and prepare cybersecurity training data
- Stage 1 training (cybersecurity domain)
- Evaluation and iteration

### Phase 2: Platform Knowledge (Weeks 5-8)
- Generate RansomEye-specific training data
- Stage 2 training (RansomEye-specific)
- Integration testing with RAG system

### Phase 3: Conversational (Weeks 9-12)
- Create conversational training datasets
- Stage 3 training (conversational)
- Human evaluation and refinement

### Phase 4: RAG Optimization (Weeks 13-14)
- Stage 4 training (RAG-optimized)
- Final evaluation and testing
- Model registry registration

### Phase 5: Deployment (Week 15+)
- Production deployment
- Feedback collection
- Continuous monitoring

---

## Success Criteria

✅ **Cybersecurity Knowledge**: Model correctly answers 90%+ of cybersecurity concept questions

✅ **RansomEye Understanding**: Model accurately explains RansomEye features and workflows

✅ **Conversational Quality**: Analysts rate responses 4+ out of 5 for naturalness and helpfulness

✅ **RAG Performance**: Zero hallucination rate, 100% source citation accuracy

✅ **Production Ready**: Model works offline, deterministic, integrates with existing RAG system

---

## Future Enhancements

- **Continuous Learning**: Periodic retraining with new feedback
- **Specialized Models**: Separate models for different use cases (incident analysis, threat hunting, etc.)
- **Multi-Language Support**: Fine-tune for non-English queries
- **Advanced RAG**: Optimize for more sophisticated retrieval strategies
- **Personalization**: Adapt to individual analyst preferences (future)

---

**AUTHORITATIVE**: This is the single authoritative source for RansomEye SOC Copilot training and fine-tuning strategy.
