###generate_contracts.py

import sqlite3
import random

def calculate_batter_ovr(player):
    # Safely grab ratings, defaulting to 0 if null
    con = ((player['con_timing'] or 0) + (player['con_barrel'] or 0)) / 2
    power = ((player['pow_str'] or 0) + (player['pow_batspd'] or 0) + (player['pow_elev'] or 0)) / 3
    disc = ((player['disc_eye'] or 0) + (player['disc_restr'] or 0)) / 2
    spd = ((player['spd_sprint'] or 0) + (player['spd_inst'] or 0)) / 2
    
    # Weighting the OVR (feel free to adjust these weights!)
    return (con * 0.4) + (power * 0.3) + (disc * 0.2) + (spd * 0.1)

def calculate_pitcher_ovr(player):
    velo = ((player['pit_velo'] or 0) + (player['pit_vel_armspd'] or 0) + (player['pit_vel_decept'] or 0)) / 3
    ctrl = ((player['pit_ctrl'] or 0) + (player['pit_ctrl_acc'] or 0) + (player['pit_ctrl_cmd'] or 0)) / 3
    mov = ((player['pit_mov'] or 0) + (player['pit_mov_spin'] or 0) + (player['pit_mov_bite'] or 0)) / 3
    
    return (velo * 0.35) + (ctrl * 0.35) + (mov * 0.3)

def generate_initial_contracts():
    conn = sqlite3.connect('diamondbucs_test.db')
    conn.row_factory = sqlite3.Row # This lets us access columns by name!
    cursor = conn.cursor()
    
    try:
        # 1. Wipe the slate clean
        cursor.execute("DELETE FROM Contracts")
        
        # 2. Get all players assigned to a team
        cursor.execute("SELECT * FROM Player_Ratings WHERE team_id IS NOT NULL AND season = 1")
        players = cursor.fetchall()
        
        contracts_to_insert = []
        
        for player in players:
            player_id = player['player_id']
            team_id = player['team_id']
            age = player['age'] or 25
            position = player['position']
            
            # --- MINOR LEAGUE CONTRACTS (Under 23) ---
            if age < 23:
                cost_per_season = 100000 
                years = max(1, 23 - age)
                
            # --- MAJOR LEAGUE CONTRACTS (23 and older) ---
            else:
                # Determine if pitcher or position player based on position string
                is_pitcher = position in ['SP', 'RP', 'CP', 'P']
                
                if is_pitcher:
                    ovr = calculate_pitcher_ovr(player)
                else:
                    ovr = calculate_batter_ovr(player)
                
                # --- FA DEMAND / SALARY CURVE ---
                # Assuming ratings are roughly 1-100 scale. Adjust as needed!
                if ovr >= 80:
                    cost_per_season = random.randint(15000000, 25000000) # Superstar
                elif ovr >= 65:
                    cost_per_season = random.randint(5000000, 14000000)  # Solid Starter
                elif ovr >= 50:
                    cost_per_season = random.randint(1000000, 4000000)   # Rotation/Bench
                else:
                    cost_per_season = random.randint(500000, 900000)     # Fringe/Min
                
                # Randomize contract length so they don't all hit FA at once
                years = random.randint(1, 5)
                
            year_start = 1
            year_end = year_start + years - 1
            
            contracts_to_insert.append((
                player_id, team_id, year_start, year_end, cost_per_season, "Active"
            ))
            
        # 3. Insert the newly generated contracts
        cursor.executemany("""
            INSERT INTO Contracts (player_id, team_id, year_start, year_end, cost_per_season, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, contracts_to_insert)
        
        conn.commit()
        print(f"Successfully generated {len(contracts_to_insert)} realistic, rating-based contracts.")
        
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    generate_initial_contracts()