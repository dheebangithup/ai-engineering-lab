"""
SQL tools — core database tools for the SQL Analyst skill.

Provides two interfaces:
  - Native SDK @tool decorated functions for SDK MCP Server
  - Internal helper functions for direct database access
"""

import json
import os

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from core.database_manager import DatabaseManager
from config import Config, logger

# Shared database manager instance
_db = DatabaseManager(db_url=Config.DATABASE_URL)


def initialize_tools():
    """Initialize the database connection for tools."""
    is_sqlite = _db.db_url.startswith("sqlite:///")
    file_path = _db.db_url.replace("sqlite:///", "") if is_sqlite else ""
    
    # If SQLite and file doesn't exist, initialize data
    if is_sqlite and not os.path.exists(file_path):
        logger.info(f"Creating sample database at {file_path}...")
        _db.initialize_sample_data()
    else:
        # Otherwise just connect normally
        _db.connect()
        try:
            # Let's run a quick health test / init for non SQLite
            if not is_sqlite:
                _db.initialize_sample_data()
        except Exception as e:
            logger.warning(f"Database sample data init error (safe to ignore if using existing DB): {e}")
            
    logger.info(f"✓ Using database: {_db.db_url}")


def cleanup_tools():
    """Clean up database resources."""
    _db.close()


from claude_agent_sdk import tool

# ─── Standard tool functions (used by SDK MCP Server) ────────────────

@tool(
    name="get_database_schema",
    description="Get the database schema. By default, it returns a list of table names. If specific 'tables' are provided, it returns the detailed schema (columns and types) for those tables. Follow a progressive disclosure pattern: list tables first, then request details for specific ones you need.",
    input_schema={
        "tables": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional list of table names to get detailed schema for."
        }
    }
)
async def get_database_schema_mcp(args: dict) -> dict:
    try:
        tables = args.get("tables")
        schema = _db.get_schema(tables=tables)
        return {"content": [{"type": "text", "text": json.dumps({"success": True, "schema": schema})}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({"success": False, "error": str(e)})}]}


@tool(
    name="execute_sql_query",
    description="Execute a safe SQL SELECT query against the database and return structured results. Only SELECT queries are allowed for safety.",
    input_schema={
        "query": str,
        "explanation": str
    }
)
async def execute_sql_query_mcp(args: dict) -> dict:
    query = args["query"]
    explanation = args.get("explanation", "")
    logger.info(f"Executing SQL Query")
    logger.debug(f"SQL: {query} | Purpose: {explanation}")

    try:
        df = _db.execute_query(query)
        result = {
            "success": True,
            "rows_returned": len(df),
            "columns": list(df.columns),
            "data_preview": df.head(10).to_dict("records"),
            "summary": f"Successfully retrieved {len(df)} rows",
        }
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({"success": False, "error": str(e)})}]}


# For compatibility/internal use if needed
def get_database_schema():
    return _db.get_schema()

def execute_sql_query(query: str, explanation: str = ""):
    return _db.execute_query(query)

DB_TOOLS = [get_database_schema_mcp, execute_sql_query_mcp]
