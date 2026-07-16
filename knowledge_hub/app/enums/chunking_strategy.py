from enum import Enum





class ChunkingStrategy(Enum):
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    STRUCTURE_AWARE = "structure_aware"
    PARENT_CHILD = "parent_child"
    TABLE_AWARE = "table_aware"