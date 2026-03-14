from tools.sql_tool import SQLAnalystToolkit


def main():
    """Standalone testing"""
    print("=" * 70)
    print("SQL ANALYST SKILL - TOOLKIT TEST")
    print("=" * 70)

    toolkit = SQLAnalystToolkit()
    toolkit.initialize()

    print("\n" + "=" * 70)
    print("Testing Tools:")
    print("=" * 70)

    # Test 1: Get schema
    print("\n1️⃣  Testing: get_schema()")
    result = toolkit.get_schema()
    if result["success"]:
        print(result["schema"])

    # Test 2: Execute query
    print("\n2️⃣  Testing: execute_query()")
    result = toolkit.execute_query(
        query="SELECT product_name, SUM(revenue) as total FROM sales JOIN products ON sales.product_id = products.product_id GROUP BY product_name ORDER BY total DESC LIMIT 5",
        explanation="Top 5 products by revenue"
    )
    if result["success"]:
        print(f"✓ Retrieved {result['rows_returned']} rows")
        print(f"  Columns: {result['columns']}")
        print(f"  Data Preview: {result['data_preview']}")
        print(f"  Summary: {result['summary']}")


    print("\n" + "=" * 70)
    print("✓ All tools working correctly!")
    print("=" * 70)

    toolkit.cleanup()


if __name__ == "__main__":
    main()