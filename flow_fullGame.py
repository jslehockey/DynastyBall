# ==========================================
# flow_full_game.py
# ==========================================
# Manages the macro 9-inning game flow, live score evaluation, 
# pitching decision attribution, and box score payload generation.
# ==========================================
from flow_halfInning import HalfInning

class FullGame:
    def __init__(self, away_team, home_team, league_env, weather=None, career_stats=None, hr_record_target_away=0, hr_record_target_home=0, attendance_data=0, modifiers=None):
        # --- GAME TEAMS & ENVIRONMENT ---
        self.away = away_team
        self.home = home_team
        self.env = league_env
        self.weather = weather if weather else {"temp": 70, "wind_speed": 0, "wind_direction": "Calm", "precipitation": "None"}
        
        # --- GAME STATE ---
        self.inning = 1
        self.game_events = []
        self.current_lead = "Tie"
        
        # --- PITCHING DECISION TRACKERS ---
        self.away_por = self.away.pitcher 
        self.home_por = self.home.pitcher 
        self.away_starter = self.away.pitcher
        self.home_starter = self.home.pitcher

        # --- PRE-GAME STAT LOAD (Phase 3 Integration) ---
        self.career_stats = career_stats if career_stats else {}
        for team in [self.away, self.home]:
            for player in team.lineup + [team.pitcher] + team.bullpen:
                pid = str(player.player_id)
                player.career_context = self.career_stats.get(pid, {
                    # Added HBP, SF, and GIDP to the baseline tracking
                    "H": 0, "HR": 0, "RBI": 0, "K": 0, "W": 0, "SV": 0, "IP": 0.0,
                    "HBP": 0, "SF": 0, "GIDP": 0 
                }).copy()

    # ==========================================
    # LEAD TRACKING & PITCHING DECISIONS
    # ==========================================
    def evaluate_run_scored(self, half_inning_obj):
        """Monitors live score changes to evaluate blown saves and pitchers of record."""
        away_live = self.away.stats["batting"]["R"] + (half_inning_obj.runs if half_inning_obj.is_top else 0)
        home_live = self.home.stats["batting"]["R"] + (half_inning_obj.runs if not half_inning_obj.is_top else 0)
        
        new_lead = "Tie"
        if away_live > home_live: new_lead = "Away"
        elif home_live > away_live: new_lead = "Home"

        if new_lead != self.current_lead:
            if self.current_lead != "Tie":
                pitcher_who_blew_it = self.home.pitcher if self.current_lead == "Home" else self.away.pitcher
                if getattr(pitcher_who_blew_it, 'is_in_save_situation', False):
                    pitcher_who_blew_it.stats["pitching"]["BS"] += 1
                    pitcher_who_blew_it.is_in_save_situation = False 
                    print(f"  [BLOWN SAVE] {pitcher_who_blew_it.name} surrenders the lead!")

            if new_lead == "Away":
                self.away_por = self.away.pitcher
                self.home_por = self.home.pitcher
            elif new_lead == "Home":
                self.home_por = self.home.pitcher
                self.away_por = self.away.pitcher
                
            self.current_lead = new_lead

    def award_pitching_decisions(self):
        """Awards Wins, Losses, Holds, and Saves post-game."""
        if self.away.stats["batting"]["R"] > self.home.stats["batting"]["R"]:
            winner_team, loser_team = self.away, self.home
            winning_pitcher, losing_pitcher = self.away_por, self.home_por
            winner_starter = self.away_starter 
        else:
            winner_team, loser_team = self.home, self.away
            winning_pitcher, losing_pitcher = self.home_por, self.away_por
            winner_starter = self.home_starter

        if winning_pitcher == winner_starter and winning_pitcher.stats["pitching"]["Outs"] < 15:
            relievers = [p for p in winner_team.used_pitchers + [winner_team.pitcher] if p != winner_starter]
            if relievers: winning_pitcher = max(relievers, key=lambda p: p.stats["pitching"]["Outs"])

        winning_pitcher.stats["pitching"]["W"] += 1
        losing_pitcher.stats["pitching"]["L"] += 1
        
        winning_pitcher.game_decision = "W"
        losing_pitcher.game_decision = "L"

        winning_relievers = [p for p in winner_team.used_pitchers + [winner_team.pitcher] 
                             if p != winner_starter and p != winning_pitcher]
        
        for p in winning_relievers:
            if getattr(p, 'is_in_save_situation', False):
                if p == winner_team.pitcher: 
                    p.stats["pitching"]["SV"] += 1
                    p.game_decision = "SV" 
                else: 
                    p.stats["pitching"]["HLD"] += 1
                    p.game_decision = "H"  

    # ==========================================
    # MACRO GAME ENGINE LOOP
    # ==========================================
    def play_game(self):
        """Runs the 9-inning structure, instantiating HalfInnings."""
        print(f"\n========== PLAY BALL! ==========")
        print(f"{self.away.name} vs. {self.home.name}")
        print(f"================================\n")
        
        while self.inning <= 9 or self.away.stats["batting"]["R"] == self.home.stats["batting"]["R"]:
            
            top_half = HalfInning(self.away, self.home, self.env, self.inning, True, 
                                  self.away.stats["batting"]["R"], self.home.stats["batting"]["R"], 
                                  self.game_events, self, weather=self.weather) 
            top_half.play()
            
            if self.inning >= 9 and self.home.stats["batting"]["R"] > self.away.stats["batting"]["R"]:
                self.home.linescore.append(None)
                break
                
            bottom_half = HalfInning(self.home, self.away, self.env, self.inning, False, 
                                     self.away.stats["batting"]["R"], self.home.stats["batting"]["R"], 
                                     self.game_events, self, weather=self.weather) 
            bottom_half.play()
            
            self.inning += 1
            
        print(f"\n========== BALLGAME ==========")
        print(f"FINAL SCORE: {self.away.name} {self.away.stats['batting']['R']} - {self.home.name} {self.home.stats['batting']['R']}")
        
        self.award_pitching_decisions()
        print(f"==============================\n")
    
    # ==========================================
    # POST-GAME REPORTING
    # ==========================================
    def check_milestones(self):
        """Evaluates rare full-game milestones like Cycles and No-Hitters."""
        milestones = []
        
        for team, opponent in [(self.away, self.home), (self.home, self.away)]:
            # --- PITCHING POST-GAME MILESTONES ---
            unique_pitchers = list(set(team.game_pitchers))
            is_cg = False
            
            if len(unique_pitchers) == 1:
                sp = unique_pitchers[0]
                sp.stats["pitching"]["CG"] = sp.stats["pitching"].get("CG", 0)
                sp.stats["pitching"]["SHO"] = sp.stats["pitching"].get("SHO", 0)

                if sp.stats["pitching"]["Outs"] >= 24:
                    is_cg = True
                    sp.stats["pitching"]["CG"] += 1
                    if opponent.stats["batting"]["R"] == 0:
                        sp.stats["pitching"]["SHO"] += 1
                        if opponent.stats["batting"]["H"] == 0:
                            if opponent.stats["batting"]["BB"] == 0 and opponent.stats["batting"]["HBP"] == 0 and team.stats["defense"]["E"] == 0:
                                milestones.append(f"PERFECT GAME: {sp.name} pitches a Perfect Game!")
                            else:
                                milestones.append(f"NO-HITTER: {sp.name} throws a No-Hitter!")
                        else:
                            milestones.append(f"COMPLETE GAME SHUTOUT: {sp.name} goes the distance and blanks the opponent!")
                    else:
                        milestones.append(f"COMPLETE GAME: {sp.name} pitches a complete game victory.")
            
            if not is_cg:
                if opponent.stats["batting"]["H"] == 0:
                    if opponent.stats["batting"]["BB"] == 0 and opponent.stats["batting"]["HBP"] == 0 and team.stats["defense"]["E"] == 0:
                        milestones.append(f"COMBINED PERFECT GAME: {team.name} pitching staff!")
                    else:
                        milestones.append(f"COMBINED NO-HITTER: {team.name} pitching staff!")
                elif opponent.stats["batting"]["R"] == 0:
                    milestones.append(f"SHUTOUT: {team.name} pitching staff blanks the opponent.")

            # --- BATTING POST-GAME MILESTONES ---
            for player in team.lineup:
                stats = player.stats["batting"]
                
                if stats["1B"] >= 1 and stats["2B"] >= 1 and stats["3B"] >= 1 and stats["HR"] >= 1:
                    milestones.append(f"CYCLE: {player.name} hits for the cycle!")
                if stats["HR"] >= 4: milestones.append(f"4-HR GAME: {player.name} hits {stats['HR']} home runs!")
                if stats["RBI"] >= 8: milestones.append(f"8-RBI GAME: {player.name} drives in {stats['RBI']} runs!")
                if stats["H"] >= 5: milestones.append(f"5-HIT GAME: {player.name} collects {stats['H']} hits!")

        return milestones
    
    def generate_sheets_payload(self):
        """Builds a 2D array containing the Box Score and Game Log for Google Sheets."""
        payload = [
            ["DiamondBucs Simulation Engine"],
            ["Team", "1", "2", "3", "4", "5", "6", "7", "8", "9", "R", "H", "E"]
        ]
        
        def format_linescore(linescore, innings):
            padded = linescore.copy()
            while len(padded) < innings:
                padded.append("")
            return padded

        innings_played = max(9, self.inning - 1)
        away_line = format_linescore(self.away.linescore, innings_played)
        home_line = format_linescore(self.home.linescore, innings_played)

        if len(home_line) < len(away_line):
            home_line.append("X")

        payload.append([self.away.name] + away_line + [
            self.away.stats["batting"]["R"], 
            self.away.stats["batting"]["H"], 
            self.away.stats["defense"]["E"]
        ])
        
        payload.append([self.home.name] + home_line + [
            self.home.stats["batting"]["R"], 
            self.home.stats["batting"]["H"], 
            self.home.stats["defense"]["E"]
        ])
        
        post_game_milestones = self.check_milestones()
        for m in post_game_milestones:
            self.game_events.append(["Final", "End", "League", "Game Milestone", "Team/Staff", m])

        payload.append([])
        payload.append(["--- NOTABLE GAME EVENTS ---"])
        payload.append(["Inning", "Half", "Team", "Event Type", "Player", "Play Description"])
        
        if not self.game_events:
            payload.append(["", "", "", "No notable events recorded.", "", ""])
        else:
            for event in self.game_events:
                payload.append(event)
                
        return payload