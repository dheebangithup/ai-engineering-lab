"""
Export tools — save query results to CSV or JSON files.
Standardized with @beta_tool for SDK orchestration.
"""

import json
import os
import sys
from datetime import datetime
from anthropic import beta_tool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database_manager import DatabaseManager

_db = DatabaseManager()


def _ensure_db():
    if not _db.conn:
        _db.connect()


@beta_tool
def export_to_csv(query: str, filename: str = "") -> str:
    """Export SQL query results to a CSV file.

    Args:
        query: SQL SELECT query whose results to export.
        filename: Optional output filename (e.g. top_products.csv).
    """
    _ensure_db()
    if not filename:
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if not filename.endswith(".csv"):
        filename += ".csv"

    try:
        df = _db.execute_query(query)
        filepath = os.path.abspath(filename)
        df.to_csv(filepath, index=False)
        return json.dumps({
            "success": True, 
            "filepath": filepath, 
            "rows": len(df),
            "summary": f"Exported {len(df)} rows to {filename}"
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@beta_tool
def export_to_json(query: str, filename: str = "") -> str:
    """Export SQL query results to a JSON file.

    Args:
        query: SQL SELECT query whose results to export.
        filename: Optional output filename (e.g. sales_data.json).
    """
    _ensure_db()
    if not filename:
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if not filename.endswith(".json"):
        filename += ".json"

    try:
        df = _db.execute_query(query)
        filepath = os.path.abspath(filename)
        df.to_json(filepath, orient="records", indent=2, default_handler=str)
        return json.dumps({
            "success": True, 
            "filepath": filepath, 
            "rows": len(df),
            "summary": f"Exported {len(df)} rows to {filename}"
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
