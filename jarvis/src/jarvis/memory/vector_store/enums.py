from enum import Enum


class RetrievalMode(Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"