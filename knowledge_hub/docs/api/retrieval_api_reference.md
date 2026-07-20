# Knowledge Hub — Retrieval & ContextBuilder API Reference Specification

**Endpoint**: `POST /api/v1/search`  
**Content-Type**: `application/json`  
**Description**: Performs vector similarity search, processes chunks through the 6-stage enterprise `ContextBuilder` pipeline, and provisions versioned prompt templates.

---

## 1. Request Payload Schema (`SearchRequest`)

### A. Root Search Parameters

#### 1. `query`
- **Type**: `string` (Required)
- **Description**: Natural language question or search query used to generate vector embeddings.
- **Example**: `"What is Multi-Head Attention in the Transformer paper?"`
- **Usecase**: Drives semantic vector similarity retrieval in Qdrant.

#### 2. `top_k`
- **Type**: `integer` (Optional, Default: `5`, Min: `1`, Max: `100`)
- **Description**: Maximum number of nearest-neighbor vector chunks to retrieve from the vector database.
- **Example**: `10`
- **Usecase**: Increase for high-recall tasks (e.g. multi-document synthesis) or decrease for narrow factual Q&A.
- **Combination & Relationship**: 
  > 💡 **Combination Rule**: `top_k` feeds candidates into Stage 1 of the `ContextBuilder` pipeline (`input_count`). If `top_k` is too low (e.g., `2`), later pipeline stages like `ChunkMerger` or `AdjacentChunkExpander` have fewer candidates to process.

#### 3. `score_threshold`
- **Type**: `float` (Optional, Default: `0.7`, Min: `0.0`, Max: `1.0`)
- **Description**: Minimum similarity score threshold for initial vector retrieval filter.
- **Example**: `0.5`
- **Usecase**: Drops low-relevance candidates early to prevent noisy context.
- **Combination & Relationship**:
  > 💡 **Combination Rule**: If `context_builder.min_score_threshold` is omitted, `RetrievalService` automatically populates it using this root `score_threshold`.

#### 4. `max_context_tokens`
- **Type**: `integer` (Optional, Default: `6000`, Min: `100`)
- **Description**: Maximum token budget allowed for the built context string.
- **Example**: `4096`
- **Usecase**: Prevents context overflow when calling downstream LLMs (e.g. GPT-4, Claude).
- **Combination & Relationship**:
  > 💡 **Precedence & Fallback Rule**: If `context_builder.max_context_tokens` is provided inside the nested object, it **overrides** this root-level `max_context_tokens`. Root `max_context_tokens` acts as a convenient shorthand for simple requests without a nested `context_builder` object.

#### 5. `filters`
- **Type**: `object` / `dictionary` (Optional, Default: `null`)
- **Description**: Key-value pairs for metadata filtering in Qdrant (e.g., filtering by file name or document ID).
- **Example**: `{"file_name": "attention-is-all-you-need-paper.pdf"}`
- **Usecase**: Restricts retrieval scope to a specific document or folder.

#### 6. `prompt_name`
- **Type**: `string` (Optional, Default: `null`)
- **Description**: Registered prompt template identifier in `PromptRegistry`.
- **Example**: `"rag_qa"`
- **Usecase**: Triggers automatic prompt provisioning, assembling system & user prompts with injected context.
- **Combination & Relationship**:
  > 💡 **Dependency Rule**: Must match a name registered in `PromptRegistry` (e.g., `"rag_qa"`). If `prompt_name` is provided, `rendered_prompt` will be generated in the response. If `null`, `rendered_prompt` will be `null`.

#### 7. `prompt_version`
- **Type**: `string` (Optional, Default: `null`)
- **Description**: Explicit prompt template version tag.
- **Example**: `"v1.1.0"`
- **Usecase**: Pin requests to specific prompt versions (`"v1.0.0"` vs `"v1.1.0"`) to guarantee reproducible outputs.
- **Combination & Relationship**:
  > 💡 **Dependency Rule**: Requires `prompt_name` to be set. If `prompt_version` is omitted while `prompt_name` is set, `PromptRegistry` automatically defaults to the registered **active version** (e.g., `"v1.1.0"`).

#### 8. `additional_prompt_vars`
- **Type**: `object` / `dictionary` (Optional, Default: `null`)
- **Description**: Key-value dictionary of extra variables required by custom prompt templates.
- **Example**: `{"user_role": "Senior Engineer", "language": "English"}`
- **Usecase**: Supplies dynamic variables beyond `{context}` and `{query}` to prompt templates.
- **Combination & Relationship**:
  > 💡 **Dependency Rule**: These variables are merged into the prompt template rendering context alongside auto-injected `"context"` and `"query"`.

#### 9. `enable_llm_generation`
- **Type**: `boolean` (Optional, Default: `false`)
- **Description**: Controls whether to trigger LLM text generation via LangChain `ChatOpenAI` targeting local LM Studio.
- **Example**: `true`
- **Usecase**: When set to `true`, the system automatically provisions the prompt and executes `qwen2.5-7b-instruct-1m:3` to generate the final grounded response.

#### 10. `temperature`
- **Type**: `float` (Optional, Default: `null`, Min: `0.0`, Max: `2.0`)
- **Description**: Optional sampling temperature override for LLM generation.
- **Example**: `0.7`
- **Usecase**: Use lower values (e.g. `0.2`) for factual/strict Q&A, higher values (e.g. `0.8`) for creative summary generation.

#### 11. `context_builder`
- **Type**: `object` (`ContextBuilderConfig`) (Optional, Default: `null`)
- **Description**: Fine-grained configuration overrides for the 6-stage pipeline.
- **Example**: `{ "sort_strategy": "hybrid", "enable_chunk_merging": true }`
- **Usecase**: Fully controls deduplication, sorting, neighbor expansion, merging, budgeting, and formatting.

---

### B. `context_builder` Nested Configuration (`ContextBuilderConfig`)

#### 10. `context_builder.max_context_tokens`
- **Type**: `integer` (Optional, Default: `6000`, Min: `100`)
- **Description**: Token budget enforced by `TokenBudgetManager` (Stage 5).
- **Example**: `2048`
- **Usecase**: Restricts LLM prompt token consumption.
- **Combination & Relationship**: Overrides root-level `max_context_tokens`.

#### 11. `context_builder.sort_strategy`
- **Type**: `string` (`"score_desc"` | `"document_order"` | `"hybrid"`) (Optional, Default: `"score_desc"`)
- **Description**: Ordering strategy applied in Stage 2 (`ChunkSorter`).
  - `"score_desc"`: Highest relevance score first (standard RAG).
  - `"document_order"`: Natural reading order (`page_number ASC`, `chunk_index ASC`).
  - `"hybrid"`: Rank document groups by top score, then preserve internal document reading order.
- **Example**: `"hybrid"`
- **Usecase**: Use `"document_order"` for long-document summarization, `"score_desc"` for multi-document Q&A.

#### 12. `context_builder.enable_adjacent_expansion`
- **Type**: `boolean` (Optional, Default: `false`)
- **Description**: Master toggle for Stage 3 (`AdjacentChunkExpander`).
- **Example**: `true`
- **Usecase**: Expands retrieved chunks by fetching preceding/following neighbor chunks for richer context continuity.
- **Combination & Relationship**:
  > 💡 **Dependency Rule**: Must be set to `true` for `adjacency_window` to take effect.

#### 13. `context_builder.adjacency_window`
- **Type**: `integer` (Optional, Default: `1`, Min: `1`)
- **Description**: Number of neighboring chunks (±N) to fetch for each chunk.
- **Example**: `2` (fetches chunk index `i-2`, `i-1`, `i`, `i+1`, `i+2`).
- **Usecase**: Preserves paragraph continuity across split boundaries.
- **Combination & Relationship**: Requires `enable_adjacent_expansion: true`.

#### 14. `context_builder.enable_chunk_merging`
- **Type**: `boolean` (Optional, Default: `true`)
- **Description**: Master toggle for Stage 4 (`ChunkMerger`).
- **Example**: `true`
- **Usecase**: Combines consecutive chunks from the same document/page into single logical blocks.
- **Combination & Relationship**:
  > 💡 **Dependency Rule**: Must be `true` for `max_merge_gap` to take effect. Merging reduces chunk fragmentation and citation clutter.

#### 15. `context_builder.max_merge_gap`
- **Type**: `integer` (Optional, Default: `1`, Min: `1`)
- **Description**: Maximum `chunk_index` gap allowed between consecutive chunks to merge them.
- **Example**: `1` (merges chunk `#10` and `#11`).
- **Usecase**: Controls how aggressively adjacent chunks are combined.
- **Combination & Relationship**: Requires `enable_chunk_merging: true`.

#### 16. `context_builder.include_source_header`
- **Type**: `boolean` (Optional, Default: `true`)
- **Description**: Toggles citation header prepending in Stage 6 (`PromptFormatter`).
- **Example**: `true`
- **Usecase**: Enables source traceability in LLM responses.
- **Combination & Relationship**:
  > 💡 **Dependency Rule**: Must be `true` for `source_header_template` to be formatted into the context.

#### 17. `context_builder.source_header_template`
- **Type**: `string` (Optional, Default: `"[Source: {file_name} | Page {page_number} | Chunk #{chunk_index}]"`)
- **Description**: Python template format string for source citation headers.
- **Example**: `"[Doc: {file_name} (Page {page_number})]" `
- **Usecase**: Customizes citation format for custom LLM prompts.
- **Combination & Relationship**: Requires `include_source_header: true`. Placeholders `{file_name}`, `{page_number}`, `{chunk_index}` are dynamically populated.

#### 18. `context_builder.include_chunk_separator`
- **Type**: `boolean` (Optional, Default: `true`)
- **Description**: Toggles block separators between chunks in Stage 6 (`PromptFormatter`).
- **Example**: `true`
- **Usecase**: Separates chunk blocks visually for clearer LLM parsing.
- **Combination & Relationship**:
  > 💡 **Dependency Rule**: Must be `true` for `chunk_separator` to be inserted between blocks.

#### 19. `context_builder.chunk_separator`
- **Type**: `string` (Optional, Default: `"\n\n---\n\n"`)
- **Description**: Delimiter string placed between formatted chunk blocks.
- **Example**: `"\n\n=== CHUNK END ===\n\n"`
- **Usecase**: Defines visual boundary between context blocks.
- **Combination & Relationship**: Requires `include_chunk_separator: true`.

#### 20. `context_builder.min_score_threshold`
- **Type**: `float` (Optional, Default: `0.7`, Min: `0.0`, Max: `1.0`)
- **Description**: Pre-pipeline filter score threshold.
- **Example**: `0.6`
- **Usecase**: Filters out low-relevance vector hits before pipeline Stage 1.

---

## 2. Response Payload Schema (`ApiResponse[RetrievalResult]`)

### A. Root Response Structure

```json
{
  "success": true,
  "message": "success",
  "error_code": null,
  "data": { ... }
}
```

#### 1. `success`
- **Type**: `boolean`
- **Description**: `true` if search and context assembly succeeded, `false` otherwise.
- **Example**: `true`

#### 2. `message`
- **Type**: `string`
- **Description**: Human-readable status message or error detail.
- **Example**: `"success"` or `"No matching documents found"`

#### 3. `error_code`
- **Type**: `integer` / `null`
- **Description**: HTTP status code or domain error code if `success` is `false`.
- **Example**: `null` (or `400` on validation failure)

#### 4. `data`
- **Type**: `object` (`RetrievalResult`) / `null`
- **Description**: Container holding vector search results, built context, and rendered prompt.

---

### B. `data.search_response` (Raw Vector Hits)

#### 5. `data.search_response.results`
- **Type**: `array` of `SearchResult` objects
- **Description**: Direct raw ranked outputs from Qdrant vector store before pipeline post-processing.

#### 6. `data.search_response.results[].score`
- **Type**: `float`
- **Description**: Cosine similarity score (0.0 to 1.0) between query embedding and chunk vector.
- **Example**: `0.8954`

#### 7. `data.search_response.results[].document` (`ChunkPayload`)
- **Type**: `object`
- **Description**: Full chunk payload stored in Qdrant.
  - `document_id` (`string`): Parent document UUID. Example: `"c1f2e3d4-..."`
  - `chunk_id` (`string`): Unique chunk UUID. Example: `"a9b8c7d6-..."`
  - `page_number` (`integer`): Document page number. Example: `4`
  - `source` (`string`): Full file path. Example: `"data/attention.pdf"`
  - `file_name` (`string`): Base file name. Example: `"attention.pdf"`
  - `content` (`string`): Raw text content of chunk.
  - `doc_version` (`string`): Ingestion version tag. Example: `"1.0.0"`
  - `chuk_index` (`integer`): Zero-based sequential chunk index in document. Example: `12`

---

### C. `data.built_context` (Assembled Context & Audit Metrics)

#### 8. `data.built_context.context_str`
- **Type**: `string`
- **Description**: Final formatted context ready to be injected into an LLM prompt template.
- **Example**: `"[Source: attention.pdf | Page 4 | Chunk #12]\nMulti-Head Attention allows..."`

#### 9. `data.built_context.sources`
- **Type**: `array` of `SourceCitation` objects
- **Description**: Structured list of citations retained in the final built context.
  - `file_name` (`string`): `"attention.pdf"`
  - `source` (`string`): `"data/attention.pdf"`
  - `page_number` (`integer`): `4`
  - `chunk_index` (`integer`): `12`
  - `score` (`float`): `0.8954`

#### 10. `data.built_context.token_count`
- **Type**: `integer`
- **Description**: Total estimated tokens in `context_str`.
- **Example**: `342`

#### 11. `data.built_context.chunk_count`
- **Type**: `integer`
- **Description**: Total number of chunk blocks retained in final context.
- **Example**: `1`

#### 12. `data.built_context.pipeline_stats` (Observability Funnel)
- **Type**: `object`
- **Description**: Per-stage chunk counters and execution latency metrics in milliseconds.

| Field | Type | Description |
|---|---|---|
| `input_count` | `integer` | Raw chunks returned by Qdrant vector search. |
| `below_threshold_dropped` | `integer` | Chunks dropped by `min_score_threshold`. |
| `after_dedup` | `integer` | Chunks remaining after Stage 1 Deduplication. |
| `dedup_ms` | `float` | Execution time for Stage 1 in milliseconds. |
| `after_sort` | `integer` | Chunks remaining after Stage 2 Sorting. |
| `sort_ms` | `float` | Execution time for Stage 2 in milliseconds. |
| `after_expansion` | `integer` | Chunks remaining after Stage 3 Expansion. |
| `expansion_ms` | `float` | Execution time for Stage 3 in milliseconds. |
| `after_merge` | `integer` | Chunk blocks remaining after Stage 4 Merging. |
| `merge_ms` | `float` | Execution time for Stage 4 in milliseconds. |
| `after_budget` | `integer` | Chunk blocks remaining after Stage 5 Token Budgeting. |
| `budget_ms` | `float` | Execution time for Stage 5 in milliseconds. |
| `format_ms` | `float` | Execution time for Stage 6 Formatting in milliseconds. |
| `total_pipeline_ms` | `float` | Total pipeline execution time in milliseconds. |

---

### D. `data.rendered_prompt` (Versioned Prompt Provisioning Output)

#### 13. `data.rendered_prompt.system_prompt`
- **Type**: `string`
- **Description**: Fully rendered system instructions for the LLM client.
- **Example**: `"You are an enterprise AI assistant... Rely ONLY on the context provided below."`

#### 14. `data.rendered_prompt.user_prompt`
- **Type**: `string`
- **Description**: Fully rendered user message containing injected `context_str` and user `query`.
- **Example**: `"Retrieved Context:\n...\n\nQuestion: What is Multi-Head Attention?"`

#### 15. `data.rendered_prompt.prompt_name`
- **Type**: `string`
- **Description**: Name of prompt template used. Example: `"rag_qa"`.

#### 16. `data.rendered_prompt.version`
- **Type**: `string`
- **Description**: Resolved version string of prompt template used. Example: `"v1.1.0"`.

#### 17. `data.rendered_prompt.variables_used`
- **Type**: `object` / `dictionary`
- **Description**: Complete dictionary of key-value variables passed during template rendering (`context`, `query`, plus `additional_prompt_vars`).

---

### E. `data.llm_response` (LLM Generation Output)

#### 18. `data.llm_response.answer`
- **Type**: `string`
- **Description**: Grounded response generated by LangChain `ChatOpenAI` calling the LLM.
- **Example**: `"Multi-Head Attention projects queries, keys, and values into multiple representation subspaces..."`

#### 19. `data.llm_response.model_name`
- **Type**: `string`
- **Description**: Model identifier used for generation. Example: `"qwen2.5-7b-instruct-1m:3"`.

#### 20. `data.llm_response.latency_ms`
- **Type**: `float`
- **Description**: Total LLM invocation latency in milliseconds. Example: `1420.50`.

#### 21. `data.llm_response.usage`
- **Type**: `object` / `null`
- **Description**: Token usage metadata dictionary returned by the model.

---

## 3. Complete End-to-End Request & Response Example

### Request

```json
{
  "query": "What is Multi-Head Attention and why is scaled dot-product attention used?",
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

### Response

```json
{
  "success": true,
  "message": "success",
  "error_code": null,
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
            "content": "Multi-Head Attention allows the model to jointly attend to information from different representation subspaces...",
            "doc_version": "1.0.0",
            "chuk_index": 12
          },
          "score": 0.8954
        }
      ]
    },
    "built_context": {
      "context_str": "[Source: attention-is-all-you-need-paper.pdf | Page 4 | Chunk #12]\nMulti-Head Attention allows the model to jointly attend to information from different representation subspaces...",
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
        "below_threshold_dropped": 0,
        "after_dedup": 1,
        "dedup_ms": 0.52,
        "after_sort": 1,
        "sort_ms": 0.04,
        "after_expansion": 1,
        "expansion_ms": 0.0,
        "after_merge": 1,
        "merge_ms": 0.07,
        "after_budget": 1,
        "budget_ms": 0.03,
        "format_ms": 0.01,
        "total_pipeline_ms": 0.67
      }
    },
    "rendered_prompt": {
      "system_prompt": "You are an enterprise AI assistant for Knowledge Hub.\nYour goal is to provide comprehensive, factual, and strictly grounded answers.\n\nGuidelines:\n1. Rely ONLY on the context provided below.\n2. When stating facts, cite the source file and page number formatted as [Source: <filename> | Page <page>] when available.\n3. If the context does not provide sufficient detail, explicitly state what is missing.\n4. Keep your answer clear, professional, and well-structured using markdown.",
      "user_prompt": "Retrieved Context:\n===================\n[Source: attention-is-all-you-need-paper.pdf | Page 4 | Chunk #12]\nMulti-Head Attention allows the model to jointly attend to information from different representation subspaces...\n===================\n\nQuestion: What is Multi-Head Attention and why is scaled dot-product attention used?\n\nStructured Answer (with inline citations):",
      "prompt_name": "rag_qa",
      "version": "v1.1.0",
      "variables_used": {
        "context": "[Source: attention-is-all-you-need-paper.pdf | Page 4 | Chunk #12]\nMulti-Head Attention allows the model to jointly attend to information from different representation subspaces...",
        "query": "What is Multi-Head Attention and why is scaled dot-product attention used?"
      }
    }
  }
}
```
