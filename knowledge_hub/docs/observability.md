# Production Observability and Telemetry Framework

This document outlines the telemetry models, cost metrics, Prometheus scrapers, and dashboard interfaces implemented to guarantee production observability.

---

## 1. Database Schema

Production traffic and ingestion logs are persisted to PostgreSQL to allow historical reporting and performance audits.

### A. Search Telemetry Logs Table (`telemetry_logs`)
Stores execution details of search queries and LLM generation calls:

| Column | Type | Description |
| :--- | :--- | :--- |
| `request_id` | UUID (PK) | Unique identifier for each search request. |
| `query` | String | User's natural language input string. |
| `response_answer` | String | Generated LLM answer content. |
| `retrieval_mode` | String | Execution route (`dense`, `bm25`, `hybrid`). |
| `llm_provider` | String | Target LLM provider (e.g. `groq`, `openai`, `lm_studio`). |
| `llm_model` | String | The model name used to generate text. |
| `prompt_tokens` | Integer | Count of input tokens sent in the prompt. |
| `completion_tokens` | Integer | Count of output tokens generated. |
| `total_tokens` | Integer | Total tokens consumed. |
| `cost` | Float | Calculated USD cost based on token usage. |
| `llm_latency_ms` | Float | Duration of the LLM generation call. |
| `embedding_latency_ms` | Float | Duration of the query embedding + search retrieval. |
| `total_latency_ms` | Float | Cumulative RAG pipeline execution latency. |
| `retrieved_chunks` | JSON | List of retrieved chunk IDs, source files, and scores. |
| `status` | String | Run outcome (`SUCCESS` or `FAILED`). |
| `error_message` | String | Error details if the run failed. |
| `created_at` | Timestamp | Telemetry creation date. |

### B. Ingestion Logs Table (`ingestion_logs`)
Stores performance metrics for document uploads and indexing runs:

| Column | Type | Description |
| :--- | :--- | :--- |
| `ingestion_id` | UUID (PK) | Unique ID for each ingestion pipeline execution. |
| `document_id` | UUID | Relational document reference. |
| `file_name` | String | Name of the parsed document. |
| `file_type` | String | Format suffix (`pdf`, `docx`, `md`, `image`). |
| `file_size` | Integer | Calculated file size in bytes. |
| `chunk_count` | Integer | Number of chunks generated. |
| `parsing_time_ms` | Float | Duration of text extraction (OCR / Unstructured). |
| `chunking_time_ms` | Float | Duration of intelligent page hash comparisons. |
| `embedding_time_ms` | Float | Duration of chunk vector generation. |
| `vector_indexing_time_ms`| Float | Duration of Qdrant upserts and BM25 index builds. |
| `total_time_ms` | Float | Total elapsed ingestion pipeline time. |
| `status` | String | Pipeline outcome (`SUCCESS` or `FAILED`). |
| `error_message` | String | Error message if the ingestion failed. |
| `created_at` | Timestamp | Log creation date. |

---

## 2. Token Cost Calculator

The cost of each LLM generation call is calculated using pricing configurations per **1M tokens**:

```
Prompt Cost = (Prompt Tokens / 1,000,000) * Provider Input Rate
Completion Cost = (Completion Tokens / 1,000,000) * Provider Output Rate
Total Cost = Prompt Cost + Completion Cost
```

### Pricing Table Mapped
- **OpenAI**:
  * `gpt-4o`: Input: \$2.50 / 1M | Output: \$10.00 / 1M
  * `gpt-4-turbo`: Input: \$10.00 / 1M | Output: \$30.00 / 1M
- **Groq**:
  * `llama-3.1-8b-instant`: Input: \$0.05 / 1M | Output: \$0.08 / 1M
  * `llama-3.1-70b-versatile`: Input: \$0.59 / 1M | Output: \$0.79 / 1M
- **LM Studio (Local)**:
  * Input: \$0.00 | Output: \$0.00 (Local executions are free)

---

## 3. Prometheus scraping endpoint (`/metrics`)

FastAPI exposes system health and telemetry variables in standard Prometheus formatting at the `/metrics` endpoint:

- **Metrics Output Format**:
  ```text
  # HELP rag_queries_total Total search queries executed
  # TYPE rag_queries_total counter
  rag_queries_total 142
  
  # HELP rag_llm_cost_usd_total Cumulative LLM API token costs in USD
  # TYPE rag_llm_cost_usd_total counter
  rag_llm_cost_usd_total 0.124500
  
  # HELP rag_query_latency_ms_avg Average query execution latency in milliseconds
  # TYPE rag_query_latency_ms_avg gauge
  rag_query_latency_ms_avg 845.20
  ```

---

## 4. Live Observability UI Dashboard

The RAG Web Portal UI provides an **Observability Dashboard** tab to visualize live analytics:

1. **High-Level Statistics Cards**: Shows total queries, cumulative LLM cost in USD, total tokens consumed (with prompt/completion breakdown), and average request latencies.
2. **Ingestion Pipeline Profiles**: Visualizes average parsing, invalidation, embedding, and database indexing times.
3. **Traffic Share**: Summarizes query distribution across Dense, BM25, and Hybrid strategies.
4. **Recent Logs Tables**: Displays detailed telemetry lists for recent search queries and document uploads.
