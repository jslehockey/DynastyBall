from flask import Blueprint, render_template, request, redirect, url_for, jsonify, abort, flash
from sqlalchemy import text
import sqlite3
from model_player import Player
from model_bid import Bid
import json
from model_bid import FABid, Bid
from finance_engine import validate_bid, get_available_fa_money
import random

# Import the db instance from your main app
from extensions import db 

# Import all your logic from the new toolbox
from app_methods import (
    get_db_connection, get_stamina_color, get_main_bg, 
    get_main_text, parse_player_row, check_roster_limits,
    get_latest_finances, get_full_roster_details, get_player_age,
    get_expiring_contract_totals, get_roster_count, process_expired_bids,
    get_current_offseason_day, get_current_season
)
from game_math import OOP_MATRIX

# Initialize the Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    team_id = 1
    current_season = get_current_season()
    
    # 1. Fetch team details for styling
    team_query = text("SELECT location, nickname, color_primary, color_secondary FROM teams WHERE team_id = :tid")
    team = db.session.execute(team_query, {'tid': team_id}).fetchone()
    
    # 2. Roster Limits & Counts
    limits = check_roster_limits(team_id, current_season)
    
    # 3. Calculate separate MLB and AAA payrolls
    pay_query = text("""
        SELECT 
            SUM(CASE WHEN r.league_level = 'MLB' THEN c.cost_per_season ELSE 0 END) as mlb_payroll,
            SUM(CASE WHEN r.league_level IN ('AAA', 'MiLB') THEN c.cost_per_season ELSE 0 END) as aaa_payroll
        FROM contracts c
        JOIN player_ratings r ON c.player_id = r.player_id AND c.team_id = r.team_id AND r.season = :season
        WHERE c.year_end >= :season AND c.status = 'Active' AND c.team_id = :tid
    """)
    pay_row = db.session.execute(pay_query, {'season': current_season, 'tid': team_id}).fetchone()
    
    dashboard_stats = {
        'mlb_payroll': pay_row.mlb_payroll or 0,
        'aaa_payroll': pay_row.aaa_payroll or 0,
        'record': '0-0', # Placeholder until the game simulation engine is built
        'standing': 'Pre-Season' # Placeholder
    }
    
    # 4. Fetch Recent Moves (Currently utilizing Pending FA Bids)
    bids_query = text("""
        SELECT pb.first_name, pb.last_name, b.salary, b.years
        FROM fa_bids b
        JOIN players_base pb ON b.player_id = pb.player_id
        WHERE b.team_id = :tid AND b.status = 'Pending'
        ORDER BY b.salary DESC LIMIT 5
    """)
    recent_bids = db.session.execute(bids_query, {'tid': team_id}).fetchall()

    return render_template('index.html', 
                           team=team,
                           team_nickname=f"{team.location} {team.nickname}" if team else "Master Dashboard",
                           team_color_1=team.color_primary if team else "#000000",
                           team_color_2=team.color_secondary if team else "#FFFFFF",
                           limits=limits,
                           dashboard_stats=dashboard_stats,
                           recent_bids=recent_bids)

@main_bp.route("/major-league")
def major_league():
    # 1. Look for Team 1 (Integer)
    team_query = text("SELECT location, nickname, color_primary, color_secondary FROM teams WHERE team_id = 1")
    team = db.session.execute(team_query).fetchone()

    # Safety net
    if not team:
        return "Error: Team 1 not found in the database. Did the seed script run successfully?", 404

    # 2. Update roster query to use team_id = 1
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
               
        FROM players_base b
        JOIN player_ratings r ON b.player_id = r.player_id
        LEFT JOIN stats_hitting sh ON b.player_id = sh.player_id AND sh.season = 1
        LEFT JOIN stats_pitching sp ON b.player_id = sp.player_id AND sp.season = 1
        WHERE r.team_id = 1 AND r.season = 1 AND r.league_level = 'MLB'
    """)
    
    raw_roster = db.session.execute(roster_query).fetchall()

    # (Keep your existing processing logic here)
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

    limits = check_roster_limits(1, 1) # Note: Make sure check_roster_limits uses integer 1 now!

    return render_template(
        "major_league.html",
        team_nickname=f"{team.location} {team.nickname}",
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
    current_season = get_current_season()
    
    # 1. Look for Team 1
    team_query = text("SELECT location, nickname, color_primary, color_secondary FROM teams WHERE team_id = 1")
    team = db.session.execute(team_query).fetchone()

    if not team:
        return "Error: Team 1 not found in the database.", 404

    # 2. Grab the Minors roster (checking for BOTH 'AAA' and 'MiLB')
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
        FROM players_base b
        JOIN player_ratings r ON b.player_id = r.player_id
        LEFT JOIN stats_hitting sh ON b.player_id = sh.player_id AND sh.season = :season
        LEFT JOIN stats_pitching sp ON b.player_id = sp.player_id AND sp.season = :season
        WHERE r.team_id = 1 AND r.season = :season AND r.league_level IN ('AAA', 'MiLB')
    """)
    
    raw_roster = db.session.execute(roster_query, {'season': current_season}).fetchall()
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
    limits = check_roster_limits(1, current_season) 

    return render_template(
        "minor_league.html", 
        team_nickname=f"{team.location} {team.nickname} (Minor League)",
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
    current_season = get_current_season()
    data = request.json
    
    # Safely get team_id from the frontend payload, default to 1 if missing
    team_id = data.get('team_id', 1) 
    
    hitters = data.get('hitters', [])
    pitchers = data.get('pitchers', [])

    try:
        for h in hitters:
            # Skip empty slots so they don't crash the database lookup
            if 'EMPTY' in h['name']:
                continue
                
            player_query = text("SELECT player_id FROM Players_Base WHERE TRIM(first_name || ' ' || COALESCE(last_name, '')) = :fullname")
            pid_result = db.session.execute(player_query, {'fullname': h['name']}).scalar()
            
            if pid_result:
                update_query = text("""
                    UPDATE Player_Ratings 
                    SET assigned_pos = :pos, batting_order = :order 
                    WHERE player_id = :pid AND season = :season AND team_id = :tid
                """)
                db.session.execute(update_query, {
                    'pos': h['assigned_pos'], 
                    'order': h['batting_order'], 
                    'pid': pid_result,
                    'season': current_season,
                    'tid': team_id
                })

        for p in pitchers:
            # Skip empty slots
            if 'EMPTY' in p['name']:
                continue
                
            player_query = text("SELECT player_id FROM Players_Base WHERE TRIM(first_name || ' ' || COALESCE(last_name, '')) = :fullname")
            pid_result = db.session.execute(player_query, {'fullname': p['name']}).scalar()
            
            if pid_result:
                update_query = text("""
                    UPDATE Player_Ratings 
                    SET assigned_role = :role 
                    WHERE player_id = :pid AND season = :season AND team_id = :tid
                """)
                db.session.execute(update_query, {
                    'role': p['role'], 
                    'pid': pid_result,
                    'season': current_season,
                    'tid': team_id
                })

        db.session.commit()
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"CRITICAL: Error saving roster: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    
@main_bp.route("/call_ups")
def call_ups():
    # 1. Update query to use integer 1 and grab 'location'
    team_query = text("SELECT location, nickname, color_primary, color_secondary FROM teams WHERE team_id = 1")
    team = db.session.execute(team_query).fetchone()

    if not team:
        return "Error: Team 1 not found in the database.", 404

    # 2. Add hit_g and pit_g to the query to track games played
    roster_query = text("""
        SELECT b.first_name, b.last_name, b.player_id, r.age, r.league_level, r.position, r.recent_form, r.psyche_mod,
               r.stam_max, r.stam_cur, r.assigned_pos, r.batting_order, r.assigned_role,
               r.con_timing, r.con_barrel, r.pow_str, r.pow_batspd, r.pow_elev,
               r.spd_sprint, r.spd_inst, r.def_range, r.def_glove, r.def_react, r.def_armstr, r.def_armacc,
               r.pit_velo, r.pit_vel_armspd, r.pit_vel_decept, r.pit_ctrl, r.pit_ctrl_acc, 
               r.pit_ctrl_cmd, r.pit_mov, r.pit_mov_spin, r.pit_mov_bite,
               COALESCE(sh.g, 0) as hit_g, COALESCE(sh.h, 0) as hits, COALESCE(sh.ab, 0) as at_bats,
               COALESCE(sh.avg, '.000') as batting_avg, COALESCE(sh.hr, 0) as home_runs,
               COALESCE(sh.rbi, 0) as rbis, COALESCE(sh.ops, '.000') as ops,
               COALESCE(sp.g, 0) as pit_g, COALESCE(sp.ip, '0.0') as stat_ip, COALESCE(sp.era, '0.00') as stat_era,
               COALESCE(sp.k, 0) as stat_k, COALESCE(sp.bb, 0) as stat_bb,
               COALESCE(sp.whip, '0.00') as stat_whip
        FROM players_base b
        JOIN player_ratings r ON b.player_id = r.player_id
        LEFT JOIN stats_hitting sh ON b.player_id = sh.player_id AND sh.season = 1
        LEFT JOIN stats_pitching sp ON b.player_id = sp.player_id AND sp.season = 1
        WHERE r.team_id = 1 AND r.season = 1
        ORDER BY r.position ASC, b.last_name ASC
    """)
    raw_roster = db.session.execute(roster_query).fetchall()

    mlb_roster = []
    aaa_roster = []

    for row in raw_roster:
        p = parse_player_row(row)
        p['id'] = row.player_id
        
        is_pitcher = p['role'] == 'Pitcher'
        
        # 1. Calculate OVR
        if is_pitcher:
            p['ovr'] = int((p['vel'] + p['ctrl'] + p['mov']) / 3)
        else:
            p['ovr'] = int((p['con'] + p['pow'] + p['spd'] + p['defense']) / 4)

        # 2. Check where the player currently plays
        is_mlb = (row.league_level == 'MLB')

        # 3. Route the stats to the correct league bucket
        if is_pitcher:
            if is_mlb:
                p['mlb_g'] = row.pit_g
                p['mlb_ip'] = row.stat_ip
                p['mlb_era'] = row.stat_era
                p['mlb_k'] = row.stat_k
                p['mlb_whip'] = row.stat_whip
            else:
                p['aaa_g'] = row.pit_g
                p['aaa_ip'] = row.stat_ip
                p['aaa_era'] = row.stat_era
                p['aaa_k'] = row.stat_k
                p['aaa_whip'] = row.stat_whip
        else:
            if is_mlb:
                p['mlb_g'] = row.hit_g
                p['mlb_avg'] = row.batting_avg
                p['mlb_hr'] = row.home_runs
                p['mlb_rbi'] = row.rbis
                p['mlb_ops'] = row.ops
            else:
                p['aaa_g'] = row.hit_g
                p['aaa_avg'] = row.batting_avg
                p['aaa_hr'] = row.home_runs
                p['aaa_rbi'] = row.rbis
                p['aaa_ops'] = row.ops

        # 4. Sort by League Level for the tables
        if is_mlb:
            mlb_roster.append(p)
        else:
            aaa_roster.append(p)

    # Empty Slot Logic for MLB Roster
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
            
    # --- NEW: Empty Slot Logic for Minors (AAA) Roster ---
    aaa_max = 30
    aaa_slots_open = aaa_max - len(aaa_roster)
    
    if aaa_slots_open > 0:
        for _ in range(aaa_slots_open):
            aaa_roster.append({
                'id': 'EMPTY',
                'name': '[ EMPTY MINORS SLOT ]',
                'pos': '--',
                'age': '--',
                'ovr': 0,
                'stam_cur': 0,
                'stam_tot': 0,
                'role': 'Empty'
            })
    
    # 3. Update limit check to use integer 1
    limits = check_roster_limits(1, 1)
    
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

@main_bp.route('/front_office/<team_id>')
def front_office(team_id):
    # 1. Intercept phantom IDs to match your DB (Convert to Integer 1)
    try:
        team_id = int(team_id)
    except ValueError:
        team_id = 1
        
    if team_id != 1:
        team_id = 1
        
    current_season = get_current_season() 
    
    # 2. Fetch team details for base.html colors AND grab location
    team_query = text("SELECT location, nickname, color_primary, color_secondary FROM teams WHERE team_id = :tid")
    team = db.session.execute(team_query, {'tid': team_id}).fetchone()

    # 3. Dynamically calculate Player Payroll (Now grouped by Status!)
    payroll_query = text("""
        SELECT status, SUM(cost_per_season) as total_cost
        FROM contracts 
        WHERE team_id = :tid 
          AND year_end >= :season 
          AND status IN ('Active', 'Buyout', 'Dead Money')
        GROUP BY status
    """)
    payroll_rows = db.session.execute(payroll_query, {'tid': team_id, 'season': current_season}).fetchall()

    payroll_breakdown = {'Active': 0, 'Buyout': 0, 'Dead Money': 0}
    calculated_payroll = 0
    
    for row in payroll_rows:
        status_key = row.status
        cost = row.total_cost or 0
        if status_key in payroll_breakdown:
            payroll_breakdown[status_key] = cost
        calculated_payroll += cost

    # 4. Grab Starting Balance from Team_Financials (or default)
    finance_query = text("SELECT balance FROM team_financials WHERE team_id = :tid AND season = :season LIMIT 1")
    finances_row = db.session.execute(finance_query, {'tid': team_id, 'season': current_season}).fetchone()
    starting_balance = finances_row.balance if finances_row else 150000000

    finances = {
        'balance': starting_balance,
        'cost_players': calculated_payroll
    }
    
    available_budget = starting_balance - calculated_payroll

    # 5. Get the roster counts natively
    majors_query = text("SELECT COUNT(*) FROM player_ratings WHERE team_id = :tid AND league_level = 'MLB' AND season = :season")
    majors_count = db.session.execute(majors_query, {'tid': team_id, 'season': current_season}).scalar() or 0
    
    aaa_query = text("SELECT COUNT(*) FROM player_ratings WHERE team_id = :tid AND league_level IN ('AAA', 'MiLB') AND season = :season")
    aaa_count = db.session.execute(aaa_query, {'tid': team_id, 'season': current_season}).scalar() or 0

    # ==========================================
    # 5.5 League-Wide Roster Spending & Rankings
    # ==========================================
    rank_query = text("""
        SELECT 
            c.team_id,
            SUM(CASE WHEN r.league_level = 'MLB' THEN c.cost_per_season ELSE 0 END) as mlb_payroll,
            SUM(CASE WHEN r.league_level IN ('AAA', 'MiLB') THEN c.cost_per_season ELSE 0 END) as aaa_payroll
        FROM contracts c
        JOIN player_ratings r ON c.player_id = r.player_id AND c.team_id = r.team_id AND r.season = :season
        WHERE c.year_end >= :season AND c.status = 'Active'
        GROUP BY c.team_id
    """)
    team_payrolls = db.session.execute(rank_query, {'season': current_season}).fetchall()

    # Sort all teams from highest spending to lowest
    mlb_payrolls = sorted([row.mlb_payroll or 0 for row in team_payrolls], reverse=True)
    aaa_payrolls = sorted([row.aaa_payroll or 0 for row in team_payrolls], reverse=True)

    our_mlb_payroll = 0
    our_aaa_payroll = 0
    
    # Grab our specific payrolls
    for row in team_payrolls:
        if row.team_id == team_id:
            our_mlb_payroll = row.mlb_payroll or 0
            our_aaa_payroll = row.aaa_payroll or 0
            break

    # Calculate rank (1 is highest spender)
    our_mlb_rank = mlb_payrolls.index(our_mlb_payroll) + 1 if our_mlb_payroll in mlb_payrolls else len(mlb_payrolls) + 1
    our_aaa_rank = aaa_payrolls.index(our_aaa_payroll) + 1 if our_aaa_payroll in aaa_payrolls else len(aaa_payrolls) + 1
    
    team_ranks = {
        'mlb_payroll': our_mlb_payroll,
        'mlb_rank': our_mlb_rank,
        'aaa_payroll': our_aaa_payroll,
        'aaa_rank': our_aaa_rank
    }

    # ==========================================
    # 6. Fetch the Roster natively for our upcoming charts
    # ==========================================
    roster_query = text("""
        SELECT b.first_name, b.last_name, b.player_id, r.age, r.position, r.assigned_role, r.league_level,
               MAX(c.cost_per_season) as cost_per_season, MAX(c.year_end) as year_end,
               r.con_timing, r.con_barrel, r.pow_str, r.pow_batspd, r.pow_elev,
               r.spd_sprint, r.spd_inst, r.def_range, r.def_glove, r.def_react,
               r.pit_velo, r.pit_ctrl, r.pit_mov
        FROM players_base b
        JOIN player_ratings r ON b.player_id = r.player_id
        LEFT JOIN contracts c ON b.player_id = c.player_id AND c.status = 'Active' AND c.year_end >= :season
        WHERE r.team_id = :tid AND r.season = :season
        GROUP BY b.player_id
    """)
    raw_roster = db.session.execute(roster_query, {'tid': team_id, 'season': current_season}).fetchall()
    
    roster = []
    for row in raw_roster:
        years_left = (row.year_end - current_season) + 1 if row.year_end else 0
        p = {
            'id': row.player_id,
            'name': f"{row.first_name} {row.last_name}",
            'age': row.age,
            'position': row.position,
            'league': 'Majors' if row.league_level == 'MLB' else 'Minors', 
            'salary': row.cost_per_season or 0,
            'contract_end': row.year_end or 0,
            'years_left': years_left
        }
        
        is_pitcher = row.position in ['SP', 'MR', 'LR', 'SU', 'CL', 'RP', 'P']
        if is_pitcher:
            p['ovr'] = int(round(((row.pit_velo or 0) + (row.pit_ctrl or 0) + (row.pit_mov or 0)) / 3))
        else:
            con = ((row.con_timing or 0) + (row.con_barrel or 0)) / 2
            pow = ((row.pow_str or 0) + (row.pow_batspd or 0) + (row.pow_elev or 0)) / 3
            spd = ((row.spd_sprint or 0) + (row.spd_inst or 0)) / 2
            dfn = ((row.def_range or 0) + (row.def_glove or 0) + (row.def_react or 0)) / 3
            p['ovr'] = int(round((con + pow + spd + dfn) / 4))
            
        roster.append(p)

    # Sorts Majors before Minors, then sorts by highest salary
    roster.sort(key=lambda x: (0 if x['league'] == 'Majors' else 1, -x['salary']))

    # ==========================================
    # 7. Historical Finances (Capital Over Time)
    # ==========================================
    history_query = text("SELECT season, balance FROM team_financials WHERE team_id = :tid ORDER BY season ASC")
    history_rows = db.session.execute(history_query, {'tid': team_id}).fetchall()
    
    finance_history = {'seasons': [], 'balances': []}
    if history_rows:
        for r in history_rows:
            finance_history['seasons'].append(f"Season {r.season}")
            finance_history['balances'].append(r.balance)
    else:
        finance_history['seasons'].append(f"Season {current_season}")
        finance_history['balances'].append(starting_balance)

    # ==========================================
    # 8. Expiring Contracts Calculation
    # ==========================================
    expiring_query = text("""
        SELECT year_end, status, SUM(cost_per_season) as total
        FROM contracts
        WHERE team_id = :tid AND year_end >= :season AND status IN ('Active', 'Buyout', 'Dead Money')
        GROUP BY year_end, status
    """)
    expiring_rows = db.session.execute(expiring_query, {'tid': team_id, 'season': current_season}).fetchall()

    expiring_dict = {}
    for r in expiring_rows:
        year_label = f"Season {r.year_end}"
        if year_label not in expiring_dict:
            expiring_dict[year_label] = {'Active': 0, 'Dead': 0}
        
        if r.status == 'Active':
            expiring_dict[year_label]['Active'] += r.total
        else:
            expiring_dict[year_label]['Dead'] += r.total

    sorted_years = sorted(expiring_dict.keys(), key=lambda x: int(x.split(' ')[1]))

    contract_labels = []
    contract_active_values = []
    contract_dead_values = []

    for y in sorted_years:
        contract_labels.append(y)
        contract_active_values.append(expiring_dict[y]['Active'])
        contract_dead_values.append(expiring_dict[y]['Dead'])

    # ==========================================
    # 9. Team Composition (Middle Row)
    # ==========================================
    pos_counts = {'C': 0, '1B': 0, '2B': 0, '3B': 0, 'SS': 0, 'LF': 0, 'CF': 0, 'RF': 0, 'P': 0}
    spending_split = {'hitters': 0, 'pitchers': 0}

    for p in roster:
        raw_pos = p['position']
        pos = str(raw_pos).strip().upper() if raw_pos else "UNKNOWN"
        salary = p['salary']
        
        if pos == 'P' or pos in ['SP', 'MR', 'LR', 'SU', 'CL', 'RP']:
            pos_counts['P'] += 1
            spending_split['pitchers'] += salary
        elif pos in pos_counts:
            pos_counts[pos] += 1
            spending_split['hitters'] += salary

    # ==========================================
    # 10. Bottom Row Data (Age vs. Salary & Donut)
    # ==========================================
    scatter_data = []
    donut_data = {'Catchers': 0, 'Infielders': 0, 'Outfielders': 0, 'Pitchers': 0, 'Dead Cap': 0}

    for p in roster:
        age = p.get('age', 25) 
        salary = p.get('salary', 0)
        name = p.get('name', 'Unknown')
        
        scatter_data.append({'x': age, 'y': salary, 'name': name})
        
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

    # INJECT DEAD MONEY INTO THE DONUT CHART
    donut_data['Dead Cap'] = payroll_breakdown.get('Buyout', 0) + payroll_breakdown.get('Dead Money', 0)

    # ==========================================
    # 11. Fetch Active Free Agency Bids
    # ==========================================
    pending_bids_query = text("""
        SELECT b.bid_id, b.years, b.salary, b.decision_day,
               pb.player_id, pb.first_name, pb.last_name, 
               pr.position
        FROM fa_bids b
        JOIN players_base pb ON b.player_id = pb.player_id
        JOIN player_ratings pr ON pb.player_id = pr.player_id
        WHERE b.team_id = :tid 
          AND b.status = 'Pending' 
          AND pr.season = :season
        ORDER BY b.salary DESC
    """)
    raw_pending_bids = db.session.execute(pending_bids_query, {'tid': team_id, 'season': current_season}).fetchall()
    
    pending_bids = []
    pending_bids_total = 0
    
    for row in raw_pending_bids:
        pending_bids.append({
            'bid_id': row.bid_id, 
            'id': row.player_id,
            'name': f"{row.first_name} {row.last_name}",
            'position': row.position,
            'years': row.years,
            'salary': row.salary,
            'decision_day': row.decision_day
        })
        pending_bids_total += row.salary

    effective_budget = available_budget - pending_bids_total
    limits = check_roster_limits(team_id, current_season)

    return render_template('front_office.html',
                           team_id=team_id,
                           team_nickname=f"{team.location} {team.nickname} Front Office" if team else "Front Office",
                           team_color_1=team.color_primary if team else "#000000",
                           team_color_2=team.color_secondary if team else "#FFFFFF",
                           get_main_bg=get_main_bg,
                           get_main_text=get_main_text,
                           finances=finances,
                           available_budget=available_budget,
                           effective_budget=effective_budget,
                           pending_bids=pending_bids,
                           pending_bids_total=pending_bids_total,
                           payroll_breakdown=payroll_breakdown,
                           majors_count=majors_count,
                           aaa_count=aaa_count,
                           team_ranks=team_ranks, # <--- NEW: Feeds the UI badges!
                           roster=roster,
                           finance_history=finance_history,
                           contract_labels=contract_labels,
                           contract_active_values=contract_active_values,
                           contract_dead_values=contract_dead_values,
                           pos_counts=pos_counts,
                           spending_split=spending_split,
                           scatter_data=scatter_data,
                           donut_data=donut_data,
                           limits=limits
                        )

@main_bp.route("/submit_offer/<string:player_id>", methods=["POST"])
def submit_offer(player_id):
    team_id = int(request.form.get("team_id", 1))
    years = int(request.form.get("years"))
    salary = int(request.form.get("salary"))
    current_season = get_current_season() 
    current_offseason_day = get_current_offseason_day() 
    
    print(f"\n--- NEGOTIATION LOG: Team {team_id} -> Player {player_id} ---")
    
    # --- NEW: Organization Capacity Check ---
    limits = check_roster_limits(team_id, current_season)
    if limits['org_total'] >= 56:
        print("BLOCKED: Organization roster is completely full (56/56).")
        # Optional: Add a flash message here if you re-enable them for errors
        return redirect(url_for('main.free_agency', team_id=team_id))
    # ----------------------------------------
    
    # 1. Financial Validation
    try:
        available_money = get_available_fa_money(team_id)
        player_age = get_player_age(player_id) or 25
        
        temp_bid = Bid(team_id=team_id, team_tier=1, duration=years, yearly_value=salary)
        is_valid, message = validate_bid(temp_bid, available_money, player_age)
        
        if not is_valid:
            print(f"BLOCKED: {message}")
            return redirect(url_for('main.free_agency', team_id=team_id))
            
    except Exception as e:
        print(f"ERROR: Validation failed: {e}")
        return redirect(url_for('main.free_agency', team_id=team_id))

    # 2. Database Save (Upsert)
    try:
        existing_bid = FABid.query.filter_by(player_id=player_id, team_id=team_id, status='Pending').first()
        
        if existing_bid:
            existing_bid.years = years
            existing_bid.salary = salary
            db.session.commit()
            print(f"SUCCESS: Bid updated to {years} yrs / ${salary:,.0f}")
        else:
            decision_day = current_offseason_day + random.randint(1, 4)
            new_fa_bid = FABid(
                player_id=player_id,
                team_id=team_id,
                season=current_season,
                years=years,
                salary=salary,
                status='Pending',
                decision_day=decision_day
            )
            db.session.add(new_fa_bid)
            db.session.commit()
            print(f"SUCCESS: New bid logged. Player decides on Day {decision_day}")
            
    except Exception as e:
        print(f"CRITICAL: Database write failed: {e}")
        db.session.rollback()

    return redirect(url_for('main.free_agency', team_id=team_id))

@main_bp.route("/cancel_offer/<int:bid_id>", methods=["POST"])
def cancel_offer(bid_id):
    team_id = request.form.get("team_id", 1)
    
    try:
        # Find the bid by its unique ID
        bid_to_cancel = FABid.query.get(bid_id)
        if bid_to_cancel:
            db.session.delete(bid_to_cancel)
            db.session.commit()
            print(f"--- LOG: Canceled bid {bid_id} ---")
    except Exception as e:
        db.session.rollback()
        print(f"CRITICAL: Failed to cancel bid: {e}")

    return redirect(url_for('main.front_office', team_id=team_id))

@main_bp.route('/free_agency/<team_id>')
def free_agency(team_id):
    try:
        team_id = int(team_id)
    except ValueError:
        team_id = 1
        
    if team_id != 1:
        team_id = 1
        
    current_season = get_current_season()
    
    # --- AUTO-PROCESS TIME ENGINE ---
    # This quietly checks real-world time and signs players in the background!
    process_expired_bids()
    current_day = get_current_offseason_day()
    
    # 1. Fetch team details for colors
    team_query = text("SELECT location, nickname, color_primary, color_secondary FROM teams WHERE team_id = :tid")
    team = db.session.execute(team_query, {'tid': team_id}).fetchone()

    # 2. Get YOUR TEAM's roster counts for the Whiteboard
    wb_query = text("""
        SELECT position, role 
        FROM player_ratings 
        WHERE team_id = :tid AND season = :season
    """)
    team_roster = db.session.execute(wb_query, {'tid': team_id, 'season': current_season}).fetchall()
    
    pos_counts = {'C': 0, '1B': 0, '2B': 0, '3B': 0, 'SS': 0, 'LF': 0, 'CF': 0, 'RF': 0, 'P': 0}
    for r in team_roster:
        pos = str(r.position).strip().upper() if r.position else "UNKNOWN"
        if pos == 'P' or pos in ['SP', 'MR', 'LR', 'SU', 'CL', 'RP']:
            pos_counts['P'] += 1
        elif pos in pos_counts:
            pos_counts[pos] += 1

    # 3. Fetch all FREE AGENTS
    fa_query = text("""
        SELECT b.first_name, b.last_name, b.player_id, r.age, r.position, r.role,
               r.con_timing, r.con_barrel, r.pow_str, r.pow_batspd, r.pow_elev,
               r.spd_sprint, r.spd_inst, r.def_range, r.def_glove, r.def_react,
               r.pit_velo, r.pit_ctrl, r.pit_mov, r.stam_cur, r.stam_max
        FROM players_base b
        JOIN player_ratings r ON b.player_id = r.player_id
        WHERE r.team_id IS NULL AND r.league_level = 'FA' AND r.season = :season
        ORDER BY r.position ASC, b.last_name ASC
    """)
    raw_fas = db.session.execute(fa_query, {'season': current_season}).fetchall()
    
    fa_hitters = []
    fa_pitchers = []
    
    for row in raw_fas:
        p = {
            'id': row.player_id,
            'name': f"{row.first_name} {row.last_name}",
            'age': row.age,
            'pos': row.position,
            'stam_cur': row.stam_cur or 0,
            'stam_tot': row.stam_max or 0
        }
        
        is_pitcher = row.role == 'Pitcher' or row.position in ['SP', 'MR', 'LR', 'SU', 'CL', 'RP', 'P']
        
        if is_pitcher:
            p['vel'] = row.pit_velo or 0
            p['ctrl'] = row.pit_ctrl or 0
            p['mov'] = row.pit_mov or 0
            p['ovr'] = int(round((p['vel'] + p['ctrl'] + p['mov']) / 3))
            fa_pitchers.append(p)
        else:
            p['con'] = int(round(((row.con_timing or 0) + (row.con_barrel or 0)) / 2))
            p['pow'] = int(round(((row.pow_str or 0) + (row.pow_batspd or 0) + (row.pow_elev or 0)) / 3))
            p['spd'] = int(round(((row.spd_sprint or 0) + (row.spd_inst or 0)) / 2))
            p['def'] = int(round(((row.def_range or 0) + (row.def_glove or 0) + (row.def_react or 0)) / 3))
            p['ovr'] = int(round((p['con'] + p['pow'] + p['spd'] + p['def']) / 4))
            fa_hitters.append(p)

    # 4. Fetch ALL pending bids to get counts, and YOUR pending bids to pre-fill the modal
    all_bids_query = text("""
        SELECT player_id, COUNT(bid_id) as total_offers 
        FROM fa_bids 
        WHERE status = 'Pending' 
        GROUP BY player_id
    """)
    all_bids_raw = db.session.execute(all_bids_query).fetchall()
    offer_counts = {str(row.player_id): row.total_offers for row in all_bids_raw}

    my_bids_query = text("""
        SELECT player_id, years, salary 
        FROM fa_bids 
        WHERE team_id = :tid AND status = 'Pending'
    """)
    my_bids_raw = db.session.execute(my_bids_query, {'tid': team_id}).fetchall()
    my_pending_offers = {str(row.player_id): {'years': row.years, 'salary': row.salary} for row in my_bids_raw}

    for player_list in [fa_hitters, fa_pitchers]:
        for p in player_list:
            p['total_offers'] = offer_counts.get(str(p['id']), 0)
            p['my_offer'] = my_pending_offers.get(str(p['id']), None)

    limits = check_roster_limits(team_id, current_season)

    return render_template('free_agency.html',
                           team_id=team_id,
                           team_nickname=f"{team.location} {team.nickname}" if team else "Free Agency",
                           team_color_1=team.color_primary if team else "#000000",
                           team_color_2=team.color_secondary if team else "#FFFFFF",
                           pos_counts=pos_counts,
                           fa_hitters=fa_hitters,
                           fa_pitchers=fa_pitchers,
                           get_main_bg=get_main_bg,
                           get_main_text=get_main_text,
                           get_stamina_color=get_stamina_color,
                           limits=limits,
                           current_day=current_day) # Passed to the UI clock!

@main_bp.route("/release_player/<string:player_id>", methods=["POST"])
def release_player(player_id):
    team_id = int(request.form.get("team_id", 1))
    current_season = get_current_season()

    # 1. Fetch their active contract
    contract_query = text("""
        SELECT cost_per_season, year_end 
        FROM contracts 
        WHERE player_id = :pid AND team_id = :tid AND status = 'Active'
    """)
    contract = db.session.execute(contract_query, {'pid': player_id, 'tid': team_id}).fetchone()

    if contract:
        years_left = (contract.year_end - current_season) + 1
        
        if years_left == 1:
            # 1 Year Left = Full Penalty (Dead Money)
            update_contract = text("UPDATE contracts SET status = 'Dead Money' WHERE player_id = :pid AND team_id = :tid AND status = 'Active'")
            db.session.execute(update_contract, {'pid': player_id, 'tid': team_id})
            print(f"RELEASED: {player_id}. 1 year left. Full dead money applied.")
            
        elif years_left >= 2:
            # 2+ Years Left = 50% Penalty (Buyout)
            new_cost = int(contract.cost_per_season / 2)
            update_contract = text("UPDATE contracts SET status = 'Buyout', cost_per_season = :new_cost WHERE player_id = :pid AND team_id = :tid AND status = 'Active'")
            db.session.execute(update_contract, {'pid': player_id, 'tid': team_id, 'new_cost': new_cost})
            print(f"RELEASED: {player_id}. 2+ years left. Buyout applied at 50% (${new_cost:,.0f}/yr).")

    # 2. Strip them from the Roster and send them to Free Agency
    release_query = text("""
        UPDATE player_ratings 
        SET team_id = NULL, league_level = 'FA', assigned_pos = NULL, assigned_role = NULL, batting_order = 99
        WHERE player_id = :pid AND season = :season
    """)
    db.session.execute(release_query, {'pid': player_id, 'season': current_season})

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"CRITICAL: Failed to release player: {e}")

    return redirect(url_for('main.front_office', team_id=team_id))

@main_bp.route('/game/<int:game_id>')
def watch_game(game_id):
    """Loads the TV Screen for a specific game."""
    game_query = text("""
        SELECT g.game_id, g.home_score, g.away_score, 
               h.location as home_loc, h.nickname as home_name, h.color_primary as home_color,
               a.location as away_loc, a.nickname as away_name, a.color_primary as away_color
        FROM games g
        JOIN teams h ON g.home_team_id = h.team_id
        JOIN teams a ON g.away_team_id = a.team_id
        WHERE g.game_id = :gid
    """)
    game_data = db.session.execute(game_query, {'gid': game_id}).fetchone()
    
    if not game_data:
        return "Game not found in database. Did you run the engine?", 404
        
    return render_template('live_game.html', game=game_data)

@main_bp.route('/api/game/<int:game_id>/play/<int:event_index>')
def get_play(game_id, event_index):
    """The hidden API that feeds the JavaScript one play at a time."""
    # Added pitch_log to the end of the SELECT statement!
    event_query = text("""
        SELECT inning, half_inning, event_type, player_name, event_text, 
               outs_after, home_score_after, away_score_after, 
               runner_1b, runner_2b, runner_3b, pitch_log
        FROM game_events
        WHERE game_id = :gid AND event_index = :idx
    """)
    event = db.session.execute(event_query, {'gid': game_id, 'idx': event_index}).fetchone()
    
    if not event:
        return jsonify({"status": "end"}) # The game is over!
        
    return jsonify({
        "status": "ok",
        "inning": event.inning,
        "half": event.half_inning,
        "type": event.event_type,
        "player": event.player_name,
        "desc": event.event_text,
        "pitch_log": event.pitch_log, 
        "outs": event.outs_after,
        "away_score": event.away_score_after,
        "home_score": event.home_score_after,
        "r1": event.runner_1b,
        "r2": event.runner_2b,
        "r3": event.runner_3b
    })