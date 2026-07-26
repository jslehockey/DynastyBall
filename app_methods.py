import sqlite3
import os

# Grabs the absolute path of the directory this file is in
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'diamondbucs_test.db')

def get_db_connection():
    # Make sure this matches your actual database filename
    conn = sqlite3.connect(DB_PATH)
    # This row_factory lets us access columns by name (e.g., row['player_id'])
    conn.row_factory = sqlite3.Row
    return conn

def get_stamina_color(current, max_stam):
    try:
        pct = float(current) / float(max_stam)
        if pct < 0.35: return "#d32f2f" 
        if pct < 0.50: return "#f57c00" 
        return "#111111" 
    except:
        return "#111111"

def get_main_bg(val):
    val = max(50, min(99, int(val)))
    hue = int(60 - ((val - 50) * (60 / 49)))
    lightness = int(80 - ((val - 50) * (40 / 49)))
    return f"hsl({hue}, 40%, {lightness}%)"

def get_main_text(val):
    val = max(50, min(99, int(val)))
    lightness = int(80 - ((val - 50) * (40 / 49)))
    return "white" if lightness < 55 else "black"

def calculate_aggregate(sub_stats):
    values = [val for label, val in sub_stats]
    if not values: return 50 
    return int((sum(values) / len(values)) + 0.5)

def parse_player_row(row):
    clean_pos = str(row.position).strip() if row.position else ""
    is_pitcher = clean_pos in ("P", "SP", "RP", "CP")
    
    assigned_pos = getattr(row, 'assigned_pos', None) or "BENCH"
    batting_order = getattr(row, 'batting_order', None)
    if batting_order is None: batting_order = 99
    assigned_role = getattr(row, 'assigned_role', None)

    role = "Pitcher" if is_pitcher else ("Lineup" if batting_order <= 9 else "Bench")
    
    player = {
        "id": row.player_id, 
        "name": f"{row.first_name} {row.last_name}",
        "age": row.age,
        "pos": clean_pos,
        "role": role,
        "order": batting_order,
        "assigned_pos": assigned_pos,
        "assigned_role": assigned_role,
        "stam_tot": row.stam_max, 
        "stam_cur": row.stam_cur, 
        "recent_form": [int(x.strip()) for x in str(row.recent_form).split(',') if x.strip()],
        "psyche_mod": row.psyche_mod
    }
    
    if is_pitcher:
        player["vel"] = row.pit_velo
        player["vel_sub"] = [("ARM", row.pit_vel_armspd), ("DEC", row.pit_vel_decept)] 
        player["ctrl"] = row.pit_ctrl
        player["ctrl_sub"] = [("ACC", row.pit_ctrl_acc), ("CMD", row.pit_ctrl_cmd)] 
        player["mov"] = row.pit_mov
        player["mov_sub"] = [("SPN", row.pit_mov_spin), ("BIT", row.pit_mov_bite)]
        
        player["vel"] = calculate_aggregate(player["vel_sub"])
        player["ctrl"] = calculate_aggregate(player["ctrl_sub"])
        player["mov"] = calculate_aggregate(player["mov_sub"])
        
        player["stat_ip"] = row.stat_ip
        player["stat_era"] = row.stat_era
        player["stat_k"] = row.stat_k
        player["stat_bb"] = row.stat_bb
        player["stat_whip"] = row.stat_whip
    else:
        player["con"] = 0
        player["con_sub"] = [("TIM", row.con_timing), ("BAR", row.con_barrel)]
        player["pow"] = 0
        player["pow_sub"] = [("STR", row.pow_str), ("SPD", row.pow_batspd), ("ELV", row.pow_elev)]
        player["spd"] = 0
        player["spd_sub"] = [("SPR", row.spd_sprint), ("INS", row.spd_inst)]
        player["defense"] = 0
        player["defense_sub"] = [("RNG", row.def_range), ("GLV", row.def_glove), ("ARM", row.def_armstr)]
        
        player["con"] = calculate_aggregate(player["con_sub"])
        player["pow"] = calculate_aggregate(player["pow_sub"])
        player["spd"] = calculate_aggregate(player["spd_sub"])
        player["defense"] = calculate_aggregate(player["defense_sub"])

        player["stat_h"] = row.hits 
        player["stat_ab"] = row.at_bats
        player["stat_avg"] = row.batting_avg
        player["stat_hr"] = row.home_runs
        player["stat_rbi"] = row.rbis
        player["stat_ops"] = row.ops
        
    return player

def check_roster_limits(team_id, season=1):
    conn = get_db_connection()
    try:
        mlb_count = conn.execute(
            "SELECT COUNT(*) FROM Player_Ratings WHERE team_id = ? AND season = ? AND league_level = 'MLB'",
            (team_id, season)
        ).fetchone()[0]
        
        aaa_count = conn.execute(
            "SELECT COUNT(*) FROM Player_Ratings WHERE team_id = ? AND season = ? AND league_level = 'AAA'",
            (team_id, season)
        ).fetchone()[0]
        
        return {
            "mlb_count": mlb_count,
            "mlb_full": mlb_count >= 26,
            "aaa_count": aaa_count,
            "aaa_full": aaa_count >= 30,
            "org_total": mlb_count + aaa_count
        }
    finally:
        conn.close()

def get_latest_finances(team_id):
    """Retrieves the most recent financial ledger for a team."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Orders by season descending to always grab the latest ledger
    cursor.execute("""
        SELECT * FROM Team_Financials 
        WHERE team_id = ? 
        ORDER BY season DESC LIMIT 1
    """, (team_id,))
    
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {'balance': 0, 'cost_players': 0}

def get_roster_count(team_id, level="Majors"):
    """Counts active players assigned to a specific level (Majors or AAA)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # We pull from Player_Ratings for the level, and ensure it's the current season
    cursor.execute("""
        SELECT COUNT(*) 
        FROM Contracts c
        JOIN Player_Ratings pr ON c.player_id = pr.player_id
        WHERE c.team_id = ? 
          AND c.status = 'Active' 
          AND pr.league_level = ?
          AND pr.season = (SELECT MAX(season) FROM Player_Ratings)
    """, (team_id, level))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_expiring_contract_totals(team_id):
    """Groups total payroll by the number of years left on the contract."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Calculates years left as (year_end - year_start + 1)
    cursor.execute("""
        SELECT (year_end - year_start + 1) as years_left, SUM(cost_per_season) as total_value
        FROM Contracts
        WHERE team_id = ? AND status = 'Active'
        GROUP BY years_left
    """, (team_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Format the SQL results into a clean dictionary: {1: 15000000, 2: 24000000, ...}
    totals = {1: 0, 2: 0, 3: 0, "4+": 0}
    for row in rows:
        years = row[0]
        value = row[1]
        
        if years == 1:
            totals[1] += value
        elif years == 2:
            totals[2] += value
        elif years == 3:
            totals[3] += value
        else:
            totals["4+"] += value
            
    return totals

def get_full_roster_details(team_id):
    """Grabs sub-ratings, averages them into main categories, and calculates overall."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Selecting the granular ratings from the schema
    cursor.execute("""
        SELECT pb.player_id, 
               (pb.first_name || ' ' || pb.last_name) as name, 
               pr.age, 
               pr.position,
               pr.con_timing, pr.con_barrel, 
               pr.pow_str, pr.pow_batspd, pr.pow_elev,
               pr.spd_sprint, pr.spd_inst,
               pr.def_range, pr.def_react, pr.def_glove, pr.def_armstr, pr.def_armacc,
               pr.pit_velo, pr.pit_vel_armspd, pr.pit_vel_decept, 
               pr.pit_ctrl, pr.pit_ctrl_acc, pr.pit_ctrl_cmd, 
               pr.pit_mov, pr.pit_mov_spin, pr.pit_mov_bite,
               c.cost_per_season as aav, 
               (c.year_end - c.year_start + 1) as years_left
        FROM Players_Base pb
        JOIN Player_Ratings pr ON pb.player_id = pr.player_id
        JOIN Contracts c ON pb.player_id = c.player_id
        WHERE c.team_id = ? 
          AND c.status = 'Active'
          AND pr.season = (SELECT MAX(season) FROM Player_Ratings)
    """, (team_id,))
    
    def calc_avg(*args):
        """Helper to safely average numbers, ignoring None values."""
        valid_nums = [val for val in args if val is not None]
        return sum(valid_nums) / len(valid_nums) if valid_nums else 0

    players = []
    for row in cursor.fetchall():
        player = dict(row)
        is_pitcher = player['position'] in ['SP', 'RP', 'CP', 'P']
        
        if is_pitcher:
            # Roll up pitcher main categories
            vel = calc_avg(player['pit_velo'], player['pit_vel_armspd'], player['pit_vel_decept'])
            ctrl = calc_avg(player['pit_ctrl'], player['pit_ctrl_acc'], player['pit_ctrl_cmd'])
            mov = calc_avg(player['pit_mov'], player['pit_mov_spin'], player['pit_mov_bite'])
            
            # Store main stats for the frontend cards
            player['vel'] = int(round(vel))
            player['ctrl'] = int(round(ctrl))
            player['mov'] = int(round(mov))
            
            # Calculate final overall
            player['ovr'] = int(round((vel + ctrl + mov) / 3))
            
        else:
            # Roll up batter main categories
            con = calc_avg(player['con_timing'], player['con_barrel'])
            pow = calc_avg(player['pow_str'], player['pow_batspd'], player['pow_elev'])
            spd = calc_avg(player['spd_sprint'], player['spd_inst'])
            defense = calc_avg(player['def_range'], player['def_react'], player['def_glove'], player['def_armstr'], player['def_armacc'])
            
            # Store main stats for the frontend cards
            player['con'] = int(round(con))
            player['pow'] = int(round(pow))
            player['spd'] = int(round(spd))
            player['defense'] = int(round(defense))
            
            # Calculate final overall
            player['ovr'] = int(round((con + pow + spd + defense) / 4))
            
        players.append(player)
        
    conn.close()
    return players

def get_player_age(player_id):
    """Fetches a single player's most recent age."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Looks at their ratings history and grabs the age from the most recent season
    cursor.execute("""
        SELECT age 
        FROM Player_Ratings 
        WHERE player_id = ? 
        ORDER BY season DESC LIMIT 1
    """, (player_id,))
    
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None