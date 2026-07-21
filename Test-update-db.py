import sqlite3

# Point this directly to your database
db_path = r'C:\Users\jsleh\Documents\SimGame\diamondbucs_test.db'

def update_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    columns_to_add = [
        "ALTER TABLE Player_Ratings ADD COLUMN assigned_pos TEXT DEFAULT 'BENCH'",
        "ALTER TABLE Player_Ratings ADD COLUMN batting_order INTEGER DEFAULT 99",
        "ALTER TABLE Player_Ratings ADD COLUMN assigned_role TEXT"
    ]

    for query in columns_to_add:
        try:
            cursor.execute(query)
            print(f"Success: {query}")
        except sqlite3.OperationalError as e:
            # If the column already exists, SQLite throws an OperationalError. We can safely ignore it.
            print(f"Skipped (already exists): {query}")

    conn.commit()
    conn.close()
    print("Database update complete!")

if __name__ == "__main__":
    update_database()