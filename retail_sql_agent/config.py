"""
Centralized configuration for SQL Agent.
All settings are loaded from environment variables with sensible defaults.
"""

import os
import logging
import sys

def setup_logging():
    """Configure production-ready logging."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    logger = logging.getLogger("retail_sql_agent")
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | [%(name)s:%(filename)s:%(lineno)d] | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Optional: File Handler for production logs
        log_file = os.getenv("LOG_FILE")
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
    return logger

# Initialize global logger
logger = setup_logging()

class Config:
    """Application configuration from environment variables."""

    # Anthropic API
    MODEL: str = os.getenv("MODEL_NAME", "claude-3-haiku-20240307")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))
    TIMEOUT: float = float(os.getenv("API_TIMEOUT", "60.0"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.getenv('DB_PATH', 'sales.db')}")
    MAX_ROWS: int = int(os.getenv("MAX_ROWS", "1000"))
    QUERY_TIMEOUT: int = int(os.getenv("QUERY_TIMEOUT", "30"))

    # Agent
    SYSTEM_PROMPT: str = """You are an expert SQL Data Analyst, Retail Data Analyst, and Business Intelligence specialist.

When answering questions about the database:
1. Always inspect the database schema first using the get_database_schema tool
2. Write optimized, safe, read-only SQL SELECT queries (never use INSERT, UPDATE, DELETE, DROP)
3. Use the execute_sql_query tool to retrieve data
4. Use JOINs between tables (e.g., sales and products) to enrich results with descriptive names when appropriate
5. Analyze trends, inventory, and sales performance when relevant
6. Summarize results clearly with structured key numbers, trend observations, and actionable business insights
7. CRITICAL: If you use any of the AVAILABLE SKILLS below, you must always start your response by explicitly stating which skill you are using (e.g. "To answer this, I will use my Retail Insights skill..."). If no extra skill is needed, just answer natively.

Always explain your reasoning and the SQL you generate."""
