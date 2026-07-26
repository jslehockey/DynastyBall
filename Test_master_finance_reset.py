import sqlite3

def master_finance_reset():
    conn = sqlite3.connect('diamondbucs_test.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # ==========================================
        # STEP 1: CLEAR OLD CONTRACTS
        # ==========================================
        cursor.execute("DELETE FROM Contracts")
        
        # ==========================================
        # STEP 2: GENERATE REALISTIC CONTRACTS
        # ==========================================
        cursor.execute("SELECT * FROM Player_Ratings WHERE team_id IS NOT NULL AND season = 1")
        players = cursor.fetchall()
        contracts_to_insert = []
        
        for p in players:
            pid = p['player_id']
            tid = p['team_id']
            age = p['age'] or 25
            pos = p['position']
            
            # Minor Leaguers (Under 23)
            if age < 23:
                aav = 100000
                years = max(1, 23 - age)
                
            # Major Leaguers (23+)
            else:
                # Calculate OVR based on position
                if pos in ['SP', 'RP', 'CP', 'P', 'MR', 'LR', 'SU', 'CL']:
                    vel = p['pit_velo'] or 0
                    ctrl = p['pit_ctrl'] or 0
                    mov = p['pit_mov'] or 0
                    ovr = (vel + ctrl + mov) / 3
                else:
                    con = ((p['con_timing'] or 0) + (p['con_barrel'] or 0)) / 2
                    pow = ((p['pow_str'] or 0) + (p['pow_batspd'] or 0) + (p['pow_elev'] or 0)) / 3
                    spd = ((p['spd_sprint'] or 0) + (p['spd_inst'] or 0)) / 2
                    defe = ((p['def_range'] or 0) + (p['def_glove'] or 0) + (p['def_react'] or 0)) / 3
                    ovr = (con + pow + spd + defe) / 4
                
                #Use YOUR exact pseudo-code formula for salary!
                aav = 750000 + (max(0, (ovr - 55)) ** 2.5) * 3500
                
                # Randomize all Major League contracts between 1 and 4 years
                years = random.randint(1, 4)
            
            year_start = 1
            year_end = year_start + years - 1
            contracts_to_insert.append((pid, tid, year_start, year_end, int(aav), 'Active'))
            
        cursor.executemany("""
            INSERT INTO Contracts (player_id, team_id, year_start, year_end, cost_per_season, status) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, contracts_to_insert)
        
        # ==========================================
        # STEP 3: SYNC TEAM FINANCIALS
        # ==========================================
        cursor.execute("""
            UPDATE Team_Financials
            SET 
                balance = 85000000, income_fa_cup = 0, income_media = 0, income_adwatch = 0, income_attendance = 0,
                players_on_contract = (SELECT COUNT(*) FROM Contracts WHERE Contracts.team_id = Team_Financials.team_id),
                cost_players = (SELECT COALESCE(SUM(cost_per_season), 0) FROM Contracts WHERE Contracts.team_id = Team_Financials.team_id)
            WHERE season = 1;
        """)
        
        conn.commit()
        
        # ==========================================
        # VERIFY RESULTS
        # ==========================================
        cursor.execute("SELECT team_id, balance, players_on_contract, cost_players FROM Team_Financials WHERE season = 1")
        print("\n--- MASTER RESET COMPLETE ---")
        print(f"{'Team ID':<15} | {'Balance':<12} | {'Roster Size':<12} | {'Total Payroll'}")
        print("-" * 65)
        for row in cursor.fetchall():
            print(f"{str(row['team_id']):<15} | ${str(row['balance']):<11} | {str(row['players_on_contract']):<12} | ${str(row['cost_players'])}")
            
    except Exception as e:
        print(f"Error during reset: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    master_finance_reset()