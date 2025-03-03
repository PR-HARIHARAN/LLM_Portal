import os
from my_agent.DatabaseManager import DatabaseManager  # Ensure correct filename casing

# Set environment variables (For testing only; prefer setting them in the system)
os.environ["DATABASE_URL"] = "mysql+mysqlconnector://root:@127.0.0.2:3306/Student"

def main():
    # Create an instance of DatabaseManager
    db_manager = DatabaseManager()

    try:
        # Connect to the database
        db_manager.connect_database
        print("✅ Connected to the database!")

        # Fetch and print database schema (tables)
        tables = db_manager.get_database_schema()
        if tables:
            print("\n📌 Tables in the database:")
            for table in tables:
                print(f"- {table}")
        else:
            print("⚠️ No tables found.")

    except Exception as e:
        print(f"❌ Error: {e}")

    print(db_manager.execute_read_query("select * from student.studentperformance;"))

if __name__ == "__main__":
    main()
