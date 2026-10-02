class EmbeddingEngineError(Exception):
    """Base exception for the embedding engine."""


class ModelDownloadError(EmbeddingEngineError):
    """Raised when the embedding model cannot be downloaded."""


class ModelLoadError(EmbeddingEngineError):
    """Raised when the embedding model cannot be loaded."""