"""
Export tools — save query results to CSV or JSON files.
Standardized with @tool for SDK orchestration.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database_manager import DatabaseManager

_db = DatabaseManager()


def _ensure_db():
    if not _db.conn:
        _db.connect()


from claude_agent_sdk import tool

@tool(
    name="export_to_csv",
    description="Export SQL query results to a CSV file.",
    input_schema={
        "query": str,
        "filename": str
    }
)
async def export_to_csv_mcp(args: dict) -> dict:
    query = args["query"]
    filename = args.get("filename", "")
    _ensure_db()
    if not filename:
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if not filename.endswith(".csv"):
        filename += ".csv"

    try:
        # Note: We can reuse the internal implementation if we want, but keeping it direct for clarity
        from tools.database_tools import execute_sql_query
        df = execute_sql_query(query)
        filepath = os.path.abspath(filename)
        df.to_csv(filepath, index=False)
        res = {
            "success": True, 
            "filepath": filepath, 
            "rows": len(df),
            "summary": f"Exported {len(df)} rows to {filename}"
        }
        return {"content": [{"type": "text", "text": json.dumps(res)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({"success": False, "error": str(e)})}]}


@tool(
    name="export_to_json",
    description="Export SQL query results to a JSON file.",
    input_schema={
        "query": str,
        "filename": str
    }
)
async def export_to_json_mcp(args: dict) -> dict:
    query = args["query"]
    filename = args.get("filename", "")
    _ensure_db()
    if not filename:
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if not filename.endswith(".json"):
        filename += ".json"

    try:
        from tools.database_tools import execute_sql_query
        df = execute_sql_query(query)
        filepath = os.path.abspath(filename)
        df.to_json(filepath, orient="records", indent=2, default_handler=str)
        res = {
            "success": True, 
            "filepath": filepath, 
            "rows": len(df),
            "summary": f"Exported {len(df)} rows to {filename}"
        }
        return {"content": [{"type": "text", "text": json.dumps(res)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({"success": False, "error": str(e)})}]}

EXPORT_TOOLS = [export_to_csv_mcp, export_to_json_mcp]

