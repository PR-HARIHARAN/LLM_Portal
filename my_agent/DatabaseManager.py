import os
from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase

class DatabaseManager:
    def __init__(self):
        """Initialize database manager with environment variables."""
        self.db_url = "mysql+mysqlconnector://root:@127.0.0.2:3306/Student"

        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set.")

        self.engine = None
        self.db = None

    def connect_database(self):
        """Connect to the database using SQLAlchemy."""
        if self.engine is None:
            try:
                self.engine = create_engine(self.db_url, pool_recycle=3600)
                self.db = SQLDatabase(self.engine)
                return self.db
            except Exception as e:
                print(f"Database connection error: {e}")
                raise
        return self.db  # Return existing database connection

    def get_database_schema(self):
        """Retrieve database schema with table names and respective column names."""
        if self.engine is None:
            self.connect_database()

        try:
            with self.engine.connect() as connection:
                tables_query = text("SHOW TABLES")
                result = connection.execute(tables_query)
                tables = [row[0] for row in result.fetchall()]

                schema = {}
                for table in tables:
                    columns_query = text(f"SHOW COLUMNS FROM {table}")
                    columns_result = connection.execute(columns_query)
                    schema[table] = [col[0] for col in columns_result.fetchall()]

                return schema  # Returns a dictionary {table_name: [columns]}
        except Exception as e:
            print(f"Error fetching database schema: {e}")
            return "Error fetching database schema."

    def execute_read_query(self, query):
        """Execute read-only queries using the main database connection."""
        if self.engine is None:
            self.connect_database()

        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                return result.keys(), result.fetchall()
        except Exception as e:
            print(f"Error executing query: {e}")
            raise
