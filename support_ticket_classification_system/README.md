# 🚀 AI Support Ticket Classification System

An AI-powered classification system that automatically categorizes and routes customer support tickets into structured, actionable insights using Large Language Models (LLMs) with production-grade security guardrails.

---

## 📌 Overview

Customer support teams receive large volumes of unstructured queries from platforms like Zendesk and Gmail. Manually categorizing and routing these tickets is time-consuming, inconsistent, and expensive.

This project solves that problem by building an AI-driven decision system that:

- Classifies support tickets into categories  
- Assigns priority levels  
- Detects sentiment  
- Routes tickets to appropriate teams  
- Produces structured JSON output for downstream automation  

> **Note:** This system currently focuses on a **UI-based demo for portfolio purposes**. The architecture is designed to plug into external source stream applications (Zendesk, Gmail, etc.) but currently processes tickets via direct invocation.

---

## 🧠 Key Features

| Feature | Description |
|:---|:---|
| 🧩 **Structured JSON Output** | LLM output is parsed, cleaned (markdown fences stripped), and returned as strict JSON |
| 🤖 **LLM Classification Engine** | Real LLM calls via NVIDIA NIM endpoints with `ChatNVIDIA` |
| 🛡️ **Validation Layer** | Pydantic-based schema validation ensures all fields conform to expected types and enums |
| ⚠️ **Prompt Injection Protection** | OWASP LLM01-compliant LLM-as-a-Judge guardrail with few-shot detection across 6 attack categories |
| 🔁 **Fallback & Retry Mechanism** | Exponential backoff retry with configurable attempts; safe fallback on exhaustion |
| 💰 **Cost Tracking** | Per-request token usage and estimated USD cost tracking |
| 🔍 **PII Detection** | Regex-based middleware that masks sensitive data (email, phone, SSN, credit card, etc.) before LLM processing and restores it after |
| 📜 **Super Prompt Versioning** | Versioned prompt registry (v1, v2) with runtime selection and environment override |

---

## 🏗️ System Architecture

```
Input Text
    ↓
┌─────────────────────────────┐
│  @pii_middleware             │  ← Masks PII (email, phone, SSN, etc.)
│  @security_guardrails        │  ← LLM-as-a-Judge blocks prompt injection
│  ┌─────────────────────────┐ │
│  │  llm_node               │ │  ← Real LLM classification with retry
│  │  ├─ Prompt Registry     │ │  ← Versioned prompt selection (v1/v2)
│  │  ├─ JSON Parsing        │ │  ← Structured output extraction
│  │  ├─ Pydantic Validation │ │  ← Schema enforcement
│  │  └─ Cost Tracking       │ │  ← Token usage + USD estimation
│  └─────────────────────────┘ │
└─────────────────────────────┘
    ↓
Structured JSON Output + Metadata
```

**Graph Flow:** `START → llm_node → END`

Middleware is applied via Python decorators, keeping the graph topology simple while adding powerful pre/post-processing.

---

## 📤 Example Output

```json
{
  "category": "Technical Support",
  "priority": "High",
  "assigned_team": "Technical Team",
  "sentiment": "Negative",
  "confidence_score": 0.95
}
```

**Full pipeline state includes:**
```
Validated    : True
PII Detected : True
Injection    : False
Prompt Ver   : v2
Retry Count  : 1
Cost         : {prompt_tokens: 254, completion_tokens: 45, estimated_cost_usd: 0.0000389}
```

---

## 📁 Project Structure

```
support_ticket_classification_system/
├── main.py                      # Entry point — runs E2E test suite
├── core/
│   └── config.py                # Environment config (API keys, retry, cost)
├── graph/
│   ├── graph.py                 # LangGraph definition (START → llm_node → END)
│   ├── state.py                 # TicketState TypedDict
│   ├── middleware.py            # @pii_middleware — PII masking/restoring
│   └── guardrails.py           # @security_guardrails — prompt injection detection
├── prompts/
│   └── prompt_registry.py      # Versioned system prompts (v1, v2)
├── schemas/
│   └── ticket_schema.py        # TicketResponse TypedDict
├── services/
│   ├── llm_provider.py         # LLM engine with retry, JSON parsing, cost tracking
│   └── validation.py           # Pydantic-based output validation
└── tests/
    └── test_cases.py           # E2E test suite (safe + malicious inputs)
```

---

## 🕸️ Why LangGraph Instead of LangChain

- **Stateful multi-stage workflow** — not a single LLM call, but an orchestrated pipeline with guardrails, classification, validation, and routing.
- **Middleware-driven architecture** — PII detection and security guardrails are applied as decorators on the graph node, keeping the topology clean.
- **Conditional routing support** — enables dynamic decisions like fallback to human review when confidence is low.
- **Prompt versioning** — different prompt strategies (v1, v2) can be tested within the same workflow.
- **Production-grade reliability** — built-in retry, validation, and controlled execution paths.
- **Observability** — each step can be independently logged and monitored via Python logging.

---

## ⚙️ Tech Stack

- **Python 3.12+**
- **LangGraph** — Graph-based workflow orchestration
- **LangChain** — LLM abstraction layer
- **NVIDIA NIM Endpoints** — LLM inference (`meta/llama-3.1-8b-instruct`)
- **Pydantic** — Output validation and schema enforcement
- **python-dotenv** — Environment configuration

---

## 🚀 Getting Started

### 1. Clone & Install

```bash
git clone https://github.com/your-username/ai-engineering-lab.git
cd ai-engineering-lab
pip install -r support_ticket_classification_system/requirements.txt
```

### 2. Configure Environment

Create a `.env` file inside `support_ticket_classification_system/`:

```env
NVIDIA_API_KEY=your_nvidia_api_key_here
MODEL_NAME=meta/llama-3.1-8b-instruct
DEFAULT_PROMPT_VERSION=v2
RETRY_ATTEMPTS=3
PII_DETECTION_ENABLED=true
```

### 3. Run the System

You can run the system in two modes:

#### Option A: Web UI (Main Entry Point)
This starts the local web server with the HTML interface.
```bash
python -m support_ticket_classification_system.main
```
Access the UI at: **http://localhost:8000**

#### Option B: E2E Test Suite (CLI)
This runs the full automated test suite separately.
```bash
python -m support_ticket_classification_system.tests.run_tests
```

> **Important:** Always run from the `ai-engineering-lab` root directory.

---

## 🔐 Security Architecture

### Prompt Injection Protection (OWASP LLM01:2025)

The system implements an **LLM-as-a-Judge** pattern using a separate lightweight model to evaluate every incoming request before it reaches the classification LLM.

**Attack categories detected:**
- Instruction Override
- Jailbreak / Role-Play (DAN-style)
- System Prompt Extraction
- Data Exfiltration
- Social Engineering
- Encoded / Obfuscated attacks

**Design principles:**
- XML delimiter separation (`<instructions>` / `<user_input>`)
- Instruction hierarchy locking (judge ignores instructions inside user input)
- Few-shot examples across all attack categories
- Fail-closed on errors (blocks by default)

---

## 🎯 Business Impact

- Reduces manual ticket triage effort by 80%+
- Improves response time through automated classification
- Enables scalable support operations
- Cuts operational cost with per-request cost tracking
- Protects against AI-specific attack vectors (prompt injection, PII leakage)

---

## 👤 Author

Dheeban M  
AI Engineer | Backend Systems | Applied AI
