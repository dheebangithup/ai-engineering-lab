# RAG Retrieval and Search Pipeline

This document details the retrieval strategies, fusion algorithms, versioned prompt template binding, and the context-building engine implemented in the platform.

---

## 1. Retrieval Router Modes

The platform supports three distinct search strategies configured on a per-request basis:

```
                            [ User Query ]
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
                [ DENSE ]       [ BM25 ]      [ HYBRID ]
               Vector Space    Keyword Match    Combined
             Cosine Similarity   TF-IDF Sparse   Dense + BM25
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
                            [ Fusion/RRF ]
                                   │
                                   ▼
                           [ ContextBuilder ]
                                   │
                                   ▼
                             [ Prompt Reg ]
                                   │
                                   ▼
                            [ LLM Generation ]
```

### A. Dense Retrieval (Semantic Search)
- **Method**: Computes semantic embedding vector for the user query text using the configured model.
- **Backend**: Executes a vector similarity search (using cosine distance) against Qdrant collection payloads.
- **Strength**: Captures semantic intent, synonyms, and multi-media summaries, bypassing keyword limitations.

### B. Sparse Retrieval (BM25 Keyword Search)
- **Method**: Tokenizes the query and evaluates term frequency/inverse document frequency scores against documents.
- **Backend**: Uses an in-memory `BM25Okapi` index rebuilt from scroll vector payloads.
- **Strength**: Captures exact serial numbers, product IDs, spelling variations, and specific technical phrases.

### C. Hybrid Search (Dense + BM25 Fusion)
- Combines candidate lists fetched from both dense and sparse retrieval engines to provide balanced keyword-semantic matching.

---

## 2. Reciprocal Rank Fusion (RRF)

To merge candidate lists of varying score scales (e.g., Qdrant cosine similarity vs BM25 unbounded keyword relevance), the platform applies **Reciprocal Rank Fusion (RRF)**.

### RRF Formula
For each unique chunk, an RRF score is computed as:

$$\text{RRF Score}(d) = w_{\text{dense}} \times \left( \frac{1}{k + \text{rank}_{\text{dense}}(d)} \right) + w_{\text{bm25}} \times \left( \frac{1}{k + \text{rank}_{\text{bm25}}(d)} \right)$$

Where:
- $k = 60$ is the RRF constant (which stabilizes scores and prevents top items from dominating).
- $w_{\text{dense}}$ and $w_{\text{bm25}}$ are search-specific weighting coefficients (defaulting to `0.70` and `0.30` respectively).
- $\text{rank}(d)$ is the 1-indexed position of document $d$ in the candidate list.

---

## 3. ContextBuilder Pipeline

Once candidates are fused and sorted, they are processed by the **ContextBuilder Pipeline** before formatting the final LLM prompt.

```
[ Raw Ranked Chunks ] 
         │
         ▼
[ 1. Min Score Filter ] (Drops chunks below score threshold)
         │
         ▼
[ 2. Deduplication ] (Removes redundant chunk IDs across engines)
         │
         ▼
[ 3. Adjacent Expansion ] (Optionally pulls surrounding chunk history)
         │
         ▼
[ 4. Chunk Merging ] (Merges adjacent pages/chunks to save headers)
         │
         ▼
[ 5. Token Budget Allocation ] (Crops content to fit MAX_CONTEXT_TOKENS)
         │
         ▼
[ Assembled Context Payload ]
```

### Stage Details:
1. **Min Score Filter**: Drops chunks falling below the per-request similarity score threshold.
2. **Deduplication**: Removes duplicated chunk IDs.
3. **Adjacent Expansion**: If enabled, fetches page chunks immediately before/after retrieved indices from PostgreSQL to restore missing context.
4. **Chunk Merging**: Merges contiguous chunks from the same document. It combines text fragments to reduce headers and structural syntax (e.g., `---` separators), maximizing raw context density.
5. **Token Budget Constraints**: Counts tokens using local tokenizers and trims the tail of the list to fit within `MAX_CONTEXT_TOKENS` constraints.

---

## 4. Prompt Registry & Provisioning

The `PromptRegistry` manages versioned prompt templates, separating application logic from prompt engineering.

- **Variables Binding**: Renders placeholders like `{context}` and `{query}` alongside request-specific variables.
- **Versioning**: Supports fetching specific historical versions (e.g., `v1.0.0`) or falling back to the current active template.
- **RAG QA Template Example**:
  ```markdown
  System: Use the provided context to answer the user's question accurately. If you don't know the answer, state that you do not know.
  Context: {context}
  User: {query}
  ```
