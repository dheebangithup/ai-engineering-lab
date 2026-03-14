"""
SQL tools — core database tools for the SQL Analyst skill.

Provides two interfaces:
  - @beta_tool decorated functions for Anthropic SDK tool_runner
  - Handler-style dicts (ALL_MCP_TOOLS) for claude_agent_sdk MCP server
"""

import json
import os

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anthropic import beta_tool
from core.data_base_manager import DatabaseManager
from config import Config

# Shared database manager instance
_db = DatabaseManager(db_path=Config.DB_PATH)


def initialize_tools():
    """Initialize the database connection for tools."""
    if not os.path.exists(_db.db_path):
        print("Creating sample database...")
        _db.initialize_sample_data()
    else:
        _db.connect()
        print(f"✓ Using existing database: {_db.db_path}")


def cleanup_tools():
    """Clean up database resources."""
    _db.close()


# ─── @beta_tool versions (used by Anthropic SDK tool_runner) ────────────────

@beta_tool
def get_database_schema() -> str:
    """Get the complete database schema showing all tables, columns, and their types.

    Use this tool first to understand the database structure before writing queries.

    Returns:
        A formatted string showing all tables and their column definitions.
    """
    try:
        schema = _db.get_schema()
        return json.dumps({"success": True, "schema": schema})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@beta_tool
def execute_sql_query(query: str, explanation: str) -> str:
    """Execute a SQL SELECT query against the database and return structured results.

    Only SELECT queries are allowed for safety. The query results are returned
    as JSON with column names and data preview.

    Args:
        query: A valid SQL SELECT statement to execute.
        explanation: Brief explanation of what this query does and why.

    Returns:
        JSON string with query results including row count, columns, and data preview.
    """
    print(f"\n🔍 Executing Query:")
    print(f"   SQL: {query}")
    print(f"   Purpose: {explanation}\n")

    try:
        df = _db.execute_query(query)
        result = {
            "success": True,
            "rows_returned": len(df),
            "columns": list(df.columns),
            "data_preview": df.head(10).to_dict("records"),
            "summary": f"Successfully retrieved {len(df)} rows",
        }
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ─── Handler-style dicts (used by claude_agent_sdk create_sdk_mcp_server) ───

def _get_schema_handler(args: dict) -> dict:
    return {"content": [{"type": "text", "text": get_database_schema()}]}


def _execute_query_handler(args: dict) -> dict:
    result = execute_sql_query(args["query"], args.get("explanation", ""))
    return {"content": [{"type": "text", "text": result}]}


SQL_SCHEMA_TOOL = {
    "name": "get_database_schema",
    "description": "Get database schema — all tables and columns. Call this first before any SQL query.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
    "handler": _get_schema_handler,
}

SQL_QUERY_TOOL = {
    "name": "execute_sql_query",
    "description": "Execute a safe SQL SELECT query on the sales database. Returns rows, columns, and data preview.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Valid SQL SELECT statement"},
            "explanation": {"type": "string", "description": "What this query does"},
        },
        "required": ["query", "explanation"],
    },
    "handler": _execute_query_handler,
}

# For @beta_tool / tool_runner
ALL_TOOLS = [get_database_schema, execute_sql_query]

# For claude_agent_sdk MCP server
ALL_MCP_TOOLS = [SQL_SCHEMA_TOOL, SQL_QUERY_TOOL]
