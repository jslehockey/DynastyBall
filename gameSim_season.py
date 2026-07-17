# ==========================================
# gameSim_season.py
# ==========================================
# Handles macro league events: Playoffs, Offseason,
# Draft Class Generation, and Stamina Recovery.
# ==========================================
import random
from model_player import Player
import gameSim_reporter as reporter
import gameSim_builder as builder

def recover_daily_stamina(engine, is_bye=False):
    for roster in engine.rosters.values():
        for player in roster:
            # 1. Extract Traits
            traits = [
                str(player.get("Trait1", "")), 
                str(player.get("Trait2", "")), 
                str(player.get("Trait3", ""))
            ]
            
            # 2. Determine Position
            pos = str(player.get("Pos", "DH"))
            game_pos = str(player.get("Game Pos", pos))
            is_pitcher = (pos == "P" or game_pos == "P")
            
            # 3. Apply Your Custom Recovery Rates
            if is_pitcher:
                base_recovery = 30 if "Rubber Arm" in traits else 20
            else:
                base_recovery = 26  # All everyday batters
                
            # Apply the Bye Day rest bonus if the engine triggers it
            recovery_amount = base_recovery * 2 if is_bye else base_recovery
            
            # 4. Cap at Maximum
            max_stam = int(player.get("Max Stam", 100))
            cur_stam = int(player.get("Cur Stam", 100))
            
            player["Cur Stam"] = min(max_stam, cur_stam + recovery_amount)

def get_current_sim_block(engine):
    max_games_played = max((team["W"] + team["L"]) for team in engine.standings.values())
    if max_games_played < 28: return (max_games_played // 4) + 1
    elif max_games_played < 61: return 7 + ((max_games_played - 28) // 3) + 1
    elif max_games_played < 89: return 18 + ((max_games_played - 61) // 4) + 1
    elif max_games_played >= 89 and max_games_played < 93: return 26
    else: return 27

def simulate_playoff_block(engine, SHEET):
    sorted_teams = sorted(engine.teams, key=lambda x: engine.standings[x]["W"], reverse=True)
    seed1, seed2, seed3, seed4 = sorted_teams[0], sorted_teams[1], sorted_teams[2], sorted_teams[3]
    
    print(f"\n🏆 PLAYOFFS INITIATED 🏆")
    series_a_scores = {seed1: [], seed4: []}
    series_b_scores = {seed2: [], seed3: []}
    
    for day in range(1, 5):
        recover_daily_stamina(engine)
        if day == 4:
            reporter.export_all(engine, SHEET)
            break
            
        games_played_today = False
        if len(series_a_scores[seed1]) < 3 and series_a_scores[seed1].count("W") < 2 and series_a_scores[seed4].count("W") < 2:
            games_played_today = True
            away = seed4 if day in [1, 3] else seed1
            home = seed1 if day in [1, 3] else seed4
            engine.simulate_game(away, home, match_type="Playoffs")
            last_game = engine.game_log[-1] 
            series_a_scores[away].append(last_game[1])
            series_a_scores[home].append(last_game[4])
            
        if len(series_b_scores[seed2]) < 3 and series_b_scores[seed2].count("W") < 2 and series_b_scores[seed3].count("W") < 2:
            games_played_today = True
            away = seed3 if day in [1, 3] else seed2
            home = seed2 if day in [1, 3] else seed3
            engine.simulate_game(away, home, match_type="Playoffs")
            last_game = engine.game_log[-1]
            series_b_scores[away].append(last_game[1])
            series_b_scores[home].append(last_game[4])

        if not games_played_today: break
        reporter.export_all(engine, SHEET)
        
    adv_a = seed1 if sum(1 for i in range(len(series_a_scores[seed1])) if series_a_scores[seed1][i] > series_a_scores[seed4][i]) == 2 else seed4
    adv_b = seed2 if sum(1 for i in range(len(series_b_scores[seed2])) if series_b_scores[seed2][i] > series_b_scores[seed3][i]) == 2 else seed3
    
    high_seed = adv_a if sorted_teams.index(adv_a) < sorted_teams.index(adv_b) else adv_b
    low_seed = adv_b if high_seed == adv_a else adv_a
    finals_scores = {high_seed: [], low_seed: []}

    for day in range(1, 5):
        recover_daily_stamina(engine)
        if day == 4:
            reporter.export_all(engine, SHEET)
            break

        if len(finals_scores[high_seed]) < 3 and sum(1 for i in range(len(finals_scores[high_seed])) if finals_scores[high_seed][i] > finals_scores[low_seed][i]) < 2 and sum(1 for i in range(len(finals_scores[low_seed])) if finals_scores[low_seed][i] > finals_scores[high_seed][i]) < 2:
            away = low_seed if day in [1, 3] else high_seed
            home = high_seed if day in [1, 3] else low_seed
            engine.simulate_game(away, home, match_type="Playoffs")
            last_game = engine.game_log[-1]
            finals_scores[away].append(last_game[1])
            finals_scores[home].append(last_game[4])
            reporter.export_all(engine, SHEET)
        else:
            break
            
    reporter.export_playoff_bracket(engine, SHEET, series_a_scores, series_b_scores, finals_scores)

def generate_draft_class(SHEET):
    print("\n🧬 GENERATING NEW DRAFT CLASS...")
    ws = SHEET.worksheet("Draft Class")
    ws.clear()

    first_names = ["Jackson", "Liam", "Noah", "Aiden", "Caden", "Grayson", "Lucas", "Mason", "Oliver", "Elijah"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "P", "P", "P"]

    pitching_traits = ["Marathon Man", "Escape Artist", "Groundball Guru", "Putaway Pitcher", "Rubber Arm", "Ice in the Veins", "Pitch to Contact", "Lights Out"]
    hitting_traits = ["Clutch", "Table Setter", "First Pitch Killer", "Gold Glover", "Speed Demon", "Unfazed", "Platoon Punisher", "Launch Angle God"]

    headers = ["ID", "Name", "Pos", "Age", "Arch", "Trait1", "Trait2", "Trait3", "TraitCount"] + \
          ["Con.Timing", "Con.Barrel", "Pow.Str", "Pow.BatSpd", "Pow.Elev", "Disc.Eye", "Disc.Restr", 
           "Spd.Sprint", "Spd.Inst", "def.Range", "Def.React", "Def.Glove", "Def.ArmStr", "Def.ArmAcc", 
           "Vel.ArmSpd", "Vel.Decept", "Ctrl.Acc", "Ctrl.Cmd", "Mov.Spin", "Mov.Bite", "Max Stam", "Cur Stam"]

    grid = [headers]

    for i in range(50):
        pos = random.choice(positions)
        age = random.randint(18, 22)
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        pid = f"2027{str(i).zfill(8)}"
    
        player_traits = []
        available_traits = pitching_traits.copy() if pos == "P" else hitting_traits.copy()
    
        if random.uniform(0, 100) <= 60.0:
            t1 = random.choice(available_traits)
            player_traits.append(t1)
            available_traits.remove(t1)
        
            if random.uniform(0, 100) <= 25.0:
                t2 = random.choice(available_traits)
                player_traits.append(t2)
                available_traits.remove(t2)
            
                if random.uniform(0, 100) <= 10.0:
                    t3 = random.choice(available_traits)
                    player_traits.append(t3)
                    
        t1_col = player_traits[0] if len(player_traits) > 0 else "-"
        t2_col = player_traits[1] if len(player_traits) > 1 else "-"
        t3_col = player_traits[2] if len(player_traits) > 2 else "-"
        t_count = len(player_traits)
        
        stats = [random.randint(35, 65) for _ in range(20)]
        stam = random.randint(80, 100) if pos == "P" else 100
        
        row = [pid, name, pos, age, "Rookie", t1_col, t2_col, t3_col, t_count] + stats + [stam, stam]
        grid.append(row)
        
    ws.append_rows(grid)
    print("✅ 50 Prospects (with Traits!) exported to 'Draft Class' tab!")

def run_offseason_progression(engine, SHEET):
    print("\n🍂 INITIATING OFFSEASON PROGRESSION (Block 28) 🍂")
    
    current_year = 2026 
    reporter.log_season_history(engine, SHEET, current_year)
    
    for team_name, roster in engine.rosters.items():
        for flat_player in roster:
            
            # 1. Build or retrieve the player object
            player_obj = builder.build_team_object(engine, team_name, "SP1").defense.get(flat_player.get("Game Pos", "DH"))
            if not player_obj: 
                player_obj = Player(flat_player["ID"], flat_player["Name"], {
                    "development": {"age": flat_player["Age"], "peak_age": 27}, 
                    "batting": {}, "pitching": {}, "defense": {}, "baserunning": {}
                })
            
            # 2. Map flat dictionary values to the object attributes
            for cat in ["Con.Timing", "Con.Barrel", "Pow.Str", "Pow.BatSpd", "Pow.Elev", "Disc.Eye", "Disc.Restr"]:
                player_obj.attributes["batting"][cat.split(".")[1].lower()] = flat_player.get(cat, 0)
            for cat in ["Vel.ArmSpd", "Vel.Decept", "Ctrl.Acc", "Ctrl.Cmd", "Mov.Spin", "Mov.Bite"]:
                player_obj.attributes["pitching"][cat.split(".")[1].lower()] = flat_player.get(cat, 0)
            for cat in ["def.Range", "Def.React", "Def.Glove", "Def.ArmStr", "Def.ArmAcc"]:
                player_obj.attributes["defense"][cat.lower()] = flat_player.get(cat, 0)
            
            # ============================================================
            # 3. PRE-ALPHA OVERRIDE: Age-Based Progression & Regression
            # ============================================================
            age = flat_player.get("Age", 25)
            
            def apply_modifiers(category_dict):
                for attr, val in category_dict.items():
                    if not isinstance(val, (int, float)): continue
                    
                    if age <= 26:
                        # Progress 1 to 3 points (Capped at 99)
                        category_dict[attr] = min(99, val + random.randint(1, 3))
                    elif age > 33:
                        # Regress 1 to 3 points (Floor of 1)
                        category_dict[attr] = max(1, val - random.randint(1, 3))

            # Execute modifications across the loaded dictionaries
            apply_modifiers(player_obj.attributes["batting"])
            apply_modifiers(player_obj.attributes["pitching"])
            apply_modifiers(player_obj.attributes["defense"])
            # ============================================================

            # Run existing aging method if it handles other logic (like stamina decay)
            if hasattr(player_obj, "process_offseason_aging"):
                player_obj.process_offseason_aging()
                
            flat_player["Age"] += 1
            
            # 4. Map the modified attributes back to the flat dictionary
            for cat, key in [("Con.Timing", "timing"), ("Con.Barrel", "barreling"), ("Pow.Str", "strength"), ("Pow.BatSpd", "bat_speed"), ("Pow.Elev", "elevation"), ("Disc.Eye", "eye"), ("Disc.Restr", "restraint")]:
                flat_player[cat] = player_obj.attributes["batting"].get(key, flat_player.get(cat))
                
            for cat, key in [("Vel.ArmSpd", "arm_speed"), ("Vel.Decept", "deception"), ("Ctrl.Acc", "accuracy"), ("Ctrl.Cmd", "command"), ("Mov.Spin", "spin_rate"), ("Mov.Bite", "bite")]:
                flat_player[cat] = player_obj.attributes["pitching"].get(key, flat_player.get(cat))
                
            # FIXED: Added the loop to map defense stats back so progression actually saves
            for cat in ["def.Range", "Def.React", "Def.Glove", "Def.ArmStr", "Def.ArmAcc"]:
                flat_player[cat] = player_obj.attributes["defense"].get(cat.lower(), flat_player.get(cat))
    
    reporter.export_all(engine, SHEET)
    generate_draft_class(SHEET)
    print("Offseason complete! Ready for next season.")