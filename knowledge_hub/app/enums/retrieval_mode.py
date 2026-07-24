from enum import Enum


class RetrievalMode(str, Enum):
    """Retrieval pipeline mode controlling which search strategy to use."""
    DENSE = "dense"      # Vector similarity search only (Qdrant cosine)
    BM25 = "bm25"        # BM25 keyword search only (sparse retrieval)
    HYBRID = "hybrid"    # Dense + BM25 fused via Reciprocal Rank Fusion (RRF)
