# ==========================================
# GameSim.py (Master Controller)
# ==========================================
# Orchestrates the League Environment, runs the 
# simulation loops, and delegates tasks to submodules.
# ==========================================
import random
import gspread
import time

from model_league import LeagueEnvironment
from flow_fullGame import FullGame
from gameSim_weather import LeagueWeatherSystem

# --- DELEGATED MODULES ---
import gameSim_builder as builder
import gameSim_reporter as reporter
import gameSim_economy as economy
import gameSim_season as season

# --- CONFIGURATION ---
SPREADSHEET_ID = "1mC6-qF2_niu5756t5Q1yI-QJL_fZcvaF_KkOTrHX3Yc"
CLIENT = gspread.service_account(filename='credentials.json')
SHEET = CLIENT.open_by_key(SPREADSHEET_ID)

class SimulationEngine:
    def __init__(self):
        # 1. Static Configuration
        self.system_sheets = [
            "Stats", "StatLog", "GameLog", "Standings", "Parks", 
            "BoxScores", "Playoffs", "Draft Class", "TeamRegistry"
        ]
        
        # 2. State (Populated dynamically via builder)
        self.teams = [] 
        self.team_ids = {}
        self.rosters = {}
        self.parks = {} 
        self.standings = {}
        
        # 3. Game/Season Memory
        self.game_log = []
        self.boxscores = []
        self.player_stats = {}
        self.current_day = 0
        self.weather_system = LeagueWeatherSystem()
        self.record_book = None # Loaded in builder

    def _get_win_pct(self, team_name):
        w = self.standings[team_name]["W"]
        l = self.standings[team_name]["L"]
        return w / (w + l) if (w + l) > 0 else 0.500

    def _count_superstars(self, team_obj):
        """Rough estimation of superstars based on traits/stats until OVR is fully integrated."""
        count = 0
        for p in team_obj.lineup + team_obj.game_pitchers:
            if p and len(p.traits) >= 2: count += 1 
        return count

    def get_schedule_for_day(self, day_index):
        num_teams = len(self.teams)
        if num_teams < 2: 
            return []
            
        teams = self.teams.copy()
        round_num = day_index % (num_teams - 1)
        
        if round_num > 0:
            teams = teams[:1] + teams[-round_num:] + teams[1:-round_num]
            
        matchups = []
        half = num_teams // 2
        
        for i in range(half):
            team_a = teams[i]
            team_b = teams[-1 - i]
            
            if i % 2 == round_num % 2:
                matchups.append((team_a, team_b))
            else:
                matchups.append((team_b, team_a))
                
        return matchups

    def simulate_game(self, away_team, home_team, match_type="Regular"):
        away_games = self.standings[away_team]["W"] + self.standings[away_team]["L"]
        home_games = self.standings[home_team]["W"] + self.standings[home_team]["L"]
        
        away_sp_role = f"SP{(away_games % 5) + 1}"
        home_sp_role = f"SP{(home_games % 5) + 1}"

        away_obj = builder.build_team_object(self, away_team, away_sp_role)
        home_obj = builder.build_team_object(self, home_team, home_sp_role)

        # Calculate Economy & Modifiers
        h_park = self.parks.get(home_team, {})
        a_park = self.parks.get(away_team, {})

        active_stars = self._count_superstars(home_obj) + self._count_superstars(away_obj)

        attendance_data = economy.calculate_match_attendance(
            capacity=h_park.get("capacity", 30000),
            actual_price=h_park.get("ticket_price", 30.00),
            home_tier=h_park.get("tier", 1),
            away_tier=a_park.get("tier", 1),
            match_type=match_type,
            home_prestige=h_park.get("prestige", 50),
            home_win_pct=self._get_win_pct(home_team),
            away_prestige=a_park.get("prestige", 50),
            away_win_pct=self._get_win_pct(away_team),
            active_superstars=active_stars
        )
        
        modifiers = economy.get_homefield_modifiers(attendance_data["attendance"])

        # Record Targets
        away_hr_record = self.record_book.get_franchise_records(away_team, "HR", record_type="season", limit=1)
        home_hr_record = self.record_book.get_franchise_records(home_team, "HR", record_type="season", limit=1)
        
        target_hr_away = away_hr_record[0][3] if away_hr_record else 0
        target_hr_home = home_hr_record[0][3] if home_hr_record else 0

        env = LeagueEnvironment()
        local_weather = self.weather_system.get_game_weather(self.current_day, home_team)
        
        # Execute Core Game Engine
        game = FullGame(
            away_obj, home_obj, env, weather=local_weather, career_stats=self.player_stats, 
            hr_record_target_away=target_hr_away, hr_record_target_home=target_hr_home,
            attendance_data=attendance_data, modifiers=modifiers 
        )
        game.play_game()

        # =====================================
        # Boxscore Formatting & Export Payload
        # =====================================
        away_hits = game.away.stats["batting"]["H"]
        home_hits = game.home.stats["batting"]["H"]
        away_errors = game.away.stats["defense"]["E"]
        home_errors = game.home.stats["defense"]["E"]
        
        max_innings = max(9, game.inning - 1)
        header_row = ["Team"] + [str(i) for i in range(1, max_innings + 1)] + ["R", "H", "E"]
        
        away_row = [away_team] + [str(x) if x is not None else "-" for x in game.away.linescore]
        while len(away_row) <= max_innings: away_row.append("-")
        away_row += [str(game.away.stats["batting"]["R"]), str(away_hits), str(away_errors)]
        
        home_row = [home_team] + [str(x) if x is not None else "X" for x in game.home.linescore]
        while len(home_row) <= max_innings: home_row.append("X" if len(home_row) == max_innings else "-")
        home_row += [str(game.home.stats["batting"]["R"]), str(home_hits), str(home_errors)]
        
        wp_name, lp_name, sv_name = "", "", ""
        all_pitchers = game.away.game_pitchers + game.home.game_pitchers
        for p in all_pitchers:
            decision = getattr(p, 'game_decision', '')
            if decision == "W": wp_name = p.name
            elif decision == "L": lp_name = p.name
            elif decision == "SV": sv_name = p.name
            
        decision_str = f"WP: {wp_name} | LP: {lp_name}"
        if sv_name: decision_str += f" | SV: {sv_name}"

        game_box = []
        game_box.append([f"Day {self.current_day}: {away_team} at {home_team}"])
        
        att_str = f"Attendance: {attendance_data['attendance']:,} ({attendance_data['attendance_pct']}%) | Atmosphere: {modifiers['atmosphere']} | Gate Rev: ${attendance_data['game_revenue']:,.2f}"
        game_box.append([att_str])
        
        game_box.append(header_row)
        game_box.append(away_row)
        game_box.append(home_row)
        game_box.append([decision_str])
        game_box.append([]) 

        game_box.append(["--- BATTING ---"])
        game_box.append([f"{away_team} Hitters", "AB", "R", "H", "HR", "RBI", "BB", "K"])
        for p in game.away.lineup:
            b = p.stats["batting"]
            game_box.append([p.name, b["AB"], b["R"], b["H"], b["HR"], b["RBI"], b["BB"], b["K"]])
            
        game_box.append([])
        game_box.append([f"{home_team} Hitters", "AB", "R", "H", "HR", "RBI", "BB", "K"])
        for p in game.home.lineup:
            b = p.stats["batting"]
            game_box.append([p.name, b["AB"], b["R"], b["H"], b["HR"], b["RBI"], b["BB"], b["K"]])

        game_box.append([])

        game_box.append(["--- PITCHING ---"])
        game_box.append([f"{away_team} Pitchers", "IP", "H", "R", "ER", "BB", "K", "HR", "Pitches"])
        for p in game.away.game_pitchers:
            pit = p.stats["pitching"]
            outs = pit["Outs"]
            ip_str = f"{outs // 3}.{outs % 3}"
            game_box.append([p.name, ip_str, pit["H"], pit["R"], pit["ER"], pit["BB"], pit["K"], pit["HR"], pit["Pitches"]])

        game_box.append([])
        game_box.append([f"{home_team} Pitchers", "IP", "H", "R", "ER", "BB", "K", "HR", "Pitches"])
        for p in game.home.game_pitchers:
            pit = p.stats["pitching"]
            outs = pit["Outs"]
            ip_str = f"{outs // 3}.{outs % 3}"
            game_box.append([p.name, ip_str, pit["H"], pit["R"], pit["ER"], pit["BB"], pit["K"], pit["HR"], pit["Pitches"]])

        post_game_milestones = game.check_milestones()
        for m in post_game_milestones:
            game.game_events.append(["Final", "End", "League", "Game Milestone", "Team/Staff", m])

        event_log = [["--- NOTABLE GAME EVENTS ---"]]
        event_log.append(["Inning", "Half", "Team", "Event Type", "Player", "Play Description"])
        
        if not game.game_events:
            event_log.append(["", "", "", "No notable events recorded.", "", ""])
        else:
            for event in game.game_events:
                event_log.append(event)
                
        max_rows = max(len(game_box), len(event_log))
        pad_width = max(max_innings + 4, 11) + 2
        
        for i in range(max_rows):
            left_row = game_box[i] if i < len(game_box) else []
            right_row = event_log[i] if i < len(event_log) else []
            padded_left = left_row + [""] * (pad_width - len(left_row))
            self.boxscores.append(padded_left + right_row)

        self.boxscores.append(["=" * (pad_width + 6)]) 
        
        # Adjust Standings
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
        
        # Extract Post Game Stats
        self._extract_post_game_data(away_team, away_obj)
        self._extract_post_game_data(home_team, home_obj)

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
                
                s["CG"] = s.get("CG", 0) + p_stats.get("CG", 0)
                s["SHO"] = s.get("SHO", 0) + p_stats.get("SHO", 0)
            
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

    def _run_daily_slate(self, is_bye):
        season.recover_daily_stamina(self)
        if is_bye:
            print(f"\n[LEAGUE BYE DAY] All teams are resting and recovering stamina.")
        else:
            self.weather_system.generate_daily_weather(self.current_day, self.teams)
            matchups = self.get_schedule_for_day(self.current_day)
            for away, home in matchups:
                self.simulate_game(away, home, match_type="Regular")
            self.current_day += 1
        reporter.export_all(self, SHEET)

    def simulate_next_block(self):
        block = season.get_current_sim_block(self)

        print(f"\n" + "="*50)
        print(f"INITIATING SIM-STATE BLOCK {block}")
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
            season.simulate_playoff_block(self, SHEET)
            
        elif block == 27:
            season.run_offseason_progression(self, SHEET)
        else:
            print("\nSeason has fully concluded. Please reset your Standings to start a new year.")

def run_live_test_environment():
    print("BASEBALL FRANCHISE CLI")
    engine = SimulationEngine()
    builder.load_state(engine, SHEET)
    
    current_block = season.get_current_sim_block(engine)
    print(f"\nReady to manually trigger Sim-State Block {current_block}")
    
    input("\nPress ENTER to run the current block (or CTRL+C to quit)...")
    engine.simulate_next_block()
    print("\nBlock complete. Run the script again when you are ready for the next block.")

if __name__ == "__main__":
    run_live_test_environment()