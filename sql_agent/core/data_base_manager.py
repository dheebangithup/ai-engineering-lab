import sqlite3
from datetime import datetime, timedelta
import pandas as pd

class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, db_path: str = "sales.db", max_rows: int = 1000):
        self.db_path = db_path
        self.conn = None
        self.max_rows = max_rows
        self.timeout = 30

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        print(f"✓ Connected to database: {self.db_path}")

    def initialize_sample_data(self):
        """Create sample database for testing"""
        self.connect()
        cursor = self.conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT,
                price REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                quantity INTEGER,
                sale_date DATE,
                revenue REAL,
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        """)

        # Sample products
        products = [
            (1, 'Laptop', 'Electronics', 999.99),
            (2, 'Mouse', 'Electronics', 29.99),
            (3, 'Keyboard', 'Electronics', 79.99),
            (4, 'Monitor', 'Electronics', 299.99),
            (5, 'Desk Chair', 'Furniture', 199.99),
            (6, 'Desk', 'Furniture', 399.99),
            (7, 'Coffee Maker', 'Appliances', 89.99),
            (8, 'Microwave', 'Appliances', 149.99),
            (9, 'Notebook', 'Stationery', 5.99),
            (10, 'Pen Set', 'Stationery', 12.99)
        ]

        cursor.executemany(
            "INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?)",
            products
        )

        # Generate sales data (last 90 days)
        import random
        base_date = datetime.now() - timedelta(days=90)

        sales_data = []
        for day in range(90):
            sale_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')

            for product_id in range(1, 11):
                # Different sales patterns
                if product_id in [1, 4, 6]:  # High-value items
                    num_sales = random.randint(5, 15)
                else:
                    num_sales = random.randint(10, 30)

                for _ in range(random.randint(1, 3)):
                    quantity = random.randint(1, 3)
                    price = [p[3] for p in products if p[0] == product_id][0]
                    revenue = quantity * price
                    sales_data.append((product_id, quantity, sale_date, revenue))

        cursor.executemany(
            "INSERT INTO sales (product_id, quantity, sale_date, revenue) VALUES (?, ?, ?, ?)",
            sales_data
        )

        self.conn.commit()
        print(f"✓ Database initialized with {len(sales_data)} sales records")

    def get_schema(self) -> str:
        """Get database schema"""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        schema = []

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            schema.append(f"\n📊 Table: {table_name}")
            for col in columns:
                schema.append(f"   • {col[1]} ({col[2]})")

        return "\n".join(schema)

    def is_safe_query(self, query: str) -> bool:
        """Validate query safety"""
        q = query.upper().strip()

        # Must start with SELECT
        if not q.startswith('SELECT'):
            return False

        # Block dangerous keywords
        dangerous = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER',
                     'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE']
        if any(kw in q for kw in dangerous):
            return False

        # No multiple statements
        if query.count(';') > 1:
            return False

        return True

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query safely"""
        if not self.conn:
            self.connect()

        if not self.is_safe_query(query):
            raise ValueError("⚠️  Unsafe query detected - only SELECT queries allowed")

        try:
            df = pd.read_sql_query(query, self.conn)

            if len(df) > self.max_rows:
                df = df.head(self.max_rows)
                print(f"⚠️  Results limited to {self.max_rows} rows")

            return df

        except Exception as e:
            raise Exception(f"❌ Query execution failed: {str(e)}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
