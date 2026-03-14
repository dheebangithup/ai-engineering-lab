"""
Data Quality tools — run health checks on the sales database.
Standardized with @beta_tool for SDK orchestration.
"""

import json
import os
import sys
from anthropic import beta_tool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.data_base_manager import DatabaseManager

_db = DatabaseManager()


def _ensure_db():
    if not _db.conn:
        _db.connect()


@beta_tool
def check_data_quality() -> str:
    """Run comprehensive data quality checks on the database.
    Checks for missing product names, zero revenue sales, orphaned records, 
    future dates, and duplicate sale records.
    """
    _ensure_db()

    checks = [
        ("SELECT COUNT(*) as cnt FROM products WHERE product_name IS NULL OR product_name = ''", "Missing product names", "🔴 Critical"),
        ("SELECT COUNT(*) as cnt FROM sales WHERE revenue IS NULL OR revenue <= 0", "Sales with missing/zero revenue", "🟡 Warning"),
        ("SELECT COUNT(*) as cnt FROM sales WHERE product_id NOT IN (SELECT product_id FROM products)", "Orphaned sales", "🔴 Critical"),
        ("SELECT COUNT(*) as cnt FROM sales WHERE sale_date > date('now')", "Sales with future dates", "🟡 Warning"),
        ("SELECT COUNT(*) as cnt FROM (SELECT product_id, quantity, sale_date, revenue, COUNT(*) as n FROM sales GROUP BY product_id, quantity, sale_date, revenue HAVING n > 1)", "Potential duplicate sales", "🟡 Warning"),
    ]

    findings = []
    issues = 0
    for sql, label, severity in checks:
        try:
            df = _db.execute_query(sql)
            count = int(df.iloc[0, 0])
            status = "🟢 OK" if count == 0 else severity
            if count > 0: issues += 1
            findings.append({"check": label, "status": status, "affected": count})
        except Exception as e:
            findings.append({"check": label, "status": "❌ Error", "error": str(e)})

    return json.dumps({
        "summary": "Database Healthy" if issues == 0 else f"Found {issues} issues",
        "findings": findings
    })
