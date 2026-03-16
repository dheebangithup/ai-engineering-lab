import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.database_tools import initialize_tools, execute_sql_query, cleanup_tools

def test_extended_schema():
    initialize_tools()
    
    tables_to_test = ["categories", "suppliers", "products", "inventory", "customers", "sales"]
    
    print("\n--- Testing Extended Schema ---")
    for table in tables_to_test:
        print(f"\nChecking table: {table}")
        try:
            result = execute_sql_query(f"SELECT COUNT(*) as count FROM {table}", f"Verify {table} exists")
            count = result.iloc[0]['count']
            print(f"✅ Table {table} exists and has {count} rows.")
        except Exception as e:
            print(f"❌ Error checking table {table}: {e}")

    # Test relationship
    print("\n--- Testing Relationship (Products with Category Names) ---")
    query = """
        SELECT p.product_name, c.category_name 
        FROM products p 
        JOIN categories c ON p.category_id = c.category_id 
        LIMIT 5
    """
    try:
        result = execute_sql_query(query, "Test join")
        print("✅ Join successful. Sample data:")
        print(result)
    except Exception as e:
        print(f"❌ Join failed: {e}")

    cleanup_tools()

if __name__ == "__main__":
    test_extended_schema()
