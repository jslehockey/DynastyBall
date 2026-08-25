import sqlite3

# The absolute path to your local SQLite DB
db_path = r'C:\Users\jsleh\Documents\SimGame\diamondbucs_test.db'

def pull_database_schema():
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query sqlite_master for all table creation scripts
        # Excluding internal sqlite tables that start with 'sqlite_'
        cursor.execute("""
            SELECT name, sql 
            FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%';
        """)
        
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in the database.")
            return

        print("=== DiamondBucs Database Schema ===\n")
        
        for table_name, schema in tables:
            print(f"--- Table: {table_name} ---")
            print(f"{schema}\n")
            
    except sqlite3.Error as e:
        print(f"An error occurred connecting to the database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    pull_database_schema()