import random
import gspread
import time
from models import Player, Team, LeagueEnvironment, Stadium
from game_flow import FullGame

# --- CONFIGURATION ---
SPREADSHEET_ID = "1mC6-qF2_niu5756t5Q1yI-QJL_fZcvaF_KkOTrHX3Yc"
CLIENT = gspread.service_account(filename='credentials.json')
SHEET = CLIENT.open_by_key(SPREADSHEET_ID)

class LeagueWeatherSystem:
    def __init__(self):
        self.daily_forecasts = {}

    def generate_daily_weather(self, day_number, teams):
        """Generates a unique forecast for every home stadium for the given day."""
        self.daily_forecasts[day_number] = {}
        for team in teams:
            temp = random.randint(45, 95)
            wind_speed = random.randint(0, 20)
            wind_direction = random.choice(["Blowing In", "Blowing Out", "Crosswind Left", "Crosswind Right", "Calm"])
            precipitation = random.choices(["None", "Rain"], weights=[85, 15])[0] # 15% chance of rain
            
            self.daily_forecasts[day_number][team] = {
                "temp": temp,
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "precipitation": precipitation
            }

    def get_game_weather(self, day_number, home_team):
        """Fetches the specific weather for the home stadium."""
        return self.daily_forecasts.get(day_number, {}).get(home_team, {
            "temp": 70, "wind_speed": 0, "wind_direction": "Calm", "precipitation": "None"
        })
    
class SimulationEngine:
    def __init__(self):
        self.teams = [f"Team{i}" for i in range(1, 9)]
        self.rosters = {}
        self.parks = {} 
        self.standings = {team: {"W": 0, "L": 0, "RS": 0, "RA": 0} for team in self.teams}
        self.game_log = []
        self.boxscores = []
        self.player_stats = {}
        self.current_day = 0
        self.weather_system = LeagueWeatherSystem()

    def _load_stadium_dimensions(self):
        print("  > Loading stadium dimensions and wall heights from 'Parks' sheet...")
        try:
            park_records = SHEET.worksheet("Parks").get_all_records()
            
            # Distance limits exactly as you specified
            dist_limits = {
                "Left Field Line": (300, 350), "Dead Left Field": (320, 375),
                "Left Center Gap": (340, 400), "Dead Center": (380, 425),
                "Right Center Gap": (340, 400), "Dead Right Field": (320, 375),
                "Right Field Line": (300, 350)
            }
            height_limits = (10, 50)
            
            def validate_val(value, min_val, max_val, default):
                """Ensures the value is an integer and falls within the zone's specific limits."""
                try:
                    val = int(value)
                    if min_val <= val <= max_val:
                        return val
                    else:
                        print(f"    [WARNING] Value {val} out of bounds ({min_val}-{max_val}). Defaulting to {default}.")
                        return default
                except (ValueError, TypeError):
                    return default
                    
            def get_key(row, partial_matches):
                """Fuzzy matcher: finds the column value even if the header text changes slightly."""
                for k in row.keys():
                    for match in partial_matches:
                        if match.lower() in k.lower():
                            return row[k]
                return None

            for row in park_records:
                team_name = row.get("Team")
                if not team_name: continue

                # 1. Extract and Validate Distances
                dimensions = {
                    "Left Field Line": validate_val(get_key(row, ["Lef Field Line", "Left Field Line"]), *dist_limits["Left Field Line"], 330),
                    "Dead Left Field": validate_val(get_key(row, ["Dead Left Field"]), *dist_limits["Dead Left Field"], 360),
                    "Left Center Gap": validate_val(get_key(row, ["Left Center Gap"]), *dist_limits["Left Center Gap"], 380),
                    "Dead Center": validate_val(get_key(row, ["Dead Center"]), *dist_limits["Dead Center"], 400),
                    "Right Center Gap": validate_val(get_key(row, ["Right Center Gap"]), *dist_limits["Right Center Gap"], 380),
                    "Dead Right Field": validate_val(get_key(row, ["Dead Right Field"]), *dist_limits["Dead Right Field"], 360),
                    "Right Field Line": validate_val(get_key(row, ["Right Field Line"]), *dist_limits["Right Field Line"], 330)
                }

                # 2. Extract and Validate Heights
                heights = {
                    "Left Field Line": validate_val(get_key(row, ["Left Field Fence", "LF Fence"]), *height_limits, 12),
                    "Dead Left Field": validate_val(get_key(row, ["Dead Left Fence"]), *height_limits, 12),
                    "Left Center Gap": validate_val(get_key(row, ["Left Center Fence"]), *height_limits, 12),
                    "Dead Center": validate_val(get_key(row, ["Dead Center Fence"]), *height_limits, 12),
                    "Right Center Gap": validate_val(get_key(row, ["Right Center Fence"]), *height_limits, 12),
                    "Dead Right Field": validate_val(get_key(row, ["Dead Right Fence"]), *height_limits, 12),
                    "Right Field Line": validate_val(get_key(row, ["Right Field Line Fence", "RF Fence"]), *height_limits, 12)
                }
                
                # 3. Store both dictionaries under the team's name
                self.parks[team_name] = {"dimensions": dimensions, "heights": heights}
                
        except Exception as e:
            print(f"  > [WARNING] Could not load 'Parks' tab. Defaulting all stadiums to standard. Error: {e}")

    def load_state(self):
        print("Loading current game state from Sheets...")
        for team in self.teams:
            records = SHEET.worksheet(team).get_all_records()
            self.rosters[team] = records
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
                self.player_stats[pid] = {
                    "ID": pid, "Name": player["Name"], "Team": team, "Pos": player["Pos"],
                    "G": 0, "AB": 0, "H": 0, "HR": 0, "RBI": 0, "R": 0, "AVG": ".000",
                    "IP": 0, "ER": 0, "K": 0, "BB": 0, "ERA": "0.00"
                }

        self._load_stadium_dimensions()

        try:
            stats_records = SHEET.worksheet("Stats").get_all_records()
            for r in stats_records:
                self.player_stats[str(r["ID"])] = r
        except Exception: pass

        try:
            std_records = SHEET.worksheet("Standings").get_all_records()
            for r in std_records:
                t = r["Team"]
                if t in self.standings:
                    self.standings[t].update({"W": r["W"], "L": r["L"], "RS": r["RS"], "RA": r["RA"]})
        except Exception: pass

        try:
            gl_records = SHEET.worksheet("GameLog").get_all_records()
            self.game_log = [[r["Away Team"], r["Away Score"], r["Away W/L"], 
                              r["Home Team"], r["Home Score"], r["Home W/L"]] for r in gl_records]
            self.current_day = len(self.game_log) // 4 
        except Exception: pass

    def get_schedule_for_day(self, day_index):
        master_schedule = [
            [("Team2", "Team1"), ("Team4", "Team3"), ("Team6", "Team5"), ("Team8", "Team7")], 
            [("Team1", "Team4"), ("Team3", "Team2"), ("Team5", "Team8"), ("Team7", "Team6")], 
            [("Team3", "Team1"), ("Team2", "Team4"), ("Team7", "Team5"), ("Team8", "Team6")], 
            [("Team1", "Team5"), ("Team2", "Team6"), ("Team3", "Team7"), ("Team4", "Team8")], 
            [("Team6", "Team1"), ("Team5", "Team2"), ("Team8", "Team3"), ("Team7", "Team4")], 
            [("Team1", "Team7"), ("Team2", "Team8"), ("Team3", "Team5"), ("Team4", "Team6")], 
            [("Team8", "Team1"), ("Team7", "Team2"), ("Team6", "Team3"), ("Team5", "Team4")]  
        ]
        return master_schedule[day_index % len(master_schedule)]

    def simulate_game(self, away_team, home_team):
        away_games = self.standings[away_team]["W"] + self.standings[away_team]["L"]
        home_games = self.standings[home_team]["W"] + self.standings[home_team]["L"]
        
        away_sp_role = f"SP{(away_games % 5) + 1}"
        home_sp_role = f"SP{(home_games % 5) + 1}"

        away_obj = self._build_team_object(away_team, away_sp_role)
        home_obj = self._build_team_object(home_team, home_sp_role)

        env = LeagueEnvironment()
        local_weather = self.weather_system.get_game_weather(self.current_day, home_team)
        game = FullGame(away_obj, home_obj, env, weather=local_weather, career_stats=self.player_stats) 
        game.play_game()

        # --- NEW: BOXSCORE GENERATOR ---
        away_hits = game.away.stats["batting"]["H"]
        home_hits = game.home.stats["batting"]["H"]
        away_errors = game.away.stats["defense"]["E"]
        home_errors = game.home.stats["defense"]["E"]
        
        # Calculate how many innings were actually played
        max_innings = max(9, game.inning - 1)
        
        header_row = ["Team"] + [str(i) for i in range(1, max_innings + 1)] + ["R", "H", "E"]
        
        # Format Away Line
        away_row = [away_team] + [str(x) if x is not None else "-" for x in game.away.linescore]
        while len(away_row) <= max_innings: away_row.append("-")
        away_row += [str(game.away.stats["batting"]["R"]), str(away_hits), str(away_errors)]
        
        # Format Home Line
        home_row = [home_team] + [str(x) if x is not None else "X" for x in game.home.linescore]
        while len(home_row) <= max_innings: home_row.append("X" if len(home_row) == max_innings else "-")
        home_row += [str(game.home.stats["batting"]["R"]), str(home_hits), str(home_errors)]
        
        # Extract Pitching Decisions
        wp_name, lp_name, sv_name = "", "", ""
        all_pitchers = game.away.used_pitchers + [game.away.pitcher] + game.home.used_pitchers + [game.home.pitcher]
        for p in all_pitchers:
            decision = getattr(p, 'game_decision', '')
            if decision == "W": wp_name = p.name
            elif decision == "L": lp_name = p.name
            elif decision == "SV": sv_name = p.name
            
        decision_str = f"WP: {wp_name} | LP: {lp_name}"
        if sv_name: decision_str += f" | SV: {sv_name}"

        # Append the formatted block to our master list
        self.boxscores.append([f"Day {self.current_day}: {away_team} at {home_team}"])
        self.boxscores.append(header_row)
        self.boxscores.append(away_row)
        self.boxscores.append(home_row)
        self.boxscores.append([decision_str])
        self.boxscores.append([]) # Blank row for spacing
        # -------------------------------

        away_runs = game.away.stats["batting"]["R"]
        home_runs = game.home.stats["batting"]["R"]
        
        if home_runs > away_runs:
            home_wl, away_wl = "W", "L"
            self.standings[home_team]["W"] += 1
            self.standings[away_team]["L"] += 1
        else:
            home_wl, away_wl = "L", "W"
            self.standings[home_team]["L"] += 1
            self.standings[away_team]["W"] += 1
            
        self.standings[home_team]["RS"] += home_runs
        self.standings[home_team]["RA"] += away_runs
        self.standings[away_team]["RS"] += away_runs
        self.standings[away_team]["RA"] += home_runs
        
        self.game_log.append([away_team, away_runs, away_wl, home_team, home_runs, home_wl])
        self._extract_post_game_data(away_team, away_obj)
        self._extract_post_game_data(home_team, home_obj)

    def _build_team_object(self, team_name, starting_pitcher_role):
        team_rows = self.rosters[team_name]
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
            
            if role.isdigit() and 1 <= int(role) <= 9: hitters.append((int(role), player))
            elif game_pos == "P":
                if role == starting_pitcher_role: starting_pitcher = player
                elif role not in ["Bench", "Minors"]: bullpen.append(player)

            if game_pos and game_pos not in ["DH", "P", "Bench", "Minors"]:
                defense[game_pos] = player
                
        if starting_pitcher: defense["P"] = starting_pitcher

        hitters.sort(key=lambda x: x[0])
        lineup = [h[1] for h in hitters][:9]
        
        park_data = self.parks.get(team_name, {})
        park_dims = park_data.get("dimensions", None)
        park_heights = park_data.get("heights", None)
        
        team_stadium = Stadium(name=f"{team_name} Park", custom_dimensions=park_dims, custom_heights=park_heights)
        
        team_obj = Team(team_name, lineup, starting_pitcher, defense, stadium=team_stadium)
        team_obj.bullpen = bullpen
        return team_obj

    def _extract_post_game_data(self, team_name, team_obj):
        all_players = team_obj.lineup + team_obj.game_pitchers + team_obj.bullpen
        for obj_player in all_players:
            if not obj_player: continue
            pid = str(obj_player.player_id)
            if pid in self.player_stats:
                s = self.player_stats[pid]
                b_stats = obj_player.stats["batting"]
                p_stats = obj_player.stats["pitching"]
                
                if b_stats["PA"] > 0 or p_stats["Outs"] > 0: s["G"] += 1
                s["AB"] += b_stats["AB"]; s["H"] += b_stats["H"]
                s["HR"] += b_stats["HR"]; s["RBI"] += b_stats["RBI"]; s["R"] += b_stats["R"]
                s["IP"] += p_stats["Outs"] / 3.0; s["ER"] += p_stats["ER"]
                s["K"] += p_stats["K"]; s["BB"] += p_stats["BB"]
            
            b_stats = obj_player.stats["batting"]
            if b_stats["PA"] > 0:
                new_form = f"{b_stats['H']}-{b_stats['AB']}"
                form_list = [g.strip() for g in obj_player.recent_form_str.split(',') if g.strip()]
                form_list.append(new_form)
                obj_player.recent_form_str = ", ".join(form_list[-5:])

                if b_stats["H"] > 0:
                    obj_player.current_hit_streak += 1
                    obj_player.longest_hit_streak = max(obj_player.current_hit_streak, obj_player.longest_hit_streak)
                elif b_stats["AB"] > 0:
                    obj_player.current_hit_streak = 0
                    
                if (b_stats["H"] + b_stats["BB"] + b_stats.get("HBP", 0)) > 0:
                    obj_player.current_obp_streak += 1
                    obj_player.longest_obp_streak = max(obj_player.current_obp_streak, obj_player.longest_obp_streak)
                else: obj_player.current_obp_streak = 0

            p_stats = obj_player.stats["pitching"]
            if p_stats["Outs"] > 0:
                ip_str = f"{p_stats['Outs'] // 3}.{p_stats['Outs'] % 3}"
                new_form = f"{ip_str}-{p_stats['ER']}"
                form_list = [g.strip() for g in obj_player.recent_form_str.split(',') if g.strip()]
                form_list.append(new_form)
                obj_player.recent_form_str = ", ".join(form_list[-5:])

                if p_stats["ER"] == 0:
                    obj_player.current_scoreless_outs += p_stats["Outs"]
                    obj_player.longest_scoreless_outs = max(obj_player.current_scoreless_outs, obj_player.longest_scoreless_outs)
                else: obj_player.current_scoreless_outs = 0

            for flat_player in self.rosters[team_name]:
                if str(flat_player["ID"]) == pid:
                    max_stam = flat_player.get("Max Stam", 100)
                    flat_player["Cur Stam"] = getattr(obj_player, 'current_stamina', max_stam)
                    flat_player["Cur Hit Strk"] = obj_player.current_hit_streak
                    flat_player["Max Hit Strk"] = obj_player.longest_hit_streak
                    flat_player["Cur OBP Strk"] = obj_player.current_obp_streak
                    flat_player["Max OBP Strk"] = obj_player.longest_obp_streak
                    flat_player["Cur Scoreless Outs"] = obj_player.current_scoreless_outs
                    flat_player["Max Scoreless Outs"] = obj_player.longest_scoreless_outs
                    flat_player["Recent Form"] = obj_player.recent_form_str
                    break

    def recover_daily_stamina(self):
        for roster in self.rosters.values():
            for player in roster:
                traits = [
                    str(player.get("Trait1", "")), 
                    str(player.get("Trait2", "")), 
                    str(player.get("Trait3", ""))
                ]
                
                recovery_amount = 27 if "Rubber Arm" in traits else 20
                
                max_stam = int(player.get("Max Stam", 100))
                cur_stam = int(player.get("Cur Stam", 100))
                
                player["Cur Stam"] = min(max_stam, cur_stam + recovery_amount)

    def export_all(self):
        print("Exporting updated rosters, stats, and standings back to Google Sheets...")
        
        for team_name, roster in self.rosters.items():
            ws = SHEET.worksheet(team_name)
            if not roster: 
                continue
                
            headers = list(roster[0].keys())
            grid = [headers]
            for player in roster:
                row = [player.get(h, "") for h in headers]
                grid.append(row)
                
            ws.update('A1', grid)
            print(f"  > Updated {team_name} fatigue levels.")
            time.sleep(1.5)  

        print("  > Updating Standings...")
        ws_standings = SHEET.worksheet("Standings")
        std_grid = [["Team", "W", "L", "RS", "RA"]]
        
        sorted_standings = sorted(self.standings.items(), key=lambda x: x[1]["W"], reverse=True)
        for team, data in sorted_standings:
            std_grid.append([team, data["W"], data["L"], data["RS"], data["RA"]])
            
        ws_standings.update('A1', std_grid)
        time.sleep(1.5)

        print("  > Updating GameLog...")
        ws_gamelog = SHEET.worksheet("GameLog")
        gl_grid = [["Away Team", "Away Score", "Away W/L", "Home Team", "Home Score", "Home W/L"]] + self.game_log
        ws_gamelog.update('A1', gl_grid)
        time.sleep(1.5)

        # --- NEW: EXPORT BOXSCORES ---
        print("  > Updating Boxscores...")
        try:
            ws_box = SHEET.worksheet("BoxScores")
            if self.boxscores:
                max_len = max(len(row) for row in self.boxscores)
                uniform_boxscores = []
                for row in self.boxscores:
                    padded_row = row + [""] * (max_len - len(row))
                    uniform_boxscores.append(padded_row)
                    
                ws_box.clear()
                ws_box.update('A1', uniform_boxscores)
            time.sleep(1.5)
        except Exception as e:
            print(f"  > [WARNING] Could not update 'Boxscores' tab. Did you create it? Error: {e}")

        print("  > Updating Player Stats...")
        ws_stats = SHEET.worksheet("Stats")
        stat_headers = ["ID", "Name", "Team", "Pos", "G", "AB", "H", "HR", "RBI", "R", "AVG", "IP", "ER", "K", "BB", "ERA"]
        stat_grid = [stat_headers]
        
        for pid, s in self.player_stats.items():
            if s.get("G", 0) == 0 and s.get("AB", 0) == 0 and s.get("IP", 0) == 0:
                continue 

            if s["AB"] > 0:
                avg = s["H"] / s["AB"]
                avg_str = f"{avg:.3f}".lstrip('0')
                if avg == 1.0: avg_str = "1.000"
            else:
                avg_str = ".000"
            s["AVG"] = avg_str
            
            era = (s["ER"] * 9) / s["IP"] if s["IP"] > 0 else 0.0
            s["ERA"] = f"{era:.2f}"
            
            stat_grid.append([
                s["ID"], s["Name"], s["Team"], s["Pos"], s["G"], s["AB"], s["H"], s["HR"], 
                s["RBI"], s["R"], s["AVG"], round(s["IP"], 1), s["ER"], s["K"], s["BB"], s["ERA"]
            ])
            
        ws_stats.clear()
        ws_stats.update('A1', stat_grid)
        
        print("✅ Master Export complete! All tabs are synced.")

    def get_current_sim_block(self):
        max_games_played = max((team["W"] + team["L"]) for team in self.standings.values())
        if max_games_played < 28: return (max_games_played // 4) + 1
        elif max_games_played < 61: return 7 + ((max_games_played - 28) // 3) + 1
        elif max_games_played < 89: return 18 + ((max_games_played - 61) // 4) + 1
        elif max_games_played >= 89 and max_games_played < 93: return 26
        else: return 27

    def _run_daily_slate(self, is_bye):
        self.recover_daily_stamina()
        if is_bye:
            print(f"\n[LEAGUE BYE DAY] All teams are resting and recovering stamina.")
        else:
            self.weather_system.generate_daily_weather(self.current_day, self.teams)
            matchups = self.get_schedule_for_day(self.current_day)
            for away, home in matchups:
                self.simulate_game(away, home)
            self.current_day += 1
        self.export_all()

    def simulate_playoff_block(self):
        sorted_teams = sorted(self.teams, key=lambda x: self.standings[x]["W"], reverse=True)
        seed1, seed2, seed3, seed4 = sorted_teams[0], sorted_teams[1], sorted_teams[2], sorted_teams[3]
        
        print(f"\n🏆 PLAYOFFS INITIATED 🏆")
        series_a_scores = {seed1: [], seed4: []}
        series_b_scores = {seed2: [], seed3: []}
        
        for day in range(1, 5):
            self.recover_daily_stamina()
            if day == 4:
                self.export_all()
                break
                
            games_played_today = False
            if len(series_a_scores[seed1]) < 3 and series_a_scores[seed1].count("W") < 2 and series_a_scores[seed4].count("W") < 2:
                games_played_today = True
                away = seed4 if day in [1, 3] else seed1
                home = seed1 if day in [1, 3] else seed4
                self.simulate_game(away, home)
                last_game = self.game_log[-1] 
                series_a_scores[away].append(last_game[1])
                series_a_scores[home].append(last_game[4])
                
            if len(series_b_scores[seed2]) < 3 and series_b_scores[seed2].count("W") < 2 and series_b_scores[seed3].count("W") < 2:
                games_played_today = True
                away = seed3 if day in [1, 3] else seed2
                home = seed2 if day in [1, 3] else seed3
                self.simulate_game(away, home)
                last_game = self.game_log[-1]
                series_b_scores[away].append(last_game[1])
                series_b_scores[home].append(last_game[4])

            if not games_played_today: break
            self.export_all()
            
        adv_a = seed1 if sum(1 for i in range(len(series_a_scores[seed1])) if series_a_scores[seed1][i] > series_a_scores[seed4][i]) == 2 else seed4
        adv_b = seed2 if sum(1 for i in range(len(series_b_scores[seed2])) if series_b_scores[seed2][i] > series_b_scores[seed3][i]) == 2 else seed3
        
        high_seed = adv_a if sorted_teams.index(adv_a) < sorted_teams.index(adv_b) else adv_b
        low_seed = adv_b if high_seed == adv_a else adv_a
        finals_scores = {high_seed: [], low_seed: []}

        for day in range(1, 5):
            self.recover_daily_stamina()
            if day == 4:
                self.export_all()
                break

            if len(finals_scores[high_seed]) < 3 and sum(1 for i in range(len(finals_scores[high_seed])) if finals_scores[high_seed][i] > finals_scores[low_seed][i]) < 2 and sum(1 for i in range(len(finals_scores[low_seed])) if finals_scores[low_seed][i] > finals_scores[high_seed][i]) < 2:
                away = low_seed if day in [1, 3] else high_seed
                home = high_seed if day in [1, 3] else low_seed
                self.simulate_game(away, home)
                last_game = self.game_log[-1]
                finals_scores[away].append(last_game[1])
                finals_scores[home].append(last_game[4])
                self.export_all()
            else:
                break
                
        self._export_playoff_bracket(series_a_scores, series_b_scores, finals_scores)

    def _export_playoff_bracket(self, a_scores, b_scores, f_scores):
        print("\nExporting Playoff Bracket to Google Sheets...")
        ws = SHEET.worksheet("Playoffs")
        ws.clear()
        
        grid = [
            ["🏆 SEMIFINALS (Best of 3)"],
            ["Team", "Game 1", "Game 2", "Game 3"]
        ]
        
        for series in [a_scores, b_scores]:
            for team_name, scores in series.items():
                row = [team_name] + scores
                while len(row) < 4: row.append("-")
                grid.append(row)
            grid.append([])
            
        grid.append(["🏆 CHAMPIONSHIP FINALS (Best of 3)"])
        grid.append(["Team", "Game 1", "Game 2", "Game 3"])
        for team_name, scores in f_scores.items():
            row = [team_name] + scores
            while len(row) < 4: row.append("-")
            grid.append(row)
            
        ws.append_rows(grid)

    def run_offseason_progression(self):
        print("\n🍂 INITIATING OFFSEASON PROGRESSION (Block 27) 🍂")
        
        for team_name, roster in self.rosters.items():
            for flat_player in roster:
                player_obj = self._build_team_object(team_name, "SP1").defense.get(flat_player.get("Game Pos", "DH"))
                if not player_obj: 
                    player_obj = Player(flat_player["ID"], flat_player["Name"], {"development": {"age": flat_player["Age"], "peak_age": 27}, "batting": {}, "pitching": {}, "defense": {}, "baserunning": {}})
                
                for cat in ["Con.Timing", "Con.Barrel", "Pow.Str", "Pow.BatSpd", "Pow.Elev", "Disc.Eye", "Disc.Restr"]:
                    player_obj.attributes["batting"][cat.split(".")[1].lower()] = flat_player.get(cat, 0)
                for cat in ["Vel.ArmSpd", "Vel.Decept", "Ctrl.Acc", "Ctrl.Cmd", "Mov.Spin", "Mov.Bite"]:
                    player_obj.attributes["pitching"][cat.split(".")[1].lower()] = flat_player.get(cat, 0)
                for cat in ["def.Range", "Def.React", "Def.Glove", "Def.ArmStr", "Def.ArmAcc"]:
                    player_obj.attributes["defense"][cat.lower()] = flat_player.get(cat, 0)
                
                player_obj.process_offseason_aging()
                flat_player["Age"] += 1
                
                for cat, key in [("Con.Timing", "timing"), ("Con.Barrel", "barreling"), ("Pow.Str", "strength"), ("Pow.BatSpd", "bat_speed"), ("Pow.Elev", "elevation"), ("Disc.Eye", "eye"), ("Disc.Restr", "restraint")]:
                    flat_player[cat] = player_obj.attributes["batting"].get(key, flat_player.get(cat))
                for cat, key in [("Vel.ArmSpd", "arm_speed"), ("Vel.Decept", "deception"), ("Ctrl.Acc", "accuracy"), ("Ctrl.Cmd", "command"), ("Mov.Spin", "spin_rate"), ("Mov.Bite", "bite")]:
                    flat_player[cat] = player_obj.attributes["pitching"].get(key, flat_player.get(cat))
        
        self.export_all()
        self.generate_draft_class()
        print("✅ Offseason complete! Ready for next season.")

    def generate_draft_class(self):
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

    def simulate_next_block(self):
        block = self.get_current_sim_block()

        print(f"\n" + "="*50)
        print(f"🚀 INITIATING SIM-STATE BLOCK {block}")
        print("="*50)
        
        if 1 <= block <= 7 or 19 <= block <= 25:
            print(f"Format: 4 Active Game Days")
            for _ in range(4): self._run_daily_slate(is_bye=False)
                
        elif 8 <= block <= 18:
            print(f"Format: 3 Active Game Days, 1 League-Wide Bye")
            bye_day_index = random.choice([1, 2]) 
            for i in range(4):
                self._run_daily_slate(is_bye=(i == bye_day_index))
                
        elif block == 26:
            self.simulate_playoff_block()
            
        elif block == 27:
            self.run_offseason_progression()
        else:
            print("\nSeason has fully concluded. Please reset your Standings to start a new year.")

def run_live_test_environment():
    print("⚾ BASEBALL FRANCHISE CLI ⚾")
    engine = SimulationEngine()
    engine.load_state()
    
    current_block = engine.get_current_sim_block()
    print(f"\n✅ Ready to manually trigger Sim-State Block {current_block}")
    
    input("\nPress ENTER to run the current block (or CTRL+C to quit)...")
    engine.simulate_next_block()
    print("\n🏁 Block complete. Run the script again when you are ready for the next block.")

if __name__ == "__main__":
    run_live_test_environment()