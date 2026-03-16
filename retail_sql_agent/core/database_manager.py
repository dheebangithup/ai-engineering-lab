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
            # Table creation SQL
            tables = [
                ("""
                    CREATE TABLE IF NOT EXISTS categories (
                        category_id INTEGER PRIMARY KEY,
                        category_name VARCHAR(100) NOT NULL,
                        description TEXT
                    )
                """, "categories"),
                ("""
                    CREATE TABLE IF NOT EXISTS suppliers (
                        supplier_id INTEGER PRIMARY KEY,
                        supplier_name VARCHAR(255) NOT NULL,
                        contact_info TEXT
                    )
                """, "suppliers"),
                ("""
                    CREATE TABLE IF NOT EXISTS products (
                        product_id INTEGER PRIMARY KEY,
                        product_name VARCHAR(255) NOT NULL,
                        category_id INTEGER,
                        supplier_id INTEGER,
                        price FLOAT,
                        FOREIGN KEY (category_id) REFERENCES categories(category_id),
                        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
                    )
                """, "products"),
                ("""
                    CREATE TABLE IF NOT EXISTS inventory (
                        product_id INTEGER PRIMARY KEY,
                        stock_level INTEGER,
                        reorder_point INTEGER,
                        last_restock_date DATE,
                        FOREIGN KEY (product_id) REFERENCES products(product_id)
                    )
                """, "inventory"),
                ("""
                    CREATE TABLE IF NOT EXISTS customers (
                        customer_id INTEGER PRIMARY KEY,
                        first_name VARCHAR(100),
                        last_name VARCHAR(100),
                        email VARCHAR(255),
                        loyalty_points INTEGER,
                        join_date DATE
                    )
                """, "customers"),
                ("""
                    CREATE TABLE IF NOT EXISTS sales (
                        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER,
                        customer_id INTEGER,
                        quantity INTEGER,
                        sale_date DATE,
                        revenue FLOAT,
                        FOREIGN KEY (product_id) REFERENCES products(product_id),
                        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                    )
                """, "sales")
            ]

            with self.engine.begin() as conn:
                for sql, name in tables:
                    conn.execute(text(sql))

                # Check if data already exists
                if conn.execute(text("SELECT COUNT(*) FROM products")).scalar() > 0:
                    logger.info("Sample data already exists.")
                    return

                # 1. Categories
                conn.execute(text("INSERT INTO categories (category_id, category_name, description) VALUES "
                                  "(1, 'Electronics', 'Gadgets and hardware'), "
                                  "(2, 'Furniture', 'Home and office furniture'), "
                                  "(3, 'Appliances', 'Household appliances'), "
                                  "(4, 'Stationery', 'Office supplies')"))

                # 2. Suppliers
                conn.execute(text("INSERT INTO suppliers (supplier_id, supplier_name, contact_info) VALUES "
                                  "(101, 'Global Tech', 'contact@globaltech.com'), "
                                  "(102, 'Comfort Plus', 'sales@comfortplus.com'), "
                                  "(103, 'Kitchen Pro', 'info@kitchenpro.com'), "
                                  "(104, 'Paper & Co', 'orders@paperco.com')"))

                # 3. Products
                products_list = [
                    (1, 'Laptop', 1, 101, 999.99), (2, 'Mouse', 1, 101, 29.99), (3, 'Keyboard', 1, 101, 79.99),
                    (4, 'Monitor', 1, 101, 299.99), (5, 'Desk Chair', 2, 102, 199.99), (6, 'Desk', 2, 102, 399.99),
                    (7, 'Coffee Maker', 3, 103, 89.99), (8, 'Microwave', 3, 103, 149.99), (9, 'Notebook', 4, 104, 5.99),
                    (10, 'Pen Set', 4, 104, 12.99)
                ]
                for p in products_list:
                    conn.execute(text("INSERT INTO products (product_id, product_name, category_id, supplier_id, price) "
                                      "VALUES (:id, :name, :cid, :sid, :price)"),
                                 {"id": p[0], "name": p[1], "cid": p[2], "sid": p[3], "price": p[4]})

                # 4. Inventory
                for p_id in range(1, 11):
                    stock = 5 if p_id in [1, 4, 7] else 50 # Some low stock
                    conn.execute(text("INSERT INTO inventory (product_id, stock_level, reorder_point, last_restock_date) "
                                      "VALUES (:pid, :stock, :rp, :ldate)"),
                                 {"pid": p_id, "stock": stock, "rp": 10, "ldate": '2025-01-01'})

                # 5. Customers
                conn.execute(text("INSERT INTO customers (customer_id, first_name, last_name, email, loyalty_points, join_date) VALUES "
                                  "(1, 'John', 'Doe', 'john@example.com', 150, '2024-01-15'), "
                                  "(2, 'Jane', 'Smith', 'jane@example.com', 450, '2024-03-20'), "
                                  "(3, 'Bob', 'Wilson', 'bob@example.com', 50, '2024-05-10')"))

                # 6. Sales
                import random
                base_date = datetime.now() - timedelta(days=90)
                sales_data = []
                for day in range(90):
                    sale_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')
                    for _ in range(random.randint(1, 5)):
                        p_id = random.randint(1, 10)
                        c_id = random.randint(1, 3)
                        qty = random.randint(1, 3)
                        price = [p[4] for p in products_list if p[0] == p_id][0]
                        sales_data.append({"pid": p_id, "cid": c_id, "qty": qty, "sdate": sale_date, "rev": qty * price})

                for s in sales_data:
                    conn.execute(text("INSERT INTO sales (product_id, customer_id, quantity, sale_date, revenue) "
                                      "VALUES (:pid, :cid, :qty, :sdate, :rev)"), s)
                
                conn.commit()

            logger.info(f"Database initialized with {len(sales_data)} sales records")
        except SQLAlchemyError as e:
            logger.error(f"Error initializing sample data: {e}")
            raise # Re-raise the exception after logging

    def get_schema(self, tables: list[str] = None) -> str:
        """Get database schema universally using SQLAlchemy inspector.
        If tables is provided, only return details for those tables.
        Otherwise, return a list of all table names.
        """
        self.connect()
        inspector = inspect(self.engine)

        try:
            all_tables = inspector.get_table_names()
            
            if not tables:
                logger.info(f"Retrieved table list ({len(all_tables)} tables).")
                schema_str = "Available Tables:\n"
                for table_name in all_tables:
                    schema_str += f"   • {table_name}\n"
                schema_str += "\nUse get_database_schema tool with 'tables' parameter to see column details for specific tables."
                return schema_str

            logger.info(f"Retrieved detailed schema for {len(tables)} tables: {tables}")
            schema_str = "Detailed Database Schema:\n"
            for table_name in tables:
                if table_name not in all_tables:
                    schema_str += f"\n⚠️ Table '{table_name}' not found.\n"
                    continue
                    
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

