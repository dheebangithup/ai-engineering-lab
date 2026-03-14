"""
Centralized configuration for SQL Agent.
All settings are loaded from environment variables with sensible defaults.
"""

import os


class Config:
    """Application configuration from environment variables."""

    # Anthropic API
    MODEL: str = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))
    TIMEOUT: float = float(os.getenv("API_TIMEOUT", "60.0"))

    # Database
    DB_PATH: str = os.getenv("DB_PATH", "../sales.db")
    MAX_ROWS: int = int(os.getenv("MAX_ROWS", "1000"))
    QUERY_TIMEOUT: int = int(os.getenv("QUERY_TIMEOUT", "30"))

    # Agent
    SYSTEM_PROMPT: str = """You are a professional SQL data analyst.

When answering questions about data:
1. Always inspect the database schema first using the get_database_schema tool
2. Write safe, read-only SQL SELECT queries
3. Use the execute_sql_query tool to retrieve data
4. Summarize results clearly with key insights

Never execute destructive queries (DROP, DELETE, INSERT, UPDATE, etc.).
Always explain your reasoning and the SQL you generate."""
