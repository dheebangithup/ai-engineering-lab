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

    # Claude Agent SDK Configuration
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

When answering questions about the database, follow these efficiency and scalability patterns:
1. **Schema Knowledge**:
   - Check the **AVAILABLE SKILL** section in your context. Many skills contain pre-defined table schemas (columns and types).
   - If the skill you are using provides the schema for the tables you need, **use it immediately** to write your query.
   - If you need to query tables NOT listed in the skill, or if no skill is active, use **Progressive Disclosure**:
     - Call `retail:get_database_schema` with the `tables` parameter for ONLY the additional tables you need.
2. **Safe Query Generation**:
   - Write optimized, safe, read-only SQL SELECT queries.
   - Use the `retail:execute_sql_query` tool to retrieve data.
3. **Business Insights**:
   - Analyze trends, inventory, and sales performance.
   - Summarize results clearly with structured numbers and actionable insights.
4. **Tool Referencing**:
   - Always use the fully qualified tool names: `retail:get_database_schema`, `retail:execute_sql_query`, etc.
5. **Skill Usage**:
   - If you use a skill, start your response by stating which skill you are using (e.g., "Using my Retail Insights skill...").
"""
