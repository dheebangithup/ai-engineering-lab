import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from config import Config, logger

class DatabaseManager:
    """Manages database connections and operations using SQLAlchemy for cross-DB support"""

    def __init__(self, db_url: str = "sqlite:///sales.db", max_rows: int = 1000):
        self.db_url = db_url
        self.engine = None
        self.max_rows = max_rows
        self.timeout = 30

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Establish SQLAlchemy database engine"""
        if not self.engine:
            try:
                self.engine = create_engine(self.db_url, pool_pre_ping=True)
                # Test connection immediately
                with self.engine.connect() as conn:
                    pass
                logger.info(f"Connected to database: {self.db_url}")
            except SQLAlchemyError as e:
                logger.error(f"Database connection error: {e}")
                self.engine = None
                raise # Re-raise the exception after logging

    def initialize_sample_data(self):
        """Create sample database for testing (SQLite fallback friendly)"""
        self.connect()

        try:
            # Using raw SQL for generic table creation
            create_products = text("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id INTEGER PRIMARY KEY,
                    product_name VARCHAR(255) NOT NULL,
                    category VARCHAR(100),
                    price FLOAT
                )
            """)

            create_sales = text("""
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    quantity INTEGER,
                    sale_date DATE,
                    revenue FLOAT,
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                )
            """)

            # Special casing SQLite AUTOINCREMENT syntax vs others if needed, but for the sample
            # we'll assume it's running against SQLite primarily.
            if "sqlite" not in self.db_url:
                create_sales = text("""
                    CREATE TABLE IF NOT EXISTS sales (
                        sale_id SERIAL PRIMARY KEY,
                        product_id INTEGER,
                        quantity INTEGER,
                        sale_date DATE,
                        revenue FLOAT,
                        FOREIGN KEY (product_id) REFERENCES products(product_id)
                    )
                """)

            with self.engine.begin() as conn:
                conn.execute(create_products)
                conn.execute(create_sales)

                # Check if data already exists to avoid duplication on re-runs
                existing_products = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
                if existing_products > 0:
                    logger.info("Sample data already exists.")
                    return

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

                # Insert Products
                for p in products:
                    conn.execute(
                        text("INSERT INTO products (product_id, product_name, category, price) VALUES (:id, :name, :cat, :price)"),
                        {"id": p[0], "name": p[1], "cat": p[2], "price": p[3]}
                    )

                # Generate sales data (last 90 days)
                import random
                base_date = datetime.now() - timedelta(days=90)

                sales_data = []
                for day in range(90):
                    sale_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')
                    for product_id in range(1, 11):
                        if product_id in [1, 4, 6]:
                            num_sales = random.randint(5, 15)
                        else:
                            num_sales = random.randint(10, 30)

                        for _ in range(random.randint(1, 3)):
                            quantity = random.randint(1, 3)
                            price = [prod[3] for prod in products if prod[0] == product_id][0]
                            revenue = quantity * price
                            sales_data.append({"pid": product_id, "qty": quantity, "sdate": sale_date, "rev": revenue})

                for s in sales_data:
                    conn.execute(
                        text("INSERT INTO sales (product_id, quantity, sale_date, revenue) VALUES (:pid, :qty, :sdate, :rev)"),
                        s
                    )
                conn.commit() # Ensure schema changes and data inserts are committed

            logger.info(f"Database initialized with {len(sales_data)} sales records")
        except SQLAlchemyError as e:
            logger.error(f"Error initializing sample data: {e}")
            raise # Re-raise the exception after logging

    def get_schema(self) -> str:
        """Get database schema universally using SQLAlchemy inspector"""
        self.connect()
        inspector = inspect(self.engine)
        schema = []

        try:
            table_names = inspector.get_table_names()
            logger.info(f"Retrieved schema for {len(table_names)} tables.")

            schema_str = "Database Schema:\n"
            for table_name in table_names:
                schema_str += f"\n📊 Table: {table_name}\n"
                for column in inspector.get_columns(table_name):
                    col_name = column['name']
                    col_type = str(column['type'])
                    schema_str += f"   • {col_name} ({col_type})\n"
            return schema_str
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving schema: {e}")
            raise # Re-raise the exception after logging

    def is_safe_query(self, query: str) -> bool:
        """Validate query safety"""
        q = query.upper().strip()

        # Block dangerous keywords
        dangerous = ['DROP ', 'DELETE ', 'INSERT ', 'UPDATE ', 'ALTER ',
                     'CREATE ', 'TRUNCATE ', 'EXEC ', 'EXECUTE ', 'GRANT ', 'REVOKE ']
        if any(kw in q for kw in dangerous):
            logger.warning(f"Blocked unsafe query attempt: {query}")
            return False

        # No multiple statements
        if query.count(';') > 1:
            logger.warning(f"Blocked query with multiple statements: {query}")
            return False

        logger.debug(f"Query deemed safe: {query}")
        return True

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query safely using Pandas and SQLAlchemy"""
        self.connect()

        if not self.is_safe_query(query):
            raise ValueError("⚠️  Unsafe query detected - only safe SELECT/WITH queries allowed")

        try:
            with self.engine.connect() as connection:
                df = pd.read_sql_query(text(query), connection)

            row_count = len(df)
            if row_count > self.max_rows:
                df = df.head(self.max_rows)
                logger.warning(f"Results limited to {self.max_rows} rows for query: {query}")
            
            logger.info(f"Query executed successfully, returned {row_count} rows.")
            return df

        except SQLAlchemyError as e:
            logger.error(f"Database error during query execution: {e}\nQuery: {query}")
            raise Exception(f"❌ Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise Exception(f"❌ Query execution failed: {str(e)}")

    def close(self):
        """Dispose database engine"""
        if self.engine:
            self.engine.dispose()
            self.engine = None

