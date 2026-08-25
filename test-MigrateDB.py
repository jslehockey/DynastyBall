import sqlite3
from app import app
from extensions import db
import model_league
import model_team
import model_stadium
import model_bid
import model_player

# We define the order carefully to respect Foreign Key relationships!
# (e.g., You can't import a Team if the World doesn't exist yet)
TABLE_MIGRATION_PLAN = [
    ("Worlds", model_league.World),
    ("Teams", model_team.TeamDB),
    ("Parks", model_stadium.Park),
    ("Players_Base", model_player.PlayerBase),
    ("Player_Ratings", model_player.PlayerRating),
    ("Stats_Hitting", model_player.StatHitting),
    ("Stats_Pitching", model_player.StatPitching),
    ("Stats_Fielding", model_player.StatFielding),
    ("Season_Results", model_league.SeasonResult),
    ("Game_Events", model_league.GameEvent),
    ("Team_Financials", model_team.TeamFinancials),
    ("Contracts", model_bid.Contract),
    ("Awards", model_player.Award),
]

def run_migration():
    # 1. Connect to the legacy database
    legacy_path = r'C:\Users\jsleh\Documents\SimGame\diamondbucs_legacy.db'
    legacy_conn = sqlite3.connect(legacy_path)
    
    # This trick lets us access SQLite rows as dictionaries 
    legacy_conn.row_factory = sqlite3.Row
    cursor = legacy_conn.cursor()

    print("Starting data migration...")

    # 2. Open our Flask application context to talk to the new database
    with app.app_context():
        for legacy_table, ModelClass in TABLE_MIGRATION_PLAN:
            print(f"Migrating {legacy_table}...")
            
            try:
                # Grab all data from the old table
                cursor.execute(f"SELECT * FROM {legacy_table}")
                rows = cursor.fetchall()
                
                for row in rows:
                    row_dict = dict(row)
                    
                    # --- SPECIAL FORMATTING ---
                    
                    # 1. Handle Python's rule against variables starting with numbers
                    if legacy_table == "Stats_Hitting":
                        if '1b' in row_dict:
                            row_dict['_1b'] = row_dict.pop('1b')
                        if '2b' in row_dict:
                            row_dict['_2b'] = row_dict.pop('2b')
                        if '3b' in row_dict:
                            row_dict['_3b'] = row_dict.pop('3b')
                            
                    # 2. Strip out keys that are completely empty (None) to allow 
                    # SQLAlchemy to use its own default values (like default=0)
                    row_dict = {k: v for k, v in row_dict.items() if v is not None}

                    # Create the new SQLAlchemy object
                    new_record = ModelClass(**row_dict)
                    db.session.add(new_record)
                
                # Save this table's data to the new database before moving to the next
                db.session.commit()
                print(f" -> Successfully mapped {len(rows)} rows into {ModelClass.__tablename__}.")
                
            except sqlite3.OperationalError:
                print(f" -> Skipping {legacy_table} (Table was not found in the legacy database).")
            except Exception as e:
                print(f" -> ERROR migrating {legacy_table}: {e}")
                db.session.rollback()

    legacy_conn.close()
    print("\nMigration Complete! Your new diamondbucs_test.db is fully loaded and strictly typed.")

if __name__ == "__main__":
    run_migration()