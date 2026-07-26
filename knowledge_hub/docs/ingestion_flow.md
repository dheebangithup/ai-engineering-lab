# Document Ingestion and Update Flow

This document details the architecture, pluggable strategy design, and update logic of the document ingestion pipeline in the Enterprise Knowledge Hub.

---

## 1. Architecture & Pluggable Parsers (Scalable Design)

The document ingestion layer is built using the **Strategy Pattern** to ensure the platform is highly modular, extensible, and scalable for production workloads. 

Core components are decoupled via the `DocumentProcessor` abstract base class:

```
                  [ IngestionService ]
                           │
                           ▼
              ┌──────────────────────────┐
              │ <<interface>>            │
              │ DocumentProcessor        │
              └──────────────────────────┘
                           ▲
             ┌─────────────┼─────────────┐
             │             │             │
     [Unstructured]   [LlamaParse]*  [Docling]*
       Processor       Processor     Processor
```

By coding to the `DocumentProcessor` interface, adding a new document parser requires **zero modifications** to the core `IngestionService` execution engine.

### How to Add a New Parser (e.g., LlamaParse or Docling)
1. **Inherit the Interface**: Create a new class implementing the `DocumentProcessor` base class.
2. **Implement Core Methods**:
   - `process(self, file_path: str, metadata: DocumentMetaDataEntity) -> list[Document]`: Defines how a document is parsed and parsed into chunks.
   - `get_config(self) -> dict`: Returns the dictionary of parsing configurations.
   - `compare_config(self, old_config: dict) -> bool`: Compares a new configuration configuration with the previous one to decide on resets.
3. **Register Parser**: Pass your new processor class into `IngestionService` inside `main.py` dependencies.

---

## 2. Ingestion Execution Stages

When a file path is submitted, the ingestion service performs the following steps, recording granular performance latencies:

1. **File Hash Generation**: Computes a SHA-256 hash of the document content to check for duplicates and prevent redundant embedding calculations.
2. **Document Processing (`parsing_time_ms`)**: Invokes the configured strategy parser (e.g., `UnStructuredProcessor`) to extract textual contents, tables, and images.
3. **Smart Invalidation (`chunking_time_ms`)**: Resolves incremental updates. Grouping chunks by page numbers, it compares the parsed version against historical database chunks.
4. **Vector Embedding Generation (`embedding_time_ms`)**: Computes vector representations for new/modified chunks using local or cloud embedding engines.
5. **Vector Store Upsert & Keyword Indexing (`vector_indexing_time_ms`)**:
   - Upserts vector points into the Qdrant database collection.
   - Triggers an in-memory BM25 rebuild from all Qdrant payloads to keep keyword search in sync.
6. **Relational Meta Store Updates**: Saves chunk IDs, hashes, source paths, page numbers, and reading order indices to PostgreSQL.

---

## 3. Incremental Update Flows (Page-Level Invalidation)

To minimize API consumption and vector database update overhead, the ingestion engine executes **incremental updates** when indexing updated versions of existing documents.

```
                  [ Ingest Existing Doc ]
                             │
                             ▼
               ┌───────────────────────────┐
               │  Compare Configuration?   │
               └─────────────┬─────────────┘
                             │
             ┌───────────────┴───────────────┐
             ▼ Config Changed                ▼ Config Identical
      [ Flow A: Full Reset ]        [ Flow B: Page Invalidation ]
    1. Delete all DB Chunks       1. Compare Page-by-Page Chunks
    2. Delete all Qdrant vectors  2. Find lowest edited page number
    3. Re-process & embed all     3. Delete DB/Qdrant chunks >= page
                                  4. Only embed/upsert new pages >= page
```

### Flow A: Configuration Change (Full Reset)
* **Trigger**: If parameters like `chunk_size` or parsing `strategy` (e.g., hi_res vs fast) differ from the previous ingestion run.
* **Result**: Performs a clean wipe of all existing chunks in the database and Qdrant, then re-embeds the entire document.

### Flow B: Identical Configuration (Page-Level Invalidation)
* **Trigger**: If the configuration matches the previous run exactly, but document content has changed.
* **Method**:
  1. Compares chunk hashes on each page in sequence.
  2. Resolves the **lowest edited page number** (`min_edited_page`) by identifying:
     - **Page Addition / Deletion**: A page was added or removed.
     - **Content Modification / Boundary Shift**: A chunk hash changed or text wrapping shifted content across pages.
  3. Purges only chunk metadata and vectors where `page_number >= min_edited_page`.
  4. Generates embeddings and upserts to Qdrant *only* for pages starting from the edited index.
  5. Updates postgres metadata for all chunks to maintain consistent version references.
