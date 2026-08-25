import sqlite3

DATABASE_NAME = "diamondbucs_test.db"

def create_bids_table():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Create the fa_bids table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fa_bids (
                bid_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                years INTEGER NOT NULL,
                salary INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'Pending', 
                decision_day INTEGER,                 
                FOREIGN KEY(player_id) REFERENCES players_base (player_id),
                FOREIGN KEY(team_id) REFERENCES teams (team_id)
            );
        """)
        
        conn.commit()
        print("Success! The 'fa_bids' table has been created and is ready for the offseason.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_bids_table()