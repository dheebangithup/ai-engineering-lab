from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class StrataSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://strata_user:strata_password@localhost:5432/strata"
    direct_database_url: Optional[str] = None
    db_statement_cache_size: int = 0  # Required 0 for Neon -pooler (PgBouncer transaction mode)
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10

    embedding_provider: str = "ollama"
    embedding_base_url: str = "http://localhost:11434/v1"
    embedding_api_key: str = "ollama"
    embedding_model_name: str = "nomic-embed-text"
    embedding_dimensions: int = 768

    memory_llm_enabled: bool = True
    memory_llm_base_url: str = "http://localhost:11434/v1"
    memory_llm_api_key: str = "ollama"
    memory_llm_model: str = "qwen2.5:3b-instruct"
    memory_llm_timeout_seconds: float = 240.0

    # Dynamic Recall Tuning & Limits
    recall_match_threshold: float = 0.35  # Vector similarity cutoff in hybrid_memory_search
    recall_min_score: float = 0.0         # Minimum RRF/composite score to return in recall
    entity_similarity_threshold: float = 0.40  # Seed node vector similarity cutoff
    contradiction_threshold: float = 0.94      # Cosine similarity threshold for superseding

    # Write-path Context Pre-fetch Limits
    prefetch_semantic_limit: int = 5
    prefetch_procedural_limit: int = 3
    prefetch_entity_limit: int = 5

    # Laya Decision Model Pre-routing Controls
    laya_enabled: bool = True
    laya_complexity_threshold: int = 2
    laya_fallback_to_llm: bool = True

    # Neon Management API & Compute Lifecycle Controls
    neon_api_key: Optional[str] = None
    neon_project_id: Optional[str] = None
    neon_endpoint_id: Optional[str] = None
    neon_keep_alive: bool = False  # False = suspend compute after call to save cost; True = keep alive

    strata_default_namespace: str = "default"
    strata_api_host: str = "0.0.0.0"
    strata_api_port: int = 8080

    # Memory Lifecycle & Retention Policies
    episodic_default_ttl_days: Optional[int] = 30  # Default days before episodic memory soft-expires (None = indefinite)
    superseded_retention_days: int = 90             # Days to retain superseded/soft-deleted rows before hard purge
    toxic_utility_threshold: int = -5              # Memories at or below this score are automatically retired
    distillation_batch_size: int = 20              # Batch size of expired episodes for LLM consolidation


settings = StrataSettings()
