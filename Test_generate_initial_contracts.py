import sqlite3
import random

def generate_initial_contracts():
    conn = sqlite3.connect('diamondbucs_test.db')
    cursor = conn.cursor()
    
    try:
        # 1. Wipe the slate clean
        cursor.execute("DELETE FROM Contracts")
        
        # 2. Get all assigned players (Assuming your Players table has player_id, team_id, and age)
        cursor.execute("SELECT player_id, team_id, age FROM Player_Ratings WHERE team_id IS NOT NULL")
        players = cursor.fetchall()
        
        contracts_to_insert = []
        
        for player in players:
            player_id, team_id, age = player
            
            # --- MINOR LEAGUE CONTRACT LOGIC (Under 23) ---
            if age < 23:
                # Minimum salary, contract lasts until they turn 23 (or minimum 1 year)
                cost_per_season = 100000 
                years = max(1, 23 - age) 
                
            # --- MAJOR LEAGUE CONTRACT LOGIC (23 and older) ---
            else:
                # Placeholder: Assigning random veteran contracts between 1-5 years
                # TODO: Replace the cost calculation with your actual player rating formula
                cost_per_season = random.randint(500000, 5000000) 
                years = random.randint(1, 5)
                
            year_start = 1
            year_end = year_start + years - 1
            status = "Active" # Or whatever default status you use
            
            contracts_to_insert.append((
                player_id, team_id, year_start, year_end, cost_per_season, status
            ))
            
        # 3. Insert the newly generated contracts
        cursor.executemany("""
            INSERT INTO Contracts (player_id, team_id, year_start, year_end, cost_per_season, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, contracts_to_insert)
        
        conn.commit()
        print(f"Successfully generated {len(contracts_to_insert)} new realistic contracts.")
        
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    generate_initial_contracts()