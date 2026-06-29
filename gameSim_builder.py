# ==========================================
# gameSim_builder.py
# ==========================================
# Handles reading from Google Sheets and building 
# the game objects (Teams, Players, Stadiums).
# ==========================================
import sys
import gspread
from model_player import Player
from model_team import Team
from model_stadium import Stadium
from recordBook import RecordBook

def load_stadium_dimensions(engine, SHEET):
    print("  > Loading stadium dimensions, economy, and tier data from 'Parks' sheet...")
    try:
        park_records = SHEET.worksheet("Parks").get_all_records()
        
        dist_limits = {
            "Left Field Line": (300, 350), "Dead Left Field": (320, 375),
            "Left Center Gap": (340, 400), "Dead Center": (380, 425),
            "Right Center Gap": (340, 400), "Dead Right Field": (320, 375),
            "Right Field Line": (300, 350)
        }
        height_limits = (10, 50)
        
        def validate_val(value, min_val, max_val, default):
            try:
                val = float(value)
                if min_val <= val <= max_val: return val
                else: return default
            except (ValueError, TypeError):
                return default
                
        def get_key(row, partial_matches):
            for k in row.keys():
                for match in partial_matches:
                    if match.lower() in k.lower():
                        return row[k]
            return None

        for row in park_records:
            team_name = row.get("Team")
            if not team_name: continue

            dimensions = {
                "Left Field Line": int(validate_val(get_key(row, ["Lef Field Line", "Left Field Line"]), *dist_limits["Left Field Line"], 330)),
                "Dead Left Field": int(validate_val(get_key(row, ["Dead Left Field"]), *dist_limits["Dead Left Field"], 360)),
                "Left Center Gap": int(validate_val(get_key(row, ["Left Center Gap"]), *dist_limits["Left Center Gap"], 380)),
                "Dead Center": int(validate_val(get_key(row, ["Dead Center"]), *dist_limits["Dead Center"], 400)),
                "Right Center Gap": int(validate_val(get_key(row, ["Right Center Gap"]), *dist_limits["Right Center Gap"], 380)),
                "Dead Right Field": int(validate_val(get_key(row, ["Dead Right Field"]), *dist_limits["Dead Right Field"], 360)),
                "Right Field Line": int(validate_val(get_key(row, ["Right Field Line"]), *dist_limits["Right Field Line"], 330))
            }

            heights = {
                "Left Field Line": int(validate_val(get_key(row, ["Left Field Fence", "LF Fence"]), *height_limits, 12)),
                "Dead Left Field": int(validate_val(get_key(row, ["Dead Left Fence"]), *height_limits, 12)),
                "Left Center Gap": int(validate_val(get_key(row, ["Left Center Fence"]), *height_limits, 12)),
                "Dead Center": int(validate_val(get_key(row, ["Dead Center Fence"]), *height_limits, 12)),
                "Right Center Gap": int(validate_val(get_key(row, ["Right Center Fence"]), *height_limits, 12)),
                "Dead Right Field": int(validate_val(get_key(row, ["Dead Right Fence"]), *height_limits, 12)),
                "Right Field Line": int(validate_val(get_key(row, ["Right Field Line Fence", "RF Fence"]), *height_limits, 12))
            }
            
            capacity = int(validate_val(get_key(row, ["Capacity", "Seats"]), 1000, 100000, 30000))
            ticket_price = validate_val(get_key(row, ["Ticket", "Price"]), 1.0, 500.0, 30.00)
            prestige = int(validate_val(get_key(row, ["Prestige", "Pop"]), 1, 100, 50))
            tier = int(validate_val(get_key(row, ["Tier", "League"]), 1, 5, 1))

            engine.parks[team_name] = {
                "dimensions": dimensions, "heights": heights, 
                "capacity": capacity, "ticket_price": ticket_price, 
                "prestige": prestige, "tier": tier
            }
            
    except Exception as e:
        print(f"  > [WARNING] Could not load 'Parks' tab. Defaulting all stadiums to standard. Error: {e}")

def load_state(engine, SHEET):
    print("Loading current game state from Sheets...")
    
    try:
        registry_records = SHEET.worksheet("TeamRegistry").get_all_records()
    except gspread.exceptions.WorksheetNotFound:
        print("  [FATAL ERROR] 'TeamRegistry' tab not found! Cannot proceed.")
        sys.exit()

    all_worksheets = SHEET.worksheets()
    sheet_titles = [ws.title for ws in all_worksheets]

    engine.teams = []
    for row in registry_records:
        if str(row.get("Status", "")).strip().lower() == "active":
            nickname = str(row.get("Nickname", "")).strip()
            team_id = str(row.get("Team ID", "")).strip()
            
            if nickname not in sheet_titles:
                print(f"\n [FATAL ERROR] Team Name Mismatch!")
                print(f"Registry lists '{nickname}' as Active, but no matching roster tab exists.")
                print("Halting simulation. Please fix the tab name or update the Registry.\n")
                sys.exit()
                
            engine.teams.append(nickname)
            engine.team_ids[nickname] = team_id
    
    print(f"  > Found {len(engine.teams)} active franchises: {', '.join(engine.teams)}")
    
    engine.standings = {team: {"W": 0, "L": 0, "RS": 0, "RA": 0} for team in engine.teams}

    # Initialize ALL stat tracking keys for the engine
    for team in engine.teams:
        records = SHEET.worksheet(team).get_all_records()
        engine.rosters[team] = records
        for player in records:
            player["Max Stam"] = int(player.get("Max Stam", 0) or 0)
            player["Cur Stam"] = int(player.get("Cur Stam", 0) or 0)
            player.setdefault("Cur Hit Strk", 0)
            player.setdefault("Max Hit Strk", 0)
            player.setdefault("Cur OBP Strk", 0)
            player.setdefault("Max OBP Strk", 0)
            player.setdefault("Cur Scoreless Outs", 0)
            player.setdefault("Max Scoreless Outs", 0)
            player.setdefault("Recent Form", "")
            
            pid = str(player["ID"])
            engine.player_stats[pid] = {
                "ID": pid, "Name": player["Name"], "Team": team, "Pos": player["Pos"],
                "G": 0, "PA": 0, "AB": 0, "R": 0, "H": 0, "1B": 0, "2B": 0, "3B": 0, "HR": 0, 
                "RBI": 0, "BB": 0, "HBP": 0, "K_bat": 0, "SB": 0, "CS": 0, "SF": 0, "GIDP": 0,
                # CHANGED IP TO Outs_pit
                "Outs_pit": 0, "H_allowed": 0, "R_allowed": 0, "ER": 0, "HR_allowed": 0, 
                "BB_allowed": 0, "HBP_allowed": 0, "K_pit": 0, "W": 0, "L": 0, "SV": 0, 
                "HLD": 0, "BS": 0, "Pitches": 0, "CG": 0, "SHO": 0,
                "PO": 0, "A": 0, "E": 0, "TC": 0
            }

    load_stadium_dimensions(engine, SHEET)

    # Load existing Hitting Stats
    try:
        h_records = SHEET.worksheet("HStats").get_all_records()
        for row in h_records:
            pid = str(row.get("ID", ""))
            if pid in engine.player_stats:
                s = engine.player_stats[pid]
                for key in ["G", "PA", "AB", "R", "H", "1B", "2B", "3B", "HR", "RBI", "BB", "HBP", "SB", "CS", "SF", "GIDP"]:
                    if key == "K": s["K_bat"] = int(row.get("K", 0) or 0)
                    else: s[key] = int(row.get(key, 0) or 0)
    except Exception: pass
    
    # Load existing Pitching Stats
    try:
        p_records = SHEET.worksheet("PStats").get_all_records()
        for row in p_records:
            pid = str(row.get("ID", ""))
            if pid in engine.player_stats:
                s = engine.player_stats[pid]
                
                # FIXED: Parse the "12.2" string back into raw Outs!
                ip_raw = str(row.get("IP", "0.0"))
                if '.' in ip_raw:
                    innings, partial = ip_raw.split('.')
                    s["Outs_pit"] = (int(innings) * 3) + int(partial)
                else:
                    s["Outs_pit"] = int(float(ip_raw) * 3)
                    
                for key in ["W", "L", "SV", "HLD", "BS", "ER", "CG", "SHO", "Pitches"]:
                    s[key] = int(row.get(key, 0) or 0)
                s["H_allowed"] = int(row.get("H", 0) or 0)
                s["R_allowed"] = int(row.get("R", 0) or 0)
                s["HR_allowed"] = int(row.get("HR", 0) or 0)
                s["BB_allowed"] = int(row.get("BB", 0) or 0)
                s["HBP_allowed"] = int(row.get("HBP", 0) or 0)
                s["K_pit"] = int(row.get("K", 0) or 0)
                
                # Ensure Pitchers get their G count if they only pitched
                s["G"] = max(s["G"], int(row.get("G", 0) or 0))
    except Exception: pass
    
    # Load existing Fielding Stats
    try:
        f_records = SHEET.worksheet("FStats").get_all_records()
        for row in f_records:
            pid = str(row.get("ID", ""))
            if pid in engine.player_stats:
                s = engine.player_stats[pid]
                for key in ["PO", "A", "E", "TC"]:
                    s[key] = int(row.get(key, 0) or 0)
                # Ensure Fielders get their G count
                s["G"] = max(s["G"], int(row.get("G", 0) or 0))
    except Exception: pass

    # For the RecordBook, we still want to pass some list of records. We can pass the h_records if they exist.
    try: h_records = SHEET.worksheet("HStats").get_all_records()
    except Exception: h_records = []
    engine.record_book = RecordBook(h_records)

    try:
        std_records = SHEET.worksheet("Standings").get_all_records()
        for r in std_records:
            t = r["Team"]
            if t in engine.standings:
                engine.standings[t].update({"W": r["W"], "L": r["L"], "RS": r["RS"], "RA": r["RA"]})
    except Exception: pass

    try:
        gl_records = SHEET.worksheet("GameLog").get_all_records()
        engine.game_log = [[r["Away Team"], r["Away Score"], r["Away W/L"], 
                          r["Home Team"], r["Home Score"], r["Home W/L"]] for r in gl_records]
        engine.current_day = len(engine.game_log) // (len(engine.teams) // 2) if engine.teams else 0
    except Exception: pass

def build_team_object(engine, team_name, starting_pitcher_role):
    team_rows = engine.rosters[team_name]
    hitters, defense, bullpen, starting_pitcher = [], {}, [], None
    
    for row in team_rows:
        attributes = {
            "bats": "R", "throws": "R",  
            "batting": {
                "timing": int(row.get("Con.Timing", 0) or 0), "barreling": int(row.get("Con.Barrel", 0) or 0),
                "strength": int(row.get("Pow.Str", 0) or 0), "bat_speed": int(row.get("Pow.BatSpd", 0) or 0),
                "elevation": int(row.get("Pow.Elev", 0) or 0), "eye": int(row.get("Disc.Eye", 0) or 0),
                "restraint": int(row.get("Disc.Restr", 0) or 0), "stamina": int(row.get("Max Stam", 0) or 0)
            },
            "baserunning": {
                "sprint_speed": int(row.get("Spd.Sprint", 0) or 0), "instincts": int(row.get("Spd.Inst", 0) or 0)
            },
            "defense": {
                "def.range": int(row.get("def.Range", row.get("Def.Range", 0)) or 0),
                "def.reaction": int(row.get("def.reaction", row.get("Def.React", 0)) or 0),
                "def.glove": int(row.get("def.glove", row.get("Def.Glove", 0)) or 0),
                "def.ArmStr": int(row.get("def.ArmStr", row.get("Def.ArmStr", 0)) or 0),
                "def.ArmAcc": int(row.get("def.ArmAcc", row.get("Def.ArmAcc", 0)) or 0)
            },
            "pitching": {
                "arm_speed": int(row.get("Vel.ArmSpd", 0) or 0), "deception": int(row.get("Vel.Decept", 0) or 0),
                "accuracy": int(row.get("Ctrl.Acc", 0) or 0), "command": int(row.get("Ctrl.Cmd", 0) or 0),
                "spin_rate": int(row.get("Mov.Spin", 0) or 0), "bite": int(row.get("Mov.Bite", 0) or 0),
                "stamina": int(row.get("Max Stam", 0) or 0)
            },
            "development": {
                "age": int(row.get("Age", 18) or 18), "archetype": str(row.get("Arch", "Unknown"))
            },
            "strategy": {},
            "role": str(row.get("Role/Order", "")).strip(),
            "primary_pos": str(row.get("Primary Pos", row.get("Pos", "DH"))),
            "game_pos": str(row.get("Game Pos", row.get("Pos", "DH"))),
            "current_hit_streak": int(row.get("Cur Hit Strk", 0) or 0),
            "longest_hit_streak": int(row.get("Max Hit Strk", 0) or 0),
            "current_obp_streak": int(row.get("Cur OBP Strk", 0) or 0),
            "longest_obp_streak": int(row.get("Max OBP Strk", 0) or 0),
            "current_scoreless_outs": int(row.get("Cur Scoreless Outs", 0) or 0),
            "longest_scoreless_outs": int(row.get("Max Scoreless Outs", 0) or 0),
            "recent_form": str(row.get("Recent Form", "")),
            "traits": [t.strip() for t in [str(row.get("Trait1", "")), str(row.get("Trait2", "")), str(row.get("Trait3", ""))] if t.strip() and t.strip() != "-"]
        }
        
        player = Player(row["ID"], row["Name"], attributes)
        
        player.traits = attributes["traits"]
        player.current_stamina = int(row.get("Cur Stam", 0) or 0)
        
        role = attributes["role"]
        game_pos = attributes["game_pos"]
            
            # 1. STARTING HITTERS & FIELDERS
        if role.isdigit() and 1 <= int(role) <= 9: 
            hitters.append((int(role), player))
                
                # ---> THE FIX: Only put them in the field if they are starting! <---
            if game_pos and game_pos not in ["DH", "P"]:
                defense[game_pos] = player
                    
            # 2. PITCHERS
        elif game_pos == "P":
            if role == starting_pitcher_role: 
                starting_pitcher = player
            elif role not in ["Bench", "Minors"]: 
                bullpen.append(player)

        if starting_pitcher: defense["P"] = starting_pitcher

    hitters.sort(key=lambda x: x[0])
    lineup = [h[1] for h in hitters][:9]
    
    park_data = engine.parks.get(team_name, {})
    park_dims = park_data.get("dimensions", None)
    park_heights = park_data.get("heights", None)
    
    team_stadium = Stadium(name=f"{team_name} Park", custom_dimensions=park_dims, custom_heights=park_heights)
    
    team_obj = Team(team_name, lineup, starting_pitcher, defense, stadium=team_stadium)
    team_obj.bullpen = bullpen

    historical_records = engine.record_book.records
    historical_ids = {str(r["ID"]) for r in historical_records}
    for player in team_obj.lineup + team_obj.game_pitchers + team_obj.bullpen:
        if player:
            player.is_rookie = str(player.player_id) not in historical_ids

    return team_obj