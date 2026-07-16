# knowledge_hub/app/utils/hash_util.py

from __future__ import annotations

import hashlib
from pathlib import Path
import re

from knowledge_hub.app.model import Document


class HashUtil:
    """Utility class for generating SHA-256 hashes."""


    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _sha256(data: bytes) -> str:
        """
        Generate SHA-256 hash from bytes.

        Args:
            data: Input bytes.

        Returns:
            Hexadecimal SHA-256 hash.
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def generate_text_hash(text: str) -> str:
        """
        Generate SHA-256 hash for text.
        """
        if text is None:
            raise ValueError("Text cannot be None.")

        return HashUtil._sha256(HashUtil.normalize_text(text).encode("utf-8"))

    @staticmethod
    def generate_chunk_hash(chunk_content: str) -> str:
        """
        Generate hash for a chunk.
        """
        return HashUtil.generate_text_hash(chunk_content)

    @staticmethod
    def generate_page_hash(page_content: str) -> str:
        """
        Generate hash for an entire page.
        """
        return HashUtil.generate_text_hash(page_content)

    @staticmethod
    def generate_file_hash(file_path: str | Path) -> str:
        """
        Generate SHA-256 hash for a file.

        Reads the file in chunks to support very large files.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        hasher = hashlib.sha256()

        with file_path.open("rb") as file:
            while chunk := file.read(8192):
                hasher.update(chunk)

        return hasher.hexdigest()

    # =============================================================================

    # -----------------------------------------------------------------------------
    # Chunk IDs MUST be deterministic.
    #
    # We intentionally DO NOT use random UUIDs for chunks.
    #
    # Why?
    # ----
    # During document updates (re-indexing), only the modified pages are processed.
    # Before re-indexing a page, we delete all vectors belonging to that page and
    # generate the chunks again.
    #
    # If chunk IDs were random UUIDs:
    #   - Every re-index would create completely new IDs.
    #   - Tracking and debugging become difficult.
    #   - Mapping between PostgreSQL metadata and Qdrant vectors becomes harder.
    #
    # Therefore, chunk IDs are generated deterministically using:
    #
    #     <document_id>_<page_number>_<chunk_index>
    #
    # Example:
    #
    #     550e8400-e29b-41d4-a716-446655440000_P1_C0
    #     550e8400-e29b-41d4-a716-446655440000_P1_C1
    #     550e8400-e29b-41d4-a716-446655440000_P2_C0
    #
    # This allows:
    #
    #  ✓ Easy debugging
    #  ✓ Stable identifiers
    #  ✓ Page-level incremental re-indexing
    #  ✓ Consistent PostgreSQL ↔ Qdrant mapping
    # =============================================================================
    @staticmethod
    def generate_chunk_id(
            doc_id: str,
            page_num: int,
            chunk_index:int
    ) -> str:
        import uuid
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}_P{page_num}_C{chunk_index}"))