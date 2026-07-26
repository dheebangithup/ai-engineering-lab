# Enterprise Knowledge Hub (Production RAG Platform)

A production-grade, highly scalable Retrieval-Augmented Generation (RAG) platform built with FastAPI, PostgreSQL, Qdrant, and LangChain. This platform is designed for enterprise document management, featuring modular ingestion, hybrid search with Reciprocal Rank Fusion (RRF), versioned prompts, automated RAGAS evaluations, and a comprehensive real-time observability telemetry system.

---

## 🏗️ System Architecture

The Enterprise Knowledge Hub divides document processing and retrieval into decoupled, optimized stages:

```
    [ Document Upload / API ]
                │
                ▼
      [ Ingestion Pipeline ]
  (File Hash Verification & Invalidation)
                │
         ┌──────┴──────┐
         ▼             ▼
     [Parser]      [Chunker]
    (Strategy)     (Strategy)
         │             │
         └──────┬──────┘
                ▼
      [Embedding Generator]
                │
         ┌──────┴──────┐
         ▼             ▼
    [PostgreSQL]    [Qdrant]
  (Metadata Store) (Vector Store)
                │
                ▼
      [Retrieval Router]
     (Dense / BM25 / Hybrid)
                │
                ▼
       [Context Builder]
  (Dedup, Merging, Token Budget)
                │
                ▼
     [Prompt Provisioning]
     (Registry Templating)
                │
                ▼
        [LLM Generator]
   (LM Studio / Groq / OpenAI)
                │
                ▼
    [Streaming QA & Citation]
```

---

## 🌟 Key Features

### 1. Scalable Ingestion Studio (Strategy Pattern)
- **Pluggable Architecture**: Implements the Strategy Pattern using a base `DocumentProcessor` class. You can dynamically swap parsing engines (e.g., Unstructured, or integrate **Docling** and **LlamaParse**) and chunking boundaries without modifying the ingestion runner.
- **Incremental Page-Level Invalidation**: Compares new document structures page-by-page against PostgreSQL database hashes. In a content update, it deletes and re-embeds *only* the pages starting from the lowest edited page, saving significant LLM embedding costs.

### 2. Hybrid Retrieval & Search Router
- **Dense Semantic Retrieval**: Computes query embeddings to fetch similar vector records from Qdrant using Cosine similarity.
- **Sparse Keyword Search**: Maintains an in-memory BM25 index generated dynamically from vector payload content.
- **Reciprocal Rank Fusion (RRF)**: Combines dense vector and sparse keyword results, ranking candidates using standard RRF formulas with custom fusion weights:
  $$\text{RRF Score} = \sum_{i \in \text{Runs}} w_i \times \frac{1}{k + \text{Rank}_i}$$

### 3. ContextBuilder Pipeline
- Resolves token budget boundaries before prompting the LLM.
- Supports **Adjacent Chunk Expansion** to pull surrounding text block history for better retrieval context.
- Merges adjacent chunks dynamically if the page gap is narrow, reducing prompt overhead.

### 4. Production Observability & Telemetry
- **Database Telemetry Logging**: Stores query strings, answers, retrieval models, latencies, tokens consumed, and retrieved chunk lists in `telemetry_logs`.
- **Token Cost Tracking**: Dynamically estimates LLM API token execution costs in USD using pricing models for Groq, OpenAI, and Local engines.
- **Prometheus Metrics**: Exposes a `/metrics` scraping endpoint showing request rates, error rates, average latencies, and token costs.
- **Observability Dashboard**: Built-in UI dashboard presenting aggregated metrics cards and detailed query logs.

---

## 🛠️ Technology Stack
- **Web Framework**: FastAPI (Uvicorn ASGI)
- **Database**: PostgreSQL (SQLAlchemy ORM)
- **Vector DB**: Qdrant Vector Store
- **LLM Orchestration**: LangChain (ChatOpenAI, ChatGroq, OpenAIEmbeddings)
- **Document Parsing**: Unstructured Partition Engine
- **Evaluation**: RAGAS Evaluation Suite
- **Aesthetics**: Vanilla CSS, FontAwesome, JetBrains Mono & Inter Google Typography

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure you have the following installed and running locally:
- Python 3.10+
- PostgreSQL Server
- Qdrant Database (running via Docker or Cloud)
- Local LLM Runner (e.g., [LM Studio](https://lmstudio.ai/) running an OpenAI-compatible API endpoint on port `1234`)

### 2. Installation
Clone the repository and install the Python dependencies:
```bash
pip install -r requirments.txt
```

### 3. Environment Variables
Create a `.env` file in the root folder using `.env.example` as a template:
```env
POSTGRES_URL=postgresql://username:password@localhost:5432/knowledge_hub
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=enterprise_hub
LOCAL_LM_URL=http://localhost:1234/v1
LOCAL_LM_EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5-GGUF
GROQ_API_KEY=gsk_your_key_here
```

### 4. Running the Application
Start the FastAPI server:
```powershell
$env:PYTHONPATH="d:\MDM Codes\ai-engineering-lab"
python -m uvicorn knowledge_hub.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000/` in your browser to access the RAG Playground UI.

---

## 📚 Detailed Documentation
Refer to the [docs/README.md](docs/README.md) directory for detailed explanations of each platform layer.
