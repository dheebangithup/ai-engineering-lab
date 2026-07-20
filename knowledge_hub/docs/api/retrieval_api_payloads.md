# Knowledge Hub — Retrieval & Context Builder API Documentation

## Endpoint Overview

- **Endpoint**: `POST /api/v1/search`
- **Content-Type**: `application/json`
- **Description**: Performs vector similarity retrieval, runs results through the 6-stage enterprise `ContextBuilder` pipeline, and optionally provisions versioned prompt templates.

---

## Request Schema Parameters

### 1. Root Search Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | `string` | **Yes** | — | Natural language search query. |
| `top_k` | `integer` | No | `5` | Number of nearest vector candidates to retrieve (1–100). |
| `score_threshold` | `float` | No | `0.7` | Minimum vector similarity score threshold (0.0–1.0). |
| `max_context_tokens` | `integer` | No | `6000` | Maximum token budget for assembled context. |
| `filters` | `object` | No | `null` | Key-value dictionary for metadata filtering. |
| `context_builder` | `object` | No | `null` | Dynamic overrides for the `ContextBuilderConfig` pipeline. |
| `prompt_name` | `string` | No | `null` | Registered prompt template identifier (e.g., `"rag_qa"`). |
| `prompt_version` | `string` | No | `null` | Version of prompt template (e.g., `"v1.1.0"`, `"v1.0.0"`). Defaults to active version. |
| `additional_prompt_vars`| `object` | No | `null` | Additional custom variables for prompt rendering. |

---

### 2. `context_builder` Override Parameters (`ContextBuilderConfig`)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `max_context_tokens` | `integer` | `6000` | Token budget enforced by `TokenBudgetManager`. |
| `sort_strategy` | `string` | `"score_desc"` | Ordering strategy: `"score_desc"`, `"document_order"`, or `"hybrid"`. |
| `enable_adjacent_expansion` | `boolean` | `false` | Expand retrieved chunks with ±N neighbour chunks. |
| `adjacency_window` | `integer` | `1` | Expansion window size. |
| `enable_chunk_merging` | `boolean` | `true` | Merge consecutive same-document/page chunks. |
| `max_merge_gap` | `integer` | `1` | Maximum chunk index gap allowed for merging. |
| `include_source_header` | `boolean` | `true` | Prepend source metadata citation header to chunk blocks. |
| `include_chunk_separator` | `boolean` | `true` | Insert separators between formatted context blocks. |
| `chunk_separator` | `string` | `"\n\n---\n\n"` | Separator string between blocks. |
| `source_header_template` | `string` | `"[Source: {file_name} \| Page {page_number} \| Chunk #{chunk_index}]"` | Citation header template string. |
| `min_score_threshold` | `float` | `0.7` | Pre-pipeline filtering score threshold. |

---

## Sample Request Payloads

### Sample 1: Full API Control Payload (Attention Is All You Need Search)

```json
{
  "query": "What is Multi-Head Attention and why is scaled dot-product attention used in the Transformer model?",
  "top_k": 10,
  "score_threshold": 0.5,
  "max_context_tokens": 4096,
  "prompt_name": "rag_qa",
  "prompt_version": "v1.1.0",
  "context_builder": {
    "max_context_tokens": 4096,
    "sort_strategy": "hybrid",
    "enable_adjacent_expansion": false,
    "adjacency_window": 1,
    "enable_chunk_merging": true,
    "max_merge_gap": 1,
    "include_source_header": true,
    "include_chunk_separator": true,
    "chunk_separator": "\n\n---\n\n",
    "source_header_template": "[Source: {file_name} | Page {page_number} | Chunk #{chunk_index}]",
    "min_score_threshold": 0.5
  }
}
```

---

### Sample 2: Document Reading Order & Citation Prompting Payload

```json
{
  "query": "Summarize the positional encoding mechanism in Attention Is All You Need",
  "top_k": 8,
  "prompt_name": "rag_qa",
  "prompt_version": "v1.1.0",
  "context_builder": {
    "sort_strategy": "document_order",
    "enable_chunk_merging": true,
    "max_context_tokens": 3000
  }
}
```

---

### Sample 3: Minimal Retrieval Payload (System Defaults)

```json
{
  "query": "How many attention heads are used in the base Transformer model?",
  "top_k": 5
}
```

---

## Sample Response Payload (`ApiResponse[RetrievalResult]`)

```json
{
  "success": true,
  "message": "success",
  "data": {
    "search_response": {
      "results": [
        {
          "document": {
            "document_id": "c1f2e3d4-5678-90ab-cdef-1234567890ab",
            "chunk_id": "a9b8c7d6-e5f4-3210-fedc-ba9876543210",
            "page_number": 4,
            "source": "knowledge_hub/data/attention-is-all-you-need-paper.pdf",
            "file_name": "attention-is-all-you-need-paper.pdf",
            "content": "Multi-Head Attention allows the model to jointly attend to information from different representation subspaces at different positions...",
            "doc_version": "1.0.0",
            "chuk_index": 12
          },
          "score": 0.8954
        }
      ]
    },
    "built_context": {
      "context_str": "[Source: attention-is-all-you-need-paper.pdf | Page 4 | Chunk #12]\nMulti-Head Attention allows the model to jointly attend to information from different representation subspaces at different positions...",
      "sources": [
        {
          "file_name": "attention-is-all-you-need-paper.pdf",
          "source": "knowledge_hub/data/attention-is-all-you-need-paper.pdf",
          "page_number": 4,
          "chunk_index": 12,
          "score": 0.8954
        }
      ],
      "token_count": 342,
      "chunk_count": 1,
      "pipeline_stats": {
        "input_count": 1,
        "after_dedup": 1,
        "after_sort": 1,
        "after_expansion": 1,
        "after_merge": 1,
        "after_budget": 1,
        "token_count": 342,
        "total_pipeline_ms": 3.45
      }
    },
    "rendered_prompt": {
      "system_prompt": "You are an enterprise AI assistant for Knowledge Hub.\nYour goal is to provide comprehensive, factual, and strictly grounded answers.\n\nGuidelines:\n1. Rely ONLY on the context provided below.\n2. When stating facts, cite the source file and page number formatted as [Source: <filename> | Page <page>] when available.\n3. If the context does not provide sufficient detail, explicitly state what is missing.\n4. Keep your answer clear, professional, and well-structured using markdown.",
      "user_prompt": "Retrieved Context:\n===================\n[Source: attention-is-all-you-need-paper.pdf | Page 4 | Chunk #12]\nMulti-Head Attention allows the model to jointly attend to information from different representation subspaces at different positions...\n===================\n\nQuestion: What is Multi-Head Attention and why is scaled dot-product attention used in the Transformer model?\n\nStructured Answer (with inline citations):",
      "prompt_name": "rag_qa",
      "version": "v1.1.0",
      "variables_used": {
        "context": "[Source: attention-is-all-you-need-paper.pdf | Page 4 | Chunk #12]\nMulti-Head Attention allows the model to jointly attend to information from different representation subspaces at different positions...",
        "query": "What is Multi-Head Attention and why is scaled dot-product attention used in the Transformer model?"
      }
    }
  },
  "error_code": null
}
```

---

## Integration Examples

### cURL

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Explain Scaled Dot-Product Attention in the Transformer paper",
       "top_k": 5,
       "prompt_name": "rag_qa",
       "prompt_version": "v1.1.0",
       "context_builder": {
         "sort_strategy": "score_desc",
         "enable_chunk_merging": true,
         "max_context_tokens": 4096
       }
     }'
```

### Python (`requests`)

```python
import requests

url = "http://localhost:8000/api/v1/search"
payload = {
    "query": "What is Multi-Head Attention?",
    "top_k": 5,
    "prompt_name": "rag_qa",
    "prompt_version": "v1.1.0",
    "context_builder": {
        "sort_strategy": "hybrid",
        "enable_chunk_merging": True,
        "max_context_tokens": 4096
    }
}

response = requests.post(url, json=payload)
data = response.json()

if data["success"]:
    context = data["data"]["built_context"]["context_str"]
    prompt = data["data"]["rendered_prompt"]
    print("Assembled Context:\n", context)
    print("System Prompt:\n", prompt["system_prompt"])
    print("User Prompt:\n", prompt["user_prompt"])
```
