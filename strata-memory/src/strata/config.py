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
    memory_llm_timeout_seconds: float = 120.0

    # Neon Management API & Compute Lifecycle Controls
    neon_api_key: Optional[str] = None
    neon_project_id: Optional[str] = None
    neon_endpoint_id: Optional[str] = None
    neon_keep_alive: bool = False  # False = suspend compute after call to save cost; True = keep alive

    strata_default_namespace: str = "default"
    strata_api_host: str = "0.0.0.0"
    strata_api_port: int = 8080


settings = StrataSettings()
