import sqlite3
import random

def master_finance_reset():
    conn = sqlite3.connect('diamondbucs_test.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # ==========================================
        # STEP 1: CLEAR OLD DATA
        # ==========================================
        cursor.execute("DELETE FROM Contracts")
        cursor.execute("DELETE FROM Team_Financials")
        cursor.execute("DELETE FROM stats_hitting")
        cursor.execute("DELETE FROM stats_pitching")
        
        # ==========================================
        # STEP 2: GENERATE REALISTIC CONTRACTS & STATS
        # ==========================================
        cursor.execute("SELECT * FROM Player_Ratings WHERE team_id IS NOT NULL AND season = 1")
        players = cursor.fetchall()
        
        contracts_to_insert = []
        hitting_stats = []
        pitching_stats = []
        
        contract_id_counter = 1
        stat_id_counter = 1
        
        for p in players:
            pid = p['player_id']
            tid = p['team_id']
            age = p['age'] or 25
            pos = p['position']
            
            # --- 2A: CONTRACT LOGIC ---
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
                
                # Your exact pseudo-code formula for salary!
                aav = 750000 + (max(0, (ovr - 55)) ** 2.5) * 3500
                
                # Randomize all Major League contracts between 1 and 4 years
                years = random.randint(1, 4)
            
            year_start = 1
            year_end = year_start + years - 1
            
            # Note: Adding contract_id_counter for the primary key
            contracts_to_insert.append((contract_id_counter, pid, tid, year_start, year_end, int(aav), 'Active'))
            contract_id_counter += 1

            # --- 2B: BASELINE STATS LOGIC ---
            is_pitcher = pos in ['SP', 'RP', 'CP', 'P', 'MR', 'LR', 'SU', 'CL']
            
            if not is_pitcher:
                ab = random.randint(200, 600)
                hits = int(ab * random.uniform(0.220, 0.310))
                doubles = int(hits * random.uniform(0.15, 0.25))
                triples = random.randint(0, 5)
                hr = random.randint(5, 35)
                singles = hits - (doubles + triples + hr)
                
                bb = random.randint(20, 80)
                pa = ab + bb
                k = random.randint(40, 150)
                rbi = int(hr * random.uniform(1.5, 3.0))
                
                avg = round(hits / ab, 3) if ab > 0 else 0.000
                obp = round((hits + bb) / pa, 3) if pa > 0 else 0.000
                tb = singles + (2 * doubles) + (3 * triples) + (4 * hr)
                slg = round(tb / ab, 3) if ab > 0 else 0.000
                ops = round(obp + slg, 3)

                hitting_stats.append((
                    stat_id_counter, pid, 1, 'Regular Season',
                    140, pa, ab, int(hits*0.4), hits, singles, doubles, triples, 
                    hr, rbi, bb, 0, k, random.randint(0, 20), random.randint(0, 5),
                    avg, obp, slg, ops
                ))
            else:
                ip = round(random.uniform(50.0, 200.0), 1)
                ip_calc = int(ip) + ((ip % 1) * 3.33) 
                
                era_base = random.uniform(2.50, 5.50)
                er = int((era_base * ip_calc) / 9)
                r = er + random.randint(0, 5)
                
                hits_allowed = int(ip_calc * random.uniform(0.7, 1.2))
                bb_allowed = int(ip_calc * random.uniform(0.2, 0.5))
                k_pitch = int(ip_calc * random.uniform(0.6, 1.3))
                hr_allowed = random.randint(5, 25)
                
                whip = round((hits_allowed + bb_allowed) / ip_calc, 2) if ip_calc > 0 else 0.00
                era = round((er * 9) / ip_calc, 2) if ip_calc > 0 else 0.00
                
                pitching_stats.append((
                    stat_id_counter, pid, 1, 'Regular Season',
                    30, random.randint(2, 15), random.randint(2, 15), random.randint(0, 30), 0, 0,
                    ip, hits_allowed, r, er, hr_allowed, bb_allowed, 0, k_pitch, 
                    int(ip_calc * 15), 0, 0, era, whip, 0.00
                ))

            stat_id_counter += 1
            
        cursor.executemany("""
            INSERT INTO Contracts (contract_id, player_id, team_id, year_start, year_end, cost_per_season, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, contracts_to_insert)

        cursor.executemany("""
            INSERT INTO stats_hitting (
                stat_id, player_id, season, competition, g, pa, ab, r, h, "1b", "2b", "3b", hr, rbi, bb, hbp, k, sb, cs, avg, obp, slg, ops
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, hitting_stats)

        cursor.executemany("""
            INSERT INTO stats_pitching (
                stat_id, player_id, season, competition, g, w, l, sv, hld, bs, ip, h, r, er, hr, bb, hbp, k, pitches, cg, sho, era, whip, fip
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, pitching_stats)
        
        # ==========================================
        # STEP 3: INITIALIZE & SYNC TEAM FINANCIALS
        # ==========================================
        # Since we deleted the table above, we need to INSERT fresh rows before we can UPDATE them
        financials_to_insert = []
        for tid in range(1, 11):
            financials_to_insert.append((
                tid, tid, 1, 150000000, 0, 0, 0, 0, 0, 0
            ))
            
        cursor.executemany("""
            INSERT INTO Team_Financials (
                financial_id, team_id, season, balance, players_on_contract, cost_players, income_fa_cup, income_media, income_adwatch, income_attendance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, financials_to_insert)
        
        cursor.execute("""
            UPDATE Team_Financials
            SET 
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
            # Format the output nicely
            formatted_payroll = f"${row['cost_players']:,}"
            formatted_balance = f"${row['balance']:,}"
            print(f"{str(row['team_id']):<15} | {formatted_balance:<12} | {str(row['players_on_contract']):<12} | {formatted_payroll}")
            
    except Exception as e:
        print(f"Error during reset: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    master_finance_reset()