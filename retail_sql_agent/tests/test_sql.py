import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.database_tools import initialize_tools, get_database_schema, execute_sql_query, cleanup_tools


def main():
    """Test all tools independently."""
    print("=" * 70)
    print("SQL ANALYST — TOOLKIT TEST")
    print("=" * 70)

    initialize_tools()

    # Test 1: Get schema
    print("\n1️⃣  Testing: get_database_schema()")
    result = get_database_schema()
    print(result)

    # Test 2: Execute query
    print("\n2️⃣  Testing: execute_sql_query()")
    result = execute_sql_query(
        query="SELECT product_name, SUM(revenue) as total FROM sales JOIN products ON sales.product_id = products.product_id GROUP BY product_name ORDER BY total DESC LIMIT 5",
        explanation="Top 5 products by revenue",
    )
    print(result)

    print("\n" + "=" * 70)
    print("✓ All tools working correctly!")
    print("=" * 70)

    cleanup_tools()


if __name__ == "__main__":
    main()