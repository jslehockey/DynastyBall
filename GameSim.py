import random
import gspread
from models import Player, Team, LeagueEnvironment
from game_flow import FullGame

# --- CONFIGURATION ---
SPREADSHEET_ID = "1mC6-qF2_niu5756t5Q1yI-QJL_fZcvaF_KkOTrHX3Yc"
CLIENT = gspread.service_account(filename='credentials.json')
SHEET = CLIENT.open_by_key(SPREADSHEET_ID)

class SimulationEngine:
    def __init__(self):
        self.teams = [f"Team{i}" for i in range(1, 9)]
        self.rosters = {}
        self.standings = {team: {"W": 0, "L": 0, "RS": 0, "RA": 0} for team in self.teams}
        self.game_log = []
        self.player_stats = {}
        self.current_day = 0

    def load_state(self):
        """Loads all persistent state (Rosters, Standings, Stats, GameLog) from Sheets."""
        print("Loading current game state from Sheets...")
        
        for team in self.teams:
            records = SHEET.worksheet(team).get_all_records()
            self.rosters[team] = records
            for player in records:
                player["Max Stam"] = int(player.get("Max Stam", 0) or 0)
                player["Cur Stam"] = int(player.get("Cur Stam", 0) or 0)
                
                pid = str(player["ID"])
                self.player_stats[pid] = {
                    "ID": pid, "Name": player["Name"], "Team": team, "Pos": player["Pos"],
                    "G": 0, "AB": 0, "H": 0, "HR": 0, "RBI": 0, "R": 0, "AVG": ".000",
                    "IP": 0, "ER": 0, "K": 0, "BB": 0, "ERA": "0.00"
                }

        try:
            stats_records = SHEET.worksheet("Stats").get_all_records()
            for r in stats_records:
                self.player_stats[str(r["ID"])] = r
        except Exception:
            print("No existing Stats found. Starting fresh.")

        try:
            std_records = SHEET.worksheet("Standings").get_all_records()
            for r in std_records:
                t = r["Team"]
                if t in self.standings:
                    self.standings[t].update({"W": r["W"], "L": r["L"], "RS": r["RS"], "RA": r["RA"]})
        except Exception:
            print("No existing Standings found. Starting fresh.")

        try:
            gl_records = SHEET.worksheet("GameLog").get_all_records()
            self.game_log = [[r["Away Team"], r["Away Score"], r["Away W/L"], 
                              r["Home Team"], r["Home Score"], r["Home W/L"]] for r in gl_records]
            self.current_day = len(self.game_log) // 4 
        except Exception:
            print("No existing GameLog found. Starting fresh.")

    def get_schedule_for_day(self, day_index):
        """Returns the matchups for the given day using a looped 7-day round-robin schedule."""
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
        print(f"\n======================================")
        print(f"PREPPING GAME: {away_team} @ {home_team}")
        print(f"======================================")

        away_games = self.standings[away_team]["W"] + self.standings[away_team]["L"]
        home_games = self.standings[home_team]["W"] + self.standings[home_team]["L"]
        
        away_sp_role = f"SP{(away_games % 5) + 1}"
        home_sp_role = f"SP{(home_games % 5) + 1}"

        away_obj = self._build_team_object(away_team, away_sp_role)
        home_obj = self._build_team_object(home_team, home_sp_role)

        env = LeagueEnvironment()
        game = FullGame(away_obj, home_obj, env)
        game.play_game()

        print_box_score(game)
        self.export_box_score_to_sheet(game)

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
        """Converts flat Google Sheets data into complex Team and Player objects using 19 sub-stats."""
        team_rows = self.rosters[team_name]
        
        hitters = []
        defense = {}
        starting_pitcher = None
        bullpen = []
        
        for row in team_rows:
            attributes = {
                "bats": "R", "throws": "R",  # Defaulting as it isn't in sheet export currently
                "batting": {
                    "timing": int(row.get("Con.Timing", 0) or 0),
                    "barreling": int(row.get("Con.Barrel", 0) or 0),
                    "strength": int(row.get("Pow.Str", 0) or 0),
                    "bat_speed": int(row.get("Pow.BatSpd", 0) or 0),
                    "elevation": int(row.get("Pow.Elev", 0) or 0),
                    "eye": int(row.get("Disc.Eye", 0) or 0),
                    "restraint": int(row.get("Disc.Restr", 0) or 0),
                    "stamina": int(row.get("Max Stam", 0) or 0)
                },
                "baserunning": {
                    "sprint_speed": int(row.get("Spd.Sprint", 0) or 0),
                    "instincts": int(row.get("Spd.Inst", 0) or 0)
                },
               "defense": {
                    "def.range": int(row.get("def.Range", row.get("Def.Range", 0)) or 0),
                    "def.reaction": int(row.get("def.reaction", row.get("Def.React", 0)) or 0),
                    "def.glove": int(row.get("def.glove", row.get("Def.Glove", 0)) or 0),
                    "def.ArmStr": int(row.get("def.ArmStr", row.get("Def.ArmStr", 0)) or 0),
                    "def.ArmAcc": int(row.get("def.ArmAcc", row.get("Def.ArmAcc", 0)) or 0)
                },
                "pitching": {
                    "arm_speed": int(row.get("Vel.ArmSpd", 0) or 0),
                    "deception": int(row.get("Vel.Decept", 0) or 0),
                    "accuracy": int(row.get("Ctrl.Acc", 0) or 0),
                    "command": int(row.get("Ctrl.Cmd", 0) or 0),
                    "spin_rate": int(row.get("Mov.Spin", 0) or 0),
                    "bite": int(row.get("Mov.Bite", 0) or 0),
                    "stamina": int(row.get("Max Stam", 0) or 0)
                },
                "development": {
                    "age": int(row.get("Age", 18) or 18),
                    "archetype": str(row.get("Arch", "Unknown"))
                },
                "strategy": {},
                "role": str(row.get("Role/Order", "")).strip(),
                "assigned_pos": str(row.get("Pos", ""))
            }
            
            player = Player(row["ID"], row["Name"], attributes)
            player.current_stamina = int(row.get("Cur Stam", 0) or 0)
            player.assigned_pos = str(row.get("Pos", ""))
            
            role = attributes["role"]
            
            # Extract active hitters
            if role.isdigit() and 1 <= int(role) <= 9:
                hitters.append((int(role), player))
                
            elif player.assigned_pos == "P":
                if role == starting_pitcher_role:
                    starting_pitcher = player
                elif role != "Bench" and role != "Minors":
                    bullpen.append(player)

            # Assign defense dictionary
            if player.assigned_pos and player.assigned_pos != "DH" and player.assigned_pos != "P":
                defense[player.assigned_pos] = player
                
        if starting_pitcher:
            defense["P"] = starting_pitcher

        # Sort hitters by their Role/Order integer and unpack to lineup array
        hitters.sort(key=lambda x: x[0])
        lineup = [h[1] for h in hitters][:9]

        team_obj = Team(team_name, lineup, starting_pitcher, defense)
        team_obj.bullpen = bullpen
        
        return team_obj

    def _extract_post_game_data(self, team_name, team_obj):
        """Pulls updated stats and stamina from OOP models to the flat sheet format."""
        all_players = team_obj.lineup + team_obj.game_pitchers + team_obj.bullpen
        
        for obj_player in all_players:
            if not obj_player: continue
            
            pid = str(obj_player.player_id)
            
            if pid in self.player_stats:
                s = self.player_stats[pid]
                b_stats = obj_player.stats["batting"]
                p_stats = obj_player.stats["pitching"]
                
                if b_stats["PA"] > 0 or p_stats["Outs"] > 0:
                    s["G"] += 1
                
                s["AB"] += b_stats["AB"]
                s["H"] += b_stats["H"]
                s["HR"] += b_stats["HR"]
                s["RBI"] += b_stats["RBI"]
                s["R"] += b_stats["R"]
                
                s["IP"] += p_stats["Outs"] / 3.0
                s["ER"] += p_stats["ER"]
                s["K"] += p_stats["K"]
                s["BB"] += p_stats["BB"]
            
            # Write back the drained stamina to the flat dictionary
            for flat_player in self.rosters[team_name]:
                if str(flat_player["ID"]) == pid:
                    max_stam = flat_player.get("Max Stam", 100)
                    flat_player["Cur Stam"] = getattr(obj_player, 'current_stamina', max_stam)
                    break

    def recover_daily_stamina(self):
        """Adds natural rest recovery to all players across the league at the end of a day."""
        for roster in self.rosters.values():
            for player in roster:
                player["Cur Stam"] = min(player["Max Stam"], player["Cur Stam"] + 20)

    def export_box_score_to_sheet(self, game):
        """Builds a 2D spreadsheet grid of the box score and appends it to the BoxScores tab."""
        print(f"Exporting Box Score to Sheets for {game.away.name} vs {game.home.name}...")
        ws = SHEET.worksheet("BoxScores")
        
        left_rows = []
        
        # --- 1. LINE SCORE ---
        innings_count = max(9, game.inning - 1)
        header_row = ["Team"] + [str(i+1) for i in range(innings_count)] + ["R", "H", "E"]
        left_rows.append(header_row)
        
        for team in [game.away, game.home]:
            row = [team.name]
            for score in team.linescore:
                row.append("X" if score is None else score)
            
            while len(row) < innings_count + 1:
                row.append("")
                
            row.append(team.stats['batting']['R'])
            row.append(team.stats['batting']['H'])
            row.append(team.stats['defense']['E'])
            left_rows.append(row)
            
        left_rows.append([]) 
        
        # --- 2. BATTING & PITCHING STATS ---
        for team in [game.away, game.home]:
            # Batters
            left_rows.append([f"{team.name.upper()} BATTERS", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "K"])
            for p in team.lineup:
                s = p.stats['batting']
                left_rows.append([p.name, s['AB'], s['R'], s['H'], s['2B'], s['3B'], s['HR'], s['RBI'], s['BB'], s['K']])
            
            s = team.stats['batting']
            left_rows.append(["TOTALS", s['AB'], s['R'], s['H'], s['2B'], s['3B'], s['HR'], s['RBI'], s['BB'], s['K']])
            left_rows.append([])
            
            # Pitchers
            left_rows.append([f"{team.name.upper()} PITCHERS", "IP", "H", "R", "ER", "BB", "K", "PC"])
            for p in team.game_pitchers:
                p_outs = p.stats['pitching']['Outs']
                if p_outs > 0 or hasattr(p, 'game_decision'):
                    p_ip = f"{p_outs // 3}.{p_outs % 3}" if p_outs > 0 else "0.0"
                    ps = p.stats['pitching']
                    
                    role_tag = p.attributes.get('role', 'P')
                    decision_tag = f" ({p.game_decision})" if hasattr(p, 'game_decision') else ""
                    max_stam = p.attributes.get('pitching', {}).get('stamina', 100)
                    cur_stam = getattr(p, 'current_stamina', max_stam)
                    
                    p_name_formatted = f"{p.name} ({role_tag}){decision_tag} ({cur_stam}/{max_stam})"
                    left_rows.append([p_name_formatted, p_ip, ps['H'], ps['R'], ps['ER'], ps['BB'], ps['K'], ps['Pitches']])
            left_rows.append([])

        # --- 3. SCORING PLAYS ---
        right_rows = [["SCORING PLAYS", "INNING", "EVENT", "DESCRIPTION"]]
        if not game.scoring_plays:
            right_rows.append(["", "", "", "No scoring plays."])
        else:
            for play in game.scoring_plays:
                inning_str = f"{play['half'][:3]} {play['inning']}"
                right_rows.append(["", inning_str, play['event'], play['description']])
                right_rows.append([]) 

        # --- 4. MERGE SIDES INTO A PERFECT GRID ---
        final_grid = []
        max_rows = max(len(left_rows), len(right_rows))
        
        max_left_width = max(len(row) for row in left_rows) if left_rows else 10
        gap_column = max(max_left_width + 2, 13) 
        
        for i in range(max_rows):
            l_row = left_rows[i] if i < len(left_rows) else []
            while len(l_row) < gap_column: l_row.append("")
            r_row = right_rows[i] if i < len(right_rows) else []
            final_grid.append(l_row + r_row)
            
        final_grid.append(["="*15, "="*5, "="*5, "="*5, "="*5, "="*5, "="*5])
        final_grid.append([])
        
        ws.append_rows(final_grid)

    def export_all(self):
        """Flattens the memory state and overwrites the Google Sheets with updated stamina levels."""
        print("Exporting updated player data and stamina back to Google Sheets...")
        
        for team_name, roster in self.rosters.items():
            ws = SHEET.worksheet(team_name)
            
            if not roster: 
                continue
                
            # Extract the headers dynamically from the first player in the dictionary
            headers = list(roster[0].keys())
            grid = [headers]
            
            # Map every player back into a list format matching the headers
            for player in roster:
                row = [player.get(h, "") for h in headers]
                grid.append(row)
                
            ws.clear()
            ws.append_rows(grid)
            print(f"  > Updated {team_name} fatigue levels.")
            
        print("Master Roster Export complete!")

# TEST THE ENGINE: PLAY-BY-PLAY BROADCAST
def print_box_score(game):
    left_lines = []
    
    left_lines.append("="*75)
    left_lines.append(" "*25 + "FINAL BOX SCORE")
    left_lines.append("="*75)
    
    # 1. THE LINE SCORE
    innings_count = max(9, game.inning - 1)
    header = "Team".ljust(18) + "".join([str(i+1).rjust(3) for i in range(innings_count)]) + " |  R   H   E"
    left_lines.append(header)
    left_lines.append("-" * len(header))
    
    for team in [game.away, game.home]:
        name = team.name[:16].ljust(18)
        linescore = ""
        for score in team.linescore:
            linescore += "  X" if score is None else str(score).rjust(3)
        while len(linescore) < innings_count * 3:
            linescore += "   "
            
        runs = str(team.stats['batting']['R']).rjust(2)
        hits = str(team.stats['batting']['H']).rjust(2)
        errs = str(team.stats['defense']['E']).rjust(2) 
        
        left_lines.append(f"{name}{linescore} | {runs}  {hits}  {errs}")
        
    left_lines.append("="*75)
    
    # Helper function to generate Team Batting and Pitching blocks
    def build_team_stats(team):
        left_lines.append(f"{team.name.upper()} BATTERS:")
        left_lines.append(f"    {'BATTER':<20} | AB  R   H  2B 3B HR RBI BB  K")
        left_lines.append("    " + "-"*52)
        for p in team.lineup:
            s = p.stats['batting']
            left_lines.append(f"    {p.name:<20} | {s['AB']:<3} {s['R']:<3} {s['H']:<3} {s['2B']:<2} {s['3B']:<2} {s['HR']:<2} {s['RBI']:<3} {s['BB']:<3} {s['K']:<3}")
        
        s = team.stats['batting']
        left_lines.append("    " + "-"*52)
        left_lines.append(f"    {'TOTALS':<20} | {s['AB']:<3} {s['R']:<3} {s['H']:<3} {s['2B']:<2} {s['3B']:<2} {s['HR']:<2} {s['RBI']:<3} {s['BB']:<3} {s['K']:<3}")
        left_lines.append("-" * 75)
        
        left_lines.append(f"{team.name.upper()} PITCHERS:")
        left_lines.append(f"    {'PITCHER':<32} | IP   H  R  ER BB K  PC")
        left_lines.append("    " + "-"*55)
        
        for p in team.game_pitchers:
            p_outs = p.stats['pitching']['Outs']
            
            if p_outs > 0 or hasattr(p, 'game_decision'):
                p_ip = f"{p_outs // 3}.{p_outs % 3}" if p_outs > 0 else "0.0"
                ps = p.stats['pitching']
                
                role_tag = p.attributes.get('role', 'P')
                decision_tag = f" ({p.game_decision})" if hasattr(p, 'game_decision') else ""
                max_stam = p.attributes.get('pitching', {}).get('stamina', 100)
                cur_stam = getattr(p, 'current_stamina', max_stam)
                
                p_name_stam = f"{p.name} ({role_tag}){decision_tag} ({cur_stam}/{max_stam})"
                
                left_lines.append(f"    {p_name_stam:<32} | {p_ip:<4} {ps['H']:<2} {ps['R']:<2} {ps['ER']:<2} {ps['BB']:<2} {ps['K']:<2} {ps['Pitches']:<3}")
        left_lines.append("=" * 75)

    build_team_stats(game.away)
    build_team_stats(game.home)

    # RIGHT COLUMN: SCORING PLAYS
    right_lines = []
    right_lines.append("SCORING PLAYS & EVENTS")
    right_lines.append("="*50)
    
    if not game.scoring_plays:
        right_lines.append("No scoring plays.")
    else:
        for play in game.scoring_plays:
            inning_str = f"[{play['half'][:3]} {play['inning']}]"
            event_str = f"({play['event']})"
            right_lines.append(f"{inning_str} {event_str} - {play['description']}")
            right_lines.append("")

    # COMBINE AND PRINT SIDE-BY-SIDE
    max_lines = max(len(left_lines), len(right_lines))
    print("\n")
    for i in range(max_lines):
        left = left_lines[i] if i < len(left_lines) else ""
        right = right_lines[i] if i < len(right_lines) else ""
        print(f"{left:<75} |  {right}")

def main():
    engine = SimulationEngine()
    engine.load_state()
    
    print(f"Starting simulation from Day {engine.current_day + 1}")
    
    for i in range(1):
        day_index = engine.current_day + i
        engine.recover_daily_stamina()
        matchups = engine.get_schedule_for_day(day_index)
        
        for away, home in matchups:
            engine.simulate_game(away, home)
            
    engine.export_all()
    print("Simulation block complete! Check your Google Sheet for the post-game exhausted states.")

if __name__ == "__main__":
    main()