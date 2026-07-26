# Configuration Guide

This document describes all environment configurations, default settings, and external integrations in the Enterprise Knowledge Hub RAG application.

---

## 1. Environment Variables (`.env` file)

Configuration settings are loaded dynamically using Pydantic Settings from a `.env` file located in the project root:

| Key | Default | Description |
| :--- | :--- | :--- |
| `POSTGRES_URL` | *Required* | Connection string for the PostgreSQL metadata database. |
| `QDRANT_URL` | *Required* | API endpoint for the Qdrant Vector database server. |
| `COLLECTION_NAME` | *Required* | Qdrant vector database storage collection name. |
| `LOCAL_LM_URL` | `http://localhost:1234/v1` | Local LM Studio endpoint address. |
| `LOCAL_LM_API_KEY` | `lm-studio` | Placeholder api key required by LangChain for local calls. |
| `LOCAL_LM_CHAT_MODEL` | *Required* | The name of the GGUF model loaded in LM Studio. |
| `LOCAL_LM_TEMPERATURE`| `0.7` | Temperature variance for local completions. |
| `GROQ_API_KEY` | *Optional* | API key for external Groq completions. |
| `GROQ_VISION_MODEL` | `llama-3.1-8b-instant` | Default vision-capable model name for Groq. |
| `LLM_PROVIDER` | `lm_studio` | Primary LLM Provider (`lm_studio`, `groq`, `openai`). |
| `LLM_MODEL` | *Required* | Primary LLM model identifier. |
| `MAX_CONTEXT_TOKENS` | `6000` | Maximum size of ContextBuilder context in tokens. |
| `DEFAULT_TOP_K` | `5` | Default number of candidate chunks to retrieve. |
| `DEFAULT_RETRIEVAL_MODE`| `dense` | Default retrieval strategy (`dense`, `bm25`, `hybrid`). |
| `ENABLE_BM25_INDEX_ON_STARTUP` | `True` | Rebuilds the BM25 index from Qdrant payloads on app startup. |

---

## 2. LLM and Embedding Providers

The application supports pluggable LLM backends via LangChain:

### A. LM Studio (Local Run)
- **Settings**: Set `LLM_PROVIDER=lm_studio` and point `LOCAL_LM_URL` to your running LM Studio instance (usually `http://localhost:1234/v1`).
- **Embedding**: Local embedding models (like `nomic-embed-text`) are queried via LM Studio OpenAI-compatible endpoints.

### B. Groq Cloud (API Run)
- **Settings**: Set `LLM_PROVIDER=groq` and supply a valid `GROQ_API_KEY` in your `.env`.
- **Vision Summaries**: When enabling vision model summary during ingestion, the application invokes Groq's vision models (`llama-3.1-8b-instant`) to describe images and tables parsed from documents.

### C. OpenAI (Cloud Run)
- **Settings**: Set `LLM_PROVIDER=openai` and supply `OPENAI_API_KEY` in your environment.

---

## 3. Retrieval Parameters

You can adjust retrieval performance and fusion balances in `.env` or in the RAG Playground UI:

- **Score Threshold**: Chunks with vector similarity scores below this threshold are discarded.
- **Hybrid Fusion Weights**:
  - `bm25_weight`: Relative weight of keyword search in Reciprocal Rank Fusion (RRF).
  - `dense_weight`: Relative weight of semantic vector similarity.
  - *Constraint*: `bm25_weight + dense_weight` should sum to `1.0`.
