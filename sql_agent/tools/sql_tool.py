from typing import Dict, Any
import os

from core.data_base_manager import DatabaseManager


class SQLAnalystToolkit:
    """Provides tools for Claude to use"""

    def __init__(self):
        self.db = DatabaseManager()
        self.last_result = None

    def initialize(self):
        """Set up the toolkit"""
        if not os.path.exists(self.db.db_path):
            print("Creating sample database...")
            self.db.initialize_sample_data()
        else:
            self.db.connect()
            print(f"✓ Using existing database: {self.db.db_path}")

    def get_schema(self) -> Dict[str, Any]:
        """Tool: Get database schema"""
        try:
            schema = self.db.get_schema()
            return {
                "success": True,
                "schema": schema
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def execute_query(self, query: str, explanation: str) -> Dict[str, Any]:
        """Tool: Execute SQL query"""
        print(f"\n🔍 Executing Query:")
        print(f"   SQL: {query}")
        print(f"   Purpose: {explanation}\n")

        try:
            df = self.db.execute_query(query)
            self.last_result = df

            return {
                "success": True,
                "rows_returned": len(df),
                "columns": list(df.columns),
                "data_preview": df.head(10).to_dict('records'),
                "summary": f"Successfully retrieved {len(df)} rows"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


    def cleanup(self):
        """Clean up resources"""
        self.db.close()


# Tool definitions for Claude
def get_tool_definitions():
    """Return tool definitions for Claude API"""
    return [
        {
            "name": "get_database_schema",
            "description": "Get the complete database schema showing all tables and columns. Use this when you need to understand the database structure.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "execute_sql_query",
            "description": "Execute a SQL SELECT query against the database. Returns structured data. Only SELECT queries are allowed for safety.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Valid SQL SELECT statement"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of what this query does"
                    }
                },
                "required": ["query", "explanation"]
            }
        }
    ]
