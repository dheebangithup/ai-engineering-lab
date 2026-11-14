"""
Global settings and environment variable management for J.A.R.V.I.S.
"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from jarvis.workspace import default_workspace


class Settings(BaseSettings):
    """Application-wide settings with environment variable fallbacks."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LangSmith Tracing
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_endpoint: str = Field(default="https://api.smith.langchain.com", alias="LANGSMITH_ENDPOINT")
    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="jarvis", alias="LANGSMITH_PROJECT")

    # Seed Provider Credentials (used to seed provider store if empty)
    kodekloud_api_key: Optional[str] = Field(default=None, alias="KODEKLOUD_API_KEY")
    kodekloud_base_url: str = Field(default="https://api.ai.kodekloud.com/v1", alias="KODEKLOUD_BASE_URL")
    
    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
    ollama_api_key: str = Field(default="ollama", alias="OLLAMA_API_KEY")
    
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")
    
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    # Workspace Override
    jarvis_workspace: Optional[str] = Field(default=None, alias="JARVIS_WORKSPACE")

    # Strata MCP Server Configuration
    strata_mcp_command: str = Field(default="strata-mcp", alias="STRATA_MCP_COMMAND")
    strata_mcp_transport: str = Field(default="stdio", alias="STRATA_MCP_TRANSPORT")
    strata_mcp_url: Optional[str] = Field(default=None, alias="STRATA_MCP_URL")


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Singleton getter for application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
