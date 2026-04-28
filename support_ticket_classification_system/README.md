# 🚀 AI Support Ticket Classification System

An AI-powered backend system that automatically classifies and routes customer support tickets from multiple channels into structured, actionable insights using Large Language Models (LLMs).

---

## 📌 Overview

Customer support teams receive large volumes of unstructured queries from platforms like Zendesk and Gmail. Manually categorizing and routing these tickets is time-consuming, inconsistent, and expensive.

This project solves that problem by building an AI-driven decision system that:

- Classifies support tickets into categories  
- Assigns priority levels  
- Detects sentiment  
- Routes tickets to appropriate teams  
- Produces structured JSON output for downstream automation  

---

## 🧠 Key Features

- 🧩 Structured JSON Output  
- 🤖 LLM-Based Classification Engine  
- 🛡️ Validation Layer  
- ⚠️ Prompt Injection Protection  
- 🔁 Fallback & Retry Mechanism  
- 💰 Cost Tracking  
- 🔍 PII Detection (Optional)  
- 📜 Super Prompt Versioning

---

## 🏗️ System Architecture

Input (Zendesk / Gmail/ UI)
        ↓
Preprocessing Layer
        ↓
LLM Classification Engine
        ↓
Validation Layer
        ↓
Structured JSON Output
        ↓
Routing / Automation System

---

## 📤 Example Output

```json
{
  "category": "Payment Issue",
  "priority": "High",
  "assigned_team": "Billing",
  "sentiment": "Negative",
  "confidence_score": 0.92
}
```

---

## 🕸️ Why We Used LangGraph Instead of LangChain

- **Designed the system as a multi-stage AI workflow** (not a single LLM call), requiring structured orchestration across multiple steps such as guardrails, classification, validation, and routing.
- **Leveraged stateful execution** to maintain and update shared context (e.g., prompt version, confidence score, classification output) across all stages of the pipeline.
- **Implemented conditional routing logic**, enabling dynamic decisions such as fallback to human review when confidence scores fall below a threshold.
- **Built modular processing nodes** (PII detection, prompt injection guard, LLM inference, validation), improving system clarity, reusability, and maintainability.
- **Enabled clear separation of concerns**, where each node handles a single responsibility, aligning with clean architecture principles.
- **Supported prompt versioning and experimentation**, allowing different prompt strategies (v1, v2) to be tested and evaluated within the same workflow.
- **Integrated guardrails** (PII detection + prompt injection handling) as first-class workflow steps rather than ad-hoc checks.
- **Designed for production-grade reliability**, with support for retries, validation layers, and controlled execution paths.
- **Improved observability and debugging**, as each step in the workflow can be independently logged and monitored.
- **Avoided tightly coupled, sequential code** by modeling the system as a graph-based execution pipeline, making it easier to extend and scale.

### 🚀 Summary

LangGraph was chosen to model the ticket classification system as a stateful, multi-step AI workflow with guardrails, validation, and conditional routing, enabling a more scalable and production-ready architecture compared to traditional linear LLM pipelines.

---

## ⚙️ Tech Stack

- Python (FastAPI)
- LangGraph & LangChain
- NVIDIA AI Endpoints (LLMs)
- Pydantic (Validation)
- REST APIs

---

## 🚀 Getting Started

```bash
git clone https://github.com/your-username/ai-ticket-classifier.git
cd ai-ticket-classifier
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 📡 API Example

POST /classify-ticket

Request:
```json
{
  "text": "I was charged twice for my order. Please refund."
}
```

Response:
```json
{
  "category": "Billing",
  "priority": "High",
  "assigned_team": "Finance",
  "sentiment": "Negative",
  "confidence_score": 0.95
}
```

---

## 🎯 Business Impact

- Reduces manual effort  
- Improves response time  
- Enables scalable support  
- Cuts operational cost  

---

## 👤 Author

Dheeban M  
AI Engineer | Backend Systems | Applied AI
