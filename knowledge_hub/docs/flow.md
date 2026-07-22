                Upload PDF
                     │
                     ▼
          Generate File Hash
                     │
                     ▼
         PostgreSQL (files table)
         ┌──────────────────────┐
         │ New?                 │
         │                      │
         │ Yes → Generate       │
         │       Document ID    │
         │                      │
         │ No → Get Existing    │
         │       Document ID    │
         └──────────────────────┘
                     │
                     ▼
                 Parser
                     │
                     ▼
             List<Document>
                     │
                     ▼
                Chunker
                     │
                     ▼
             List<Chunk>
                     │
                     ▼
        Generate Chunk IDs + Chunk Hash
                     │
                     ▼
      Save Chunk Metadata (PostgreSQL)
                     │
                     ▼
                 Embedding
                     │
                     ▼
          List<EmbeddedDocument>
                     │
                     ▼
             Qdrant Upsert
