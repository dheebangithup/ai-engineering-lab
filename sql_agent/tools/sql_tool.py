"""
SQL tools using the @beta_tool decorator from the Anthropic Python SDK.

The @beta_tool decorator auto-generates tool JSON schemas from function
signatures and docstrings — no more manual tool definitions needed.
The tool_runner in the agent will automatically call these functions.
"""

import json
from anthropic import beta_tool
from core.data_base_manager import DatabaseManager
from config import Config


# Shared database manager instance
_db = DatabaseManager(db_path=Config.DB_PATH)


def initialize_tools():
    """Initialize the database connection for tools."""
    import os
    if not os.path.exists(_db.db_path):
        print("Creating sample database...")
        _db.initialize_sample_data()
    else:
        _db.connect()
        print(f"✓ Using existing database: {_db.db_path}")


def cleanup_tools():
    """Clean up database resources."""
    _db.close()


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


# List of all tools for the agent to use
ALL_TOOLS = [get_database_schema, execute_sql_query]
