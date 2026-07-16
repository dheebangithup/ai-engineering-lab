from enum import Enum


class EmbeddingProvider(Enum):
    OPENAI = "openai"
    BGE = "bge"
    E5 = "e5"
    NOMIC = "nomic"