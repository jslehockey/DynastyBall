from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import ast 
from game_math import OOP_MATRIX

app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\Users\jsleh\Documents\SimGame\diamondbucs_test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- EXISTING HELPER MATH (Unchanged) ---
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
    if not values:
        return 50 
    avg = sum(values) / len(values)
    return int(avg + 0.5)

# --- DATA PARSING HELPER ---
def parse_player_row(row):
    # Strip any hidden spaces from the database string
    clean_pos = str(row.position).strip() if row.position else ""
    is_pitcher = clean_pos in ("P", "SP", "RP", "CP")
    
    # --- Fetch saved states from the database ---
    assigned_pos = getattr(row, 'assigned_pos', None) or "BENCH"
    batting_order = getattr(row, 'batting_order', None)
    if batting_order is None:
        batting_order = 99
    assigned_role = getattr(row, 'assigned_role', None)

    # Hitters with order 1-9 are Lineup, otherwise Bench.
    role = "Pitcher" if is_pitcher else ("Lineup" if batting_order <= 9 else "Bench")
    
    # Base dictionary setup
    player = {
        "name": f"{row.first_name} {row.last_name}",
        "pos": clean_pos,
        "role": role,
        "order": batting_order,
        "assigned_pos": assigned_pos,
        "assigned_role": assigned_role,
        
        "stam_cur": 100, 
        "stam_tot": 100, 
        
        "recent_form": [int(x.strip()) for x in str(row.recent_form).split(',') if x.strip()],
        "psyche_mod": row.psyche_mod
    }
    
    if is_pitcher:
        # Pitchers
        player["vel"] = 0
        player["vel_sub"] = [("ARM", row.def_armstr), ("DEC", row.spd_sprint)] 
        
        player["ctrl"] = 0
        player["ctrl_sub"] = [("ACC", row.def_armacc), ("CMD", row.def_glove)] 
        
        player["mov"] = 0
        player["mov_sub"] = [("SPN", row.def_range), ("BIT", row.def_react)]
        
        player["vel"] = calculate_aggregate(player["vel_sub"])
        player["ctrl"] = calculate_aggregate(player["ctrl_sub"])
        player["mov"] = calculate_aggregate(player["mov_sub"])
        
        player["stat_ip"] = row.stat_ip
        player["stat_era"] = row.stat_era
        player["stat_k"] = row.stat_k
        player["stat_bb"] = row.stat_bb
        player["stat_whip"] = row.stat_whip
        
    else:
        # Hitters
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

    
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/major-league")
def major_league():
    # 1. Fetch Team Details
    team_query = text("SELECT nickname, color_primary, color_secondary FROM Teams WHERE team_id = 'Alpha-0001'")
    team = db.session.execute(team_query).fetchone()

    # 2. Fetch the Active Roster (Single Query for ALL players, hitting and pitching)
    roster_query = text("""
        SELECT b.first_name, b.last_name, r.position, r.recent_form, r.psyche_mod,
               r.con_timing, r.con_barrel, r.pow_str, r.pow_batspd, r.pow_elev,
               r.spd_sprint, r.spd_inst, r.def_range, r.def_glove, r.def_react, 
               r.def_armstr, r.def_armacc,
               
               r.assigned_pos, r.batting_order, r.assigned_role,
               
               -- Hitting Stats
               COALESCE(sh.h, 0) as hits,
               COALESCE(sh.ab, 0) as at_bats,
               COALESCE(sh.avg, '.000') as batting_avg,
               COALESCE(sh.hr, 0) as home_runs,
               COALESCE(sh.rbi, 0) as rbis,
               COALESCE(sh.ops, '.000') as ops,
               
               -- Pitching Stats
               COALESCE(sp.ip, '0.0') as stat_ip,
               COALESCE(sp.era, '0.00') as stat_era,
               COALESCE(sp.k, 0) as stat_k,
               COALESCE(sp.bb, 0) as stat_bb,
               COALESCE(sp.whip, '0.00') as stat_whip
        FROM Players_Base b
        JOIN Player_Ratings r ON b.player_id = r.player_id
        LEFT JOIN Stats_Hitting sh ON b.player_id = sh.player_id AND sh.season = 2026
        LEFT JOIN Stats_Pitching sp ON b.player_id = sp.player_id AND sp.season = 2026
        WHERE r.team_id = 'Alpha-0001' AND r.season = 2026
    """)
    raw_roster = db.session.execute(roster_query).fetchall()

    # 3. Parse the SQL data
    processed_players = [parse_player_row(row) for row in raw_roster]

    # 4. Sort Hitters
    lineup = sorted([p for p in processed_players if p["role"] == "Lineup"], key=lambda x: x["order"])
    bench = [p for p in processed_players if p["role"] == "Bench"]
    
    # 5. Sort Pitchers into Roles
    raw_pitchers = [p for p in processed_players if p["role"] == "Pitcher"]
    pitcher_buckets = {'SP': [], 'LR': [], 'MR': [], 'SU': [], 'CL': []}
    unassigned_pitchers = []
    
    for p in raw_pitchers:
        role_prefix = str(p['assigned_role'])[:2] if p['assigned_role'] else None
        if role_prefix in pitcher_buckets:
            pitcher_buckets[role_prefix].append(p)
        else:
            unassigned_pitchers.append(p)

    # First-load fallback: if DB is empty/null, chunk them like we did before
    if not any(pitcher_buckets.values()):
        pitcher_buckets['SP'] = unassigned_pitchers[:5]
        pitcher_buckets['LR'] = unassigned_pitchers[5:]
    else:
        pitcher_buckets['LR'].extend(unassigned_pitchers) # Dump any stragglers in Long Relief
        
    # Sort inside buckets by their label (SP1, SP2, etc.)
    for k in pitcher_buckets:
        pitcher_buckets[k] = sorted(pitcher_buckets[k], key=lambda x: str(x.get('assigned_role')))

    valid_positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]

    return render_template(
        "major_league.html",
        team_nickname=f"Washington {team.nickname}",
        team_color_1=team.color_primary, 
        team_color_2=team.color_secondary,
        get_stamina_color=get_stamina_color,
        get_main_bg=get_main_bg,
        get_main_text=get_main_text,
        lineup=lineup,
        bench=bench,
        pitcher_buckets=pitcher_buckets, 
        positions=valid_positions,
        oop_matrix=OOP_MATRIX
    )

# --- SAVE ROSTER ROUTE ---
@app.route('/save_roster', methods=['POST'])
def save_roster():
    data = request.json
    hitters = data.get('hitters', [])
    pitchers = data.get('pitchers', [])

    try:
        # Save hitters
        for h in hitters:
            first_name, last_name = h['name'].split(' ', 1)
            player_query = text("SELECT player_id FROM Players_Base WHERE first_name = :fname AND last_name = :lname")
            pid_result = db.session.execute(player_query, {'fname': first_name, 'lname': last_name}).scalar()
            
            if pid_result:
                update_query = text("""
                    UPDATE Player_Ratings 
                    SET assigned_pos = :pos, batting_order = :order 
                    WHERE player_id = :pid AND season = 2026 AND team_id = 'Alpha-0001'
                """)
                db.session.execute(update_query, {'pos': h['assigned_pos'], 'order': h['batting_order'], 'pid': pid_result})

        # Save pitchers
        for p in pitchers:
            first_name, last_name = p['name'].split(' ', 1)
            player_query = text("SELECT player_id FROM Players_Base WHERE first_name = :fname AND last_name = :lname")
            pid_result = db.session.execute(player_query, {'fname': first_name, 'lname': last_name}).scalar()
            
            if pid_result:
                update_query = text("""
                    UPDATE Player_Ratings 
                    SET assigned_role = :role 
                    WHERE player_id = :pid AND season = 2026 AND team_id = 'Alpha-0001'
                """)
                db.session.execute(update_query, {'role': p['role'], 'pid': pid_result})

        db.session.commit()
        return jsonify({'status': 'success'})

    except Exception as e:
        print(f"Error saving: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == "__main__":
    app.run(debug=True)