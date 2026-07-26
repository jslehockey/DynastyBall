from flask import Blueprint, render_template, request, redirect, url_for, jsonify, abort, flash
from sqlalchemy import text
import sqlite3
from model_player import Player
from model_bid import Bid
from finance_engine import validate_bid
import json

# Import the db instance from your main app
from extensions import db 

# Import all your logic from the new toolbox
from app_methods import (
    get_db_connection, get_stamina_color, get_main_bg, 
    get_main_text, parse_player_row, check_roster_limits,
    get_latest_finances, get_full_roster_details, get_player_age,
    get_expiring_contract_totals, get_roster_count
)
from game_math import OOP_MATRIX

# Initialize the Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def home():
    return render_template("index.html")

@main_bp.route("/major-league")
def major_league():
    team_query = text("SELECT nickname, color_primary, color_secondary FROM Teams WHERE team_id = 'Alpha-0001'")
    team = db.session.execute(team_query).fetchone()

    roster_query = text("""
        SELECT b.first_name, b.last_name, b.player_id, r.age, r.position, r.recent_form, r.psyche_mod,
               r.stam_max, r.stam_cur, r.assigned_pos, r.batting_order, r.assigned_role,
               
               r.con_timing, r.con_barrel, r.pow_str, r.pow_batspd, r.pow_elev,
               r.spd_sprint, r.spd_inst, r.def_range, r.def_glove, r.def_react, r.def_armstr, r.def_armacc,
               
               r.pit_velo, r.pit_vel_armspd, r.pit_vel_decept, r.pit_ctrl, r.pit_ctrl_acc, 
               r.pit_ctrl_cmd, r.pit_mov, r.pit_mov_spin, r.pit_mov_bite,
               
               COALESCE(sh.h, 0) as hits, COALESCE(sh.ab, 0) as at_bats,
               COALESCE(sh.avg, '.000') as batting_avg, COALESCE(sh.hr, 0) as home_runs,
               COALESCE(sh.rbi, 0) as rbis, COALESCE(sh.ops, '.000') as ops,
               
               COALESCE(sp.ip, '0.0') as stat_ip, COALESCE(sp.era, '0.00') as stat_era,
               COALESCE(sp.k, 0) as stat_k, COALESCE(sp.bb, 0) as stat_bb,
               COALESCE(sp.whip, '0.00') as stat_whip
               
        FROM Players_Base b
        JOIN Player_Ratings r ON b.player_id = r.player_id
        LEFT JOIN Stats_Hitting sh ON b.player_id = sh.player_id AND sh.season = 1
        LEFT JOIN Stats_Pitching sp ON b.player_id = sp.player_id AND sp.season = 1
        WHERE r.team_id = 'Alpha-0001' AND r.season = 1 AND r.league_level = 'MLB'
    """)
    raw_roster = db.session.execute(roster_query).fetchall()

    processed_players = [parse_player_row(row) for row in raw_roster]

    lineup = sorted([p for p in processed_players if p["role"] == "Lineup"], key=lambda x: x["order"])
    bench = [p for p in processed_players if p["role"] == "Bench"]
    
    raw_pitchers = [p for p in processed_players if p["role"] == "Pitcher"]
    pitcher_buckets = {'SP': [], 'LR': [], 'MR': [], 'SU': [], 'CL': []}
    unassigned_pitchers = []
    
    for p in raw_pitchers:
        role_prefix = str(p['assigned_role'])[:2] if p['assigned_role'] else None
        if role_prefix in pitcher_buckets:
            pitcher_buckets[role_prefix].append(p)
        else:
            unassigned_pitchers.append(p)

    if not any(pitcher_buckets.values()):
        pitcher_buckets['SP'] = unassigned_pitchers[:5]
        pitcher_buckets['LR'] = unassigned_pitchers[5:]
    else:
        pitcher_buckets['LR'].extend(unassigned_pitchers)
        
    for k in pitcher_buckets:
        pitcher_buckets[k] = sorted(pitcher_buckets[k], key=lambda x: str(x.get('assigned_role')))

    valid_positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]

    limits = check_roster_limits('Alpha-0001', 1)

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
        oop_matrix=OOP_MATRIX,
        limits=limits
    )

@main_bp.route("/minor-league")
def minor_league():
    team_query = text("SELECT nickname, color_primary, color_secondary FROM Teams WHERE team_id = 'Alpha-0001'")
    team = db.session.execute(team_query).fetchone()

    roster_query = text("""
        SELECT b.first_name, b.last_name, b.player_id, r.age, r.position, r.recent_form, r.psyche_mod,
               r.stam_max, r.stam_cur, r.assigned_pos, r.batting_order, r.assigned_role,
               
               r.con_timing, r.con_barrel, r.pow_str, r.pow_batspd, r.pow_elev,
               r.spd_sprint, r.spd_inst, r.def_range, r.def_glove, r.def_react, r.def_armstr, r.def_armacc,
               
               r.pit_velo, r.pit_vel_armspd, r.pit_vel_decept, r.pit_ctrl, r.pit_ctrl_acc, 
               r.pit_ctrl_cmd, r.pit_mov, r.pit_mov_spin, r.pit_mov_bite,
               
               COALESCE(sh.h, 0) as hits, COALESCE(sh.ab, 0) as at_bats,
               COALESCE(sh.avg, '.000') as batting_avg, COALESCE(sh.hr, 0) as home_runs,
               COALESCE(sh.rbi, 0) as rbis, COALESCE(sh.ops, '.000') as ops,
               
               COALESCE(sp.ip, '0.0') as stat_ip, COALESCE(sp.era, '0.00') as stat_era,
               COALESCE(sp.k, 0) as stat_k, COALESCE(sp.bb, 0) as stat_bb,
               COALESCE(sp.whip, '0.00') as stat_whip
               
        FROM Players_Base b
        JOIN Player_Ratings r ON b.player_id = r.player_id
        LEFT JOIN Stats_Hitting sh ON b.player_id = sh.player_id AND sh.season = 1
        LEFT JOIN Stats_Pitching sp ON b.player_id = sp.player_id AND sp.season = 1
        WHERE r.team_id = 'Alpha-0001' AND r.season = 1 AND r.league_level = 'AAA'
    """)
    raw_roster = db.session.execute(roster_query).fetchall()

    processed_players = [parse_player_row(row) for row in raw_roster]

    lineup = sorted([p for p in processed_players if p["role"] == "Lineup"], key=lambda x: x["order"])
    bench = [p for p in processed_players if p["role"] == "Bench"]
    
    raw_pitchers = [p for p in processed_players if p["role"] == "Pitcher"]
    pitcher_buckets = {'SP': [], 'LR': [], 'MR': [], 'SU': [], 'CL': []}
    unassigned_pitchers = []
    
    for p in raw_pitchers:
        role_prefix = str(p['assigned_role'])[:2] if p['assigned_role'] else None
        if role_prefix in pitcher_buckets:
            pitcher_buckets[role_prefix].append(p)
        else:
            unassigned_pitchers.append(p)

    if not any(pitcher_buckets.values()):
        pitcher_buckets['SP'] = unassigned_pitchers[:5]
        pitcher_buckets['LR'] = unassigned_pitchers[5:]
    else:
        pitcher_buckets['LR'].extend(unassigned_pitchers)
        
    for k in pitcher_buckets:
        pitcher_buckets[k] = sorted(pitcher_buckets[k], key=lambda x: str(x.get('assigned_role')))

    valid_positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]

    limits = check_roster_limits('Alpha-0001', 1)

    return render_template(
        "minor_league.html",
        team_nickname=f"Washington {team.nickname} (AAA)",
        team_color_1=team.color_primary, 
        team_color_2=team.color_secondary,
        get_stamina_color=get_stamina_color,
        get_main_bg=get_main_bg,
        get_main_text=get_main_text,
        lineup=lineup,
        bench=bench,
        pitcher_buckets=pitcher_buckets, 
        positions=valid_positions,
        oop_matrix=OOP_MATRIX,
        limits=limits
    )

@main_bp.route('/save_roster', methods=['POST'])
def save_roster():
    data = request.json
    hitters = data.get('hitters', [])
    pitchers = data.get('pitchers', [])

    try:
        for h in hitters:
            player_query = text("SELECT player_id FROM Players_Base WHERE TRIM(first_name || ' ' || COALESCE(last_name, '')) = :fullname")
            pid_result = db.session.execute(player_query, {'fullname': h['name']}).scalar()
            
            if pid_result:
                update_query = text("""
                    UPDATE Player_Ratings 
                    SET assigned_pos = :pos, batting_order = :order 
                    WHERE player_id = :pid AND season = 1 AND team_id = 'Alpha-0001'
                """)
                db.session.execute(update_query, {'pos': h['assigned_pos'], 'order': h['batting_order'], 'pid': pid_result})

        for p in pitchers:
            player_query = text("SELECT player_id FROM Players_Base WHERE TRIM(first_name || ' ' || COALESCE(last_name, '')) = :fullname")
            pid_result = db.session.execute(player_query, {'fullname': p['name']}).scalar()
            
            if pid_result:
                update_query = text("""
                    UPDATE Player_Ratings 
                    SET assigned_role = :role 
                    WHERE player_id = :pid AND season = 1 AND team_id = 'Alpha-0001'
                """)
                db.session.execute(update_query, {'role': p['role'], 'pid': pid_result})

        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error saving: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    
@main_bp.route("/call_ups")
def call_ups():
    team_query = text("SELECT nickname, color_primary, color_secondary FROM Teams WHERE team_id = 'Alpha-0001'")
    team = db.session.execute(team_query).fetchone()

    roster_query = text("""
        SELECT b.first_name, b.last_name, b.player_id, r.age, r.league_level, r.position, r.recent_form, r.psyche_mod,
               r.stam_max, r.stam_cur, r.assigned_pos, r.batting_order, r.assigned_role,
               r.con_timing, r.con_barrel, r.pow_str, r.pow_batspd, r.pow_elev,
               r.spd_sprint, r.spd_inst, r.def_range, r.def_glove, r.def_react, r.def_armstr, r.def_armacc,
               r.pit_velo, r.pit_vel_armspd, r.pit_vel_decept, r.pit_ctrl, r.pit_ctrl_acc, 
               r.pit_ctrl_cmd, r.pit_mov, r.pit_mov_spin, r.pit_mov_bite,
               COALESCE(sh.h, 0) as hits, COALESCE(sh.ab, 0) as at_bats,
               COALESCE(sh.avg, '.000') as batting_avg, COALESCE(sh.hr, 0) as home_runs,
               COALESCE(sh.rbi, 0) as rbis, COALESCE(sh.ops, '.000') as ops,
               COALESCE(sp.ip, '0.0') as stat_ip, COALESCE(sp.era, '0.00') as stat_era,
               COALESCE(sp.k, 0) as stat_k, COALESCE(sp.bb, 0) as stat_bb,
               COALESCE(sp.whip, '0.00') as stat_whip
        FROM Players_Base b
        JOIN Player_Ratings r ON b.player_id = r.player_id
        LEFT JOIN Stats_Hitting sh ON b.player_id = sh.player_id AND sh.season = 1
        LEFT JOIN Stats_Pitching sp ON b.player_id = sp.player_id AND sp.season = 1
        WHERE r.team_id = 'Alpha-0001' AND r.season = 1
        ORDER BY r.position ASC, b.last_name ASC
    """)
    raw_roster = db.session.execute(roster_query).fetchall()

    mlb_roster = []
    aaa_roster = []

    for row in raw_roster:
        p = parse_player_row(row)
        p['id'] = row.player_id
        
        if p['role'] == 'Pitcher':
            p['ovr'] = int((p['vel'] + p['ctrl'] + p['mov']) / 3)
        else:
            p['ovr'] = int((p['con'] + p['pow'] + p['spd'] + p['defense']) / 4)

        if row.league_level == 'MLB':
            mlb_roster.append(p)
        else:
            aaa_roster.append(p)

    mlb_max = 26
    slots_open = mlb_max - len(mlb_roster)
    
    if slots_open > 0:
        for _ in range(slots_open):
            mlb_roster.insert(0, {
                'id': 'EMPTY',
                'name': '[ EMPTY ROSTER SLOT ]',
                'pos': '--',
                'age': '--',
                'ovr': 0,
                'stam_cur': 0,
                'stam_tot': 0,
                'role': 'Empty'
            })
    
    limits = check_roster_limits('Alpha-0001', 1)

    return render_template(
        "call_ups.html",
        team_nickname=f"Washington {team.nickname} Front Office",
        team_color_1=team.color_primary, 
        team_color_2=team.color_secondary,
        get_stamina_color=get_stamina_color,
        get_main_bg=get_main_bg,
        get_main_text=get_main_text,
        mlb_roster=mlb_roster,
        aaa_roster=aaa_roster,
        limits=limits
    )

@main_bp.route("/swap_players", methods=["POST"])
def swap_players():
    current_season = 1 
    
    mlb_id = request.form.get("mlb_player_id")
    aaa_id = request.form.get("aaa_player_id")
    
    if not aaa_id:
        return redirect(url_for("main.call_ups"))

    # --- NEW: HARD CAP CHECK ---
    limits = check_roster_limits('Alpha-0001', current_season)
    
    # If they are trying to promote a player to an EMPTY slot, but MLB is full, block it.
    if (not mlb_id or mlb_id == "EMPTY") and limits['mlb_full']:
        print("Blocked: MLB Roster is full.")
        return redirect(url_for("main.call_ups"))
    # ---------------------------

    conn = get_db_connection()
    
    try:
        if mlb_id and mlb_id != "EMPTY":
            conn.execute(
                "UPDATE Player_Ratings SET league_level = 'AAA' WHERE player_id = ? AND season = ?",
                (mlb_id, current_season)
            )
        
        conn.execute(
            "UPDATE Player_Ratings SET league_level = 'MLB' WHERE player_id = ? AND season = ?",
            (aaa_id, current_season)
        )
        
        conn.commit()
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error during swap: {e}")
        
    finally:
        conn.close()
        
    return redirect(url_for("main.call_ups"))

@main_bp.route("/player/<string:player_id>")
def player_profile(player_id):
    current_season = 1  # Standardizing the current season variable
    
    # 1. Fetch player using raw SQL
    query = text("""
        SELECT b.first_name, b.last_name, b.player_id, r.age, r.league_level, r.position, r.assigned_role,
               r.team_id, t.nickname as team_name,
               
               -- Fields needed for parse_player_row
               r.recent_form, r.psyche_mod, r.stam_max, r.stam_cur, r.assigned_pos, r.batting_order,
               r.con_timing, r.con_barrel, r.pow_str, r.pow_batspd, r.pow_elev,
               r.spd_sprint, r.spd_inst, r.def_range, r.def_glove, r.def_react, r.def_armstr, r.def_armacc,
               r.pit_velo, r.pit_vel_armspd, r.pit_vel_decept, r.pit_ctrl, r.pit_ctrl_acc, 
               r.pit_ctrl_cmd, r.pit_mov, r.pit_mov_spin, r.pit_mov_bite,
               
               -- Basic Stats
               COALESCE(sh.h, 0) as hits, COALESCE(sh.ab, 0) as at_bats,
               COALESCE(sh.avg, '.000') as batting_avg, COALESCE(sh.hr, 0) as home_runs,
               COALESCE(sh.rbi, 0) as rbis, COALESCE(sh.ops, '.000') as ops,
               
               COALESCE(sp.ip, '0.0') as stat_ip, COALESCE(sp.era, '0.00') as stat_era,
               COALESCE(sp.k, 0) as stat_k, COALESCE(sp.bb, 0) as stat_bb,
               COALESCE(sp.whip, '0.00') as stat_whip
               
        FROM Players_Base b
        JOIN Player_Ratings r ON b.player_id = r.player_id
        LEFT JOIN Teams t ON r.team_id = t.team_id
        LEFT JOIN Stats_Hitting sh ON b.player_id = sh.player_id AND sh.season = :current_season
        LEFT JOIN Stats_Pitching sp ON b.player_id = sp.player_id AND sp.season = :current_season
        WHERE b.player_id = :pid AND r.season = :current_season
    """)
    
    row = db.session.execute(query, {'pid': player_id, 'current_season': current_season}).fetchone()
    
    if not row:
        abort(404)

    # 2. Convert row to a dictionary using your existing toolbox method
    player = parse_player_row(row)
    
    # Inject profile-specific attributes that parse_player_row doesn't handle natively
    player['age'] = row.age
    player['roster_status'] = row.league_level
    player['bats'] = 'R'   # Fallback until added to DB
    player['throws'] = 'R' # Fallback until added to DB
    
    # 3. Team Formatting (Handling the missing city column)
    if row.team_id == 'Alpha-0001':
        team_city = "Washington"
    elif not row.team_id:
        team_city = "Free Agent"
    else:
        team_city = "Unknown City" # Fallback for other teams

    team_name = row.team_name if row.team_name else ""
    team_full_name = f"{team_city} {team_name} - {player['roster_status']}".replace("  ", " ").strip()

    # 4. Pitcher Logic & Overall Calculation
    player['is_pitcher'] = player.get('role') == 'Pitcher' or row.position in ['SP', 'MR', 'LR', 'SU', 'CL', 'RP']
    
    if player['is_pitcher']:
        player['overall'] = int(round((player['vel'] + player['ctrl'] + player['mov']) / 3))
    else:
        player['overall'] = int(round((player['con'] + player['pow'] + player['spd'] + player['defense']) / 4))

    # ==========================================
    # 5. REAL DATA INJECTION: CONTRACTS & AWARDS
    # ==========================================
    
    # --- CONTRACT ---
    # Fix: Made the status check case-insensitive to avoid missed matches
    contract_query = text("""
        SELECT cost_per_season, year_end 
        FROM Contracts 
        WHERE player_id = :pid AND LOWER(status) = 'active'
        LIMIT 1
    """)
    contract_row = db.session.execute(contract_query, {'pid': player_id}).fetchone()
    
    contract_query = text("""
        SELECT cost_per_season, year_end 
        FROM Contracts 
        WHERE player_id = :pid AND year_end >= :current_season
        LIMIT 1
    """)
    # Pass both the specific player ID and the current season (1) into the query
    contract_row = db.session.execute(contract_query, {'pid': player_id, 'current_season': current_season}).fetchone()
    
    if contract_row:
        player['contract_amount'] = contract_row.cost_per_season
        # Math: If year_end is 4 and current_season is 1, they have 4 years remaining (Years 1, 2, 3, 4)
        player['contract_years'] = (contract_row.year_end - current_season) + 1
    else:
        player['contract_amount'] = 0
        player['contract_years'] = 0

    # --- AWARDS ---
    awards_query = text("SELECT season as year, competition, title FROM Awards WHERE player_id = :pid ORDER BY season DESC")
    player['awards'] = [dict(row._mapping) for row in db.session.execute(awards_query, {'pid': player_id}).fetchall()]

    # ==========================================
    # 6. REAL DATA INJECTION: HISTORICAL STATS
    # ==========================================

    # --- RATINGS HISTORY ---
    # Pulls their raw attributes for every season to show progression/decline
    ratings_query = text("""
        SELECT season, pit_velo, pit_ctrl, pit_mov, 
               con_timing, con_barrel, pow_str, pow_batspd, pow_elev, 
               spd_sprint, spd_inst, def_range, def_glove, def_react
        FROM Player_Ratings 
        WHERE player_id = :pid 
        ORDER BY season ASC
    """)
    ratings_rows = db.session.execute(ratings_query, {'pid': player_id}).fetchall()
    
    player['ratings_history'] = []
    for r in ratings_rows:
        hist = {"season": r.season}
        
        if player['is_pitcher']:
            hist['vel'] = r.pit_velo or 0
            hist['ctrl'] = r.pit_ctrl or 0
            hist['mov'] = r.pit_mov or 0
            hist['overall'] = int(round((hist['vel'] + hist['ctrl'] + hist['mov']) / 3))
        else:
            hist['con'] = int(((r.con_timing or 0) + (r.con_barrel or 0)) / 2)
            hist['pow'] = int(((r.pow_str or 0) + (r.pow_batspd or 0) + (r.pow_elev or 0)) / 3)
            hist['spd'] = int(((r.spd_sprint or 0) + (r.spd_inst or 0)) / 2)
            hist['defense'] = int(((r.def_range or 0) + (r.def_glove or 0) + (r.def_react or 0)) / 3)
            hist['overall'] = int(round((hist['con'] + hist['pow'] + hist['spd'] + hist['defense']) / 4))
            
        player['ratings_history'].append(hist)

    # --- CAREER STATS ---
    if player['is_pitcher']:
        stats_query = text("""
            SELECT season as year, competition, w, l, era, ip, k, bb, whip 
            FROM Stats_Pitching 
            WHERE player_id = :pid 
            ORDER BY season ASC
        """)
        totals_query = text("""
            SELECT competition, SUM(w) as w, SUM(l) as l, 
                   CAST(SUM(k) AS FLOAT)/MAX(SUM(ip), 1) * 9 as era,
                   SUM(ip) as ip, SUM(k) as k, SUM(bb) as bb 
            FROM Stats_Pitching 
            WHERE player_id = :pid 
            GROUP BY competition
        """)
    else:
        stats_query = text("""
            SELECT season as year, competition, g, ab, h, hr, rbi, avg, ops 
            FROM Stats_Hitting 
            WHERE player_id = :pid 
            ORDER BY season ASC
        """)
        totals_query = text("""
            SELECT competition, SUM(g) as g, SUM(ab) as ab, SUM(h) as h, 
                   SUM(hr) as hr, SUM(rbi) as rbi 
            FROM Stats_Hitting 
            WHERE player_id = :pid 
            GROUP BY competition
        """)
        
    player['stats_career'] = [dict(row._mapping) for row in db.session.execute(stats_query, {'pid': player_id}).fetchall()]
    
    player['career_totals_by_comp'] = [dict(row._mapping) for row in db.session.execute(totals_query, {'pid': player_id}).fetchall()]
    
    # ==========================================
    # Calculate 'career_grand_total' for Jinja
    # ==========================================
    grand_total = {}
    
    if player['is_pitcher']:
        grand_total = {'w': 0, 'l': 0, 'ip': 0, 'k': 0, 'bb': 0, 'era': '0.00', 'whip': '0.00'}
        for comp in player['career_totals_by_comp']:
            grand_total['w'] += (comp.get('w') or 0)
            grand_total['l'] += (comp.get('l') or 0)
            grand_total['ip'] += (comp.get('ip') or 0)
            grand_total['k'] += (comp.get('k') or 0)
            grand_total['bb'] += (comp.get('bb') or 0)
    else:
        grand_total = {'g': 0, 'ab': 0, 'h': 0, 'hr': 0, 'rbi': 0, 'avg': '.000', 'ops': '.000'}
        for comp in player['career_totals_by_comp']:
            grand_total['g'] += (comp.get('g') or 0)
            grand_total['ab'] += (comp.get('ab') or 0)
            grand_total['h'] += (comp.get('h') or 0)
            grand_total['hr'] += (comp.get('hr') or 0)
            grand_total['rbi'] += (comp.get('rbi') or 0)
            
        if grand_total['ab'] > 0:
            calc_avg = grand_total['h'] / grand_total['ab']
            grand_total['avg'] = f"{calc_avg:.3f}".lstrip('0') 
            
    player['career_grand_total'] = grand_total
    
    # Filter 'stats_career' to get just the current year's stats
    player['stats_current'] = [s for s in player['stats_career'] if s['year'] == current_season]

    return render_template(
        "player_profile.html",
        player=player,
        team_full_name=team_full_name
    )

@main_bp.route("/submit_offer/<string:player_id>", methods=["POST"])
def submit_offer(player_id):
    new_bid = Bid(
        team_id=request.form.get("team_id"),
        team_tier=int(request.form.get("team_tier", 1)),
        duration=int(request.form.get("years")),
        yearly_value=int(request.form.get("salary"))
    )
    
    # Get player_age from your database for this player
    player_age = get_player_age(player_id) # (Assuming you have a helper for this)

    # Validate the Bid!
    is_valid, message = validate_bid(new_bid, player_age)
    
    if not is_valid:
        flash(message, "error")
        return redirect(f"/free_agency/player/{player_id}")
        
    # If valid, save it to the DB...
    # save_bid_to_database(player_id, new_bid)
    
    flash("Contract offer submitted successfully!", "success")
    return redirect(f"/free_agency/player/{player_id}")

@main_bp.route('/front_office/<team_id>')
def front_office(team_id):
    # 1. Intercept phantom IDs to match your DB
    if team_id != 'Alpha-0001':
        team_id = 'Alpha-0001'
        
    current_season = 1 
    
    # 2. Fetch team details for base.html colors
    team_query = text("SELECT nickname, color_primary, color_secondary FROM Teams WHERE team_id = :tid")
    team = db.session.execute(team_query, {'tid': team_id}).fetchone()

    # 3. Dynamically calculate Player Payroll straight from the Contracts table
    payroll_query = text("""
        SELECT SUM(c.cost_per_season) 
        FROM Contracts c
        JOIN Player_Ratings r ON c.player_id = r.player_id
        WHERE r.team_id = :tid AND r.season = :season AND c.year_end >= :season
    """)
    calculated_payroll = db.session.execute(payroll_query, {'tid': team_id, 'season': current_season}).scalar() or 0

    # 4. Grab Starting Balance from Team_Financials (or default to 85M)
    finance_query = text("SELECT balance FROM Team_Financials WHERE team_id = :tid AND season = :season LIMIT 1")
    finances_row = db.session.execute(finance_query, {'tid': team_id, 'season': current_season}).fetchone()
    starting_balance = finances_row.balance if finances_row else 85000000

    finances = {
        'balance': starting_balance,
        'cost_players': calculated_payroll
    }
    
    available_budget = starting_balance - calculated_payroll

    # 5. Get the roster counts natively
    majors_query = text("SELECT COUNT(*) FROM Player_Ratings WHERE team_id = :tid AND league_level = 'MLB' AND season = :season")
    majors_count = db.session.execute(majors_query, {'tid': team_id, 'season': current_season}).scalar() or 0
    
    aaa_query = text("SELECT COUNT(*) FROM Player_Ratings WHERE team_id = :tid AND league_level = 'AAA' AND season = :season")
    aaa_count = db.session.execute(aaa_query, {'tid': team_id, 'season': current_season}).scalar() or 0

    # 6. Fetch the Roster natively for our upcoming charts
    roster_query = text("""
        SELECT b.first_name, b.last_name, b.player_id, r.age, r.position, r.assigned_role,
               c.cost_per_season, c.year_end,
               r.con_timing, r.con_barrel, r.pow_str, r.pow_batspd, r.pow_elev,
               r.spd_sprint, r.spd_inst, r.def_range, r.def_glove, r.def_react,
               r.pit_velo, r.pit_ctrl, r.pit_mov
        FROM Players_Base b
        JOIN Player_Ratings r ON b.player_id = r.player_id
        LEFT JOIN Contracts c ON b.player_id = c.player_id AND c.year_end >= :season
        WHERE r.team_id = :tid AND r.season = :season
    """)
    raw_roster = db.session.execute(roster_query, {'tid': team_id, 'season': current_season}).fetchall()
    
    roster = []
    for row in raw_roster:
        p = {
            'name': f"{row.first_name} {row.last_name}",
            'age': row.age,
            'position': row.position,
            'salary': row.cost_per_season or 0,
            'contract_end': row.year_end or 0
        }
        
        # Calculate OVR for the charts
        is_pitcher = row.position in ['SP', 'MR', 'LR', 'SU', 'CL', 'RP']
        if is_pitcher:
            p['ovr'] = int(round(((row.pit_velo or 0) + (row.pit_ctrl or 0) + (row.pit_mov or 0)) / 3))
        else:
            con = ((row.con_timing or 0) + (row.con_barrel or 0)) / 2
            pow = ((row.pow_str or 0) + (row.pow_batspd or 0) + (row.pow_elev or 0)) / 3
            spd = ((row.spd_sprint or 0) + (row.spd_inst or 0)) / 2
            dfn = ((row.def_range or 0) + (row.def_glove or 0) + (row.def_react or 0)) / 3
            p['ovr'] = int(round((con + pow + spd + dfn) / 4))
            
        roster.append(p)

    # ==========================================
    # 7. Historical Finances (Capital Over Time)
    # ==========================================
    history_query = text("SELECT season, balance FROM Team_Financials WHERE team_id = :tid ORDER BY season ASC")
    history_rows = db.session.execute(history_query, {'tid': team_id}).fetchall()
    
    finance_history = {'seasons': [], 'balances': []}
    if history_rows:
        for r in history_rows:
            finance_history['seasons'].append(f"Season {r.season}")
            finance_history['balances'].append(r.balance)
    else:
        # Fallback if no history exists yet
        finance_history['seasons'].append(f"Season {current_season}")
        finance_history['balances'].append(starting_balance)

    # ==========================================
    # 8. Expiring Contracts Calculation
    # ==========================================
    expiring_contracts = {}
    for p in roster:
        end_year = p['contract_end']
        if end_year and end_year >= current_season:
            # Swapped "Year" for "Season" so the labels match the game's timeline perfectly
            year_label = f"Season {end_year}"
            if year_label not in expiring_contracts:
                expiring_contracts[year_label] = 0
            expiring_contracts[year_label] += p['salary']
            
    # Sort the dictionary chronologically
    expiring_sorted = dict(sorted(expiring_contracts.items()))
    contract_labels = list(expiring_sorted.keys())
    contract_values = list(expiring_sorted.values())

    # ==========================================
    # 9. Team Composition (Middle Row)
    # ==========================================
    pos_counts = {'C': 0, '1B': 0, '2B': 0, '3B': 0, 'SS': 0, 'LF': 0, 'CF': 0, 'RF': 0, 'P': 0}
    spending_split = {'hitters': 0, 'pitchers': 0}

    for p in roster:
        # Standardize the text: force uppercase and remove extra spaces
        raw_pos = p['position']
        pos = str(raw_pos).strip().upper() if raw_pos else "UNKNOWN"
        salary = p['salary']
        
        # 1. Catch Pitchers
        if pos == 'P' or pos in ['SP', 'MR', 'LR', 'SU', 'CL', 'RP']:
            pos_counts['P'] += 1
            spending_split['pitchers'] += salary
            
        # 2. Catch Specific Hitters
        elif pos in pos_counts:
            pos_counts[pos] += 1
            spending_split['hitters'] += salary
            
        # 3. Debugging Catch-All (Check your terminal if numbers are missing!)
        else:
            print(f"DEBUG: Unrecognized position '{pos}' - skipping count.")

    # ==========================================
    # 10. Bottom Row Data (Age vs. Salary & Donut)
    # ==========================================
    scatter_data = []
    donut_data = {'Catchers': 0, 'Infielders': 0, 'Outfielders': 0, 'Pitchers': 0}

    for p in roster:
        # Securely fetch data with fallbacks
        age = p.get('age', 25) 
        salary = p.get('salary', 0)
        name = p.get('name', 'Unknown')
        
        # Build Scatter Plot Data (X: Age, Y: Salary)
        scatter_data.append({'x': age, 'y': salary, 'name': name})
        
        # Build Donut Chart Data (Grouped by Unit)
        raw_pos = p.get('position', '')
        pos = str(raw_pos).strip().upper() if raw_pos else "UNKNOWN"
        
        if pos == 'C':
            donut_data['Catchers'] += salary
        elif pos in ['1B', '2B', '3B', 'SS']:
            donut_data['Infielders'] += salary
        elif pos in ['LF', 'CF', 'RF']:
            donut_data['Outfielders'] += salary
        elif pos == 'P' or pos in ['SP', 'MR', 'LR', 'SU', 'CL', 'RP']:
            donut_data['Pitchers'] += salary

    return render_template('front_office.html',
                           team_id=team_id,
                           team_nickname=f"Washington {team.nickname} Front Office" if team else "Front Office",
                           team_color_1=team.color_primary if team else "#000000",
                           team_color_2=team.color_secondary if team else "#FFFFFF",
                           get_main_bg=get_main_bg,
                           get_main_text=get_main_text,
                           finances=finances,
                           available_budget=available_budget,
                           majors_count=majors_count,
                           aaa_count=aaa_count,
                           roster=roster,
                           finance_history=finance_history,
                           contract_labels=contract_labels,
                           contract_values=contract_values,
                           pos_counts=pos_counts,
                           spending_split=spending_split,
                           scatter_data=scatter_data,
                           donut_data=donut_data
                        )