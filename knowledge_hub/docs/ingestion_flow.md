# Document Ingestion and Update Flow

This document details the architecture, stages, and update logic of the document ingestion pipeline.

---

## 1. Initial Ingestion Pipeline
When a new document is uploaded, it passes through the following sequential stages:

```
[ Upload PDF ]
      │
      ▼
[ File Hash Verification ] (Calculates SHA-256 to detect duplicates)
      │
      ▼
[ Document Parser ] (Unstructured/Strategy Pattern → list[Document])
      │
      ▼
[ Document Chunker ] (Smart boundaries → list[Chunk])
      │
      ▼
[ Embedding Generation ] (Computes vector representation)
      │
      ▼
[ Vector Store Upsert ] (Qdrant) AND [ Metadata Storage ] (PostgreSQL)
```

---

## 2. Ingestion Update Flows (Incremental updates)
When an ingestion request is triggered for an **existing document** (matching `document_id`), the pipeline runs configuration checking and decides between two flows:

### Flow A: Configuration has Changed (Full Reset)
* **Trigger**: If parameters like `chunk_size`, `strategy` (e.g., hi_res vs fast), or partitioning parameters differ from the last ingestion run.
* **Process**:
  1. Performs a **Full Reset**.
  2. Deletes **all** existing chunks for this document from both PostgreSQL database and Qdrant vector store.
  3. Re-runs the parser, chunker, and embedding generator with the new configuration.
  4. Inserts all new chunks fresh.

### Flow B: Configuration is Identical (Page-Level Invalidation)
* **Trigger**: If the configuration matches the previous run exactly, but document content has changed.
* **Process**:
  1. Compares the new parsed chunks with the database chunks page-by-page.
  2. Identifies the **lowest edited page number** (`min_edited_page`) by detecting added/deleted pages or modified chunk hashes.
  3. Deletes all chunks belonging to `page_number >= min_edited_page` from PostgreSQL and Qdrant.
  4. Only embeds and upserts the newly generated chunks for pages $\ge \text{min\_edited\_page}$.
  5. Updates all database metadata (including unchanged pages) to sync the document version.

> [!NOTE]
> For details on how the page-level comparison checks and boundaries are handled, refer to the [Page Invalidation Flow](page_invalidation_flow.md) document.
