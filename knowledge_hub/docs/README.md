# Enterprise Knowledge Hub - Technical Documentation

Welcome to the technical documentation directory for the Enterprise Knowledge Hub RAG platform. This directory contains detailed guides on the architecture, pipelines, configuration parameters, and production monitoring features of the application.

---

## 📚 Table of Contents

### 1. Ingestion Pipeline & Update Logic
* **[Document Ingestion Flow](ingestion_flow.md)**: Explains the modular Strategy-Pattern parser interface, step-by-step document ingestion stages, and cost-efficient page-level invalidation logic.

### 2. Retrieval, Routing, & Fusion
* **[RAG Retrieval Pipeline](retrieval.md)**: Details Dense, BM25, and Hybrid search options, Reciprocal Rank Fusion (RRF) formula rankings, versioned prompt template provisions, and the ContextBuilder pipeline.

### 3. Production Observability
* **[Observability and Telemetry](observability.md)**: Explains the PostgreSQL telemetry and ingestion run logging schemas, model-based token cost equations, Prometheus `/metrics` scraping, and the monitoring dashboard UI.

### 4. Configuration & Setup
* **[Configuration Guide](configuration.md)**: Explains environment variables (`.env`), LLM/embedding provider configurations (LM Studio, Groq, OpenAI), and retrieval fusion parameters.

### 5. API Reference
* **[Retrieval API Reference](api/retrieval_api_reference.md)**: Detailed JSON payloads and endpoint specifications for search, ingestion, evaluation, and telemetry metrics.
* **[Retrieval API Payloads](api/retrieval_api_payloads.md)**: Input/output example schemas for developers integrating the RAG engine.
