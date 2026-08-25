# ==========================================
# flow_half_inning.py
# ==========================================
# Manages the micro-level game state for a single half-inning,
# including baserunning, live at-bat loops, and bullpen calls.
# ==========================================
import random
from engine import AtBatSimulator

class HalfInning:
    def __init__(self, batting_team, fielding_team, league_env, inning_num, is_top, away_score, home_score, game_events, game_instance=None, weather=None, hr_record_target_away=0, hr_record_target_home=0):
        # --- TEAMS & ENVIRONMENT ---
        self.batting_team = batting_team
        self.fielding_team = fielding_team
        self.env = league_env
        self.weather = weather if weather else {"temp": 70, "wind_speed": 0, "wind_direction": "Calm", "precipitation": "None"}
        
        # --- GAME STATE CONTEXT ---
        self.inning_num = inning_num
        self.is_top = is_top
        self.away_score = away_score
        self.home_score = home_score
        self.game_events = game_events
        self.game_instance = game_instance 
        
        # --- INNING TRACKERS ---
        self.pitcher = fielding_team.pitcher
        self.defense = fielding_team.defense
        self.outs = 0
        self.runs = 0
        self.bases = {1: None, 2: None, 3: None}
        self.errors_in_inning = 0
        
        # --- MILESTONE TARGETS ---
        self.hr_record_target_away = hr_record_target_away
        self.hr_record_target_home = hr_record_target_home

    # ==========================================
    # MILESTONE & LOGGING SYSTEM
    # ==========================================
    def check_in_game_milestone(self, player, stat_type, season_stat_value):
        if not hasattr(player, 'career_context'): return None
        
        career_total = player.career_context.get(stat_type, 0) + season_stat_value
        alerts = []
        
        # The Expanded Milestone Dictionary
        milestone_thresholds = {
            "HR": [1, 10, 50, 75, 100, 150, 200, 250, 300, 350, 400, 450, 500],
            "H":  [1, 100, 250, 400, 500, 750, 1000, 1500, 2000],
            "K":  [1, 100, 500, 1000, 2000, 3000, 4000],
            "RBI": [1, 100, 500, 1000, 1500, 2000],
            "SB":  [1, 50, 100, 250, 500],
            "W":   [1, 10, 50, 100, 200, 300],
            "SV":  [1, 50, 75, 100, 150, 200, 250, 300, 350, 400]
        }
        
        if stat_type in milestone_thresholds and career_total in milestone_thresholds[stat_type]:
            if career_total == 1:
                alerts.append(f"FIRST CAREER {stat_type}! {player.name} gets on the board!")
            else:
                alerts.append(f"*** CAREER MILESTONE! {player.name} reaches {career_total} career {stat_type}s! ***")

        if self.is_top:
            target = getattr(self.game_instance, 'hr_record_target_away', 0)
        else:
            target = getattr(self.game_instance, 'hr_record_target_home', 0)
        
        if stat_type == "HR":
            if target > 0 and season_stat_value == target:
                alerts.append(f"HISTORY! {player.name} just TIED the single-season franchise Home Run record ({int(target)})!")
            elif target > 0 and season_stat_value == target + 1:
                alerts.append(f"NEW RECORD! {player.name} breaks the franchise single-season Home Run record!")
                
        return alerts if alerts else None
    
    def register_hit_milestones(self, batter, p_bat):
        """Helper to handle both Career Hits and active Hit Streaks."""
        # 1. Check Career Milestones
        milestone = self.check_in_game_milestone(batter, "H", p_bat["H"])
        if milestone:
            for m in milestone:
                print(f"  {m}")
                self.log_event("Batting Milestone", batter.name, m)
                
        # 2. Check Hit Streaks (Only triggers on their FIRST hit of the game)
        if p_bat["H"] == 1: 
            entering_streak = batter.attributes.get("current_hit_streak", 0)
            new_streak = entering_streak + 1
            
            if new_streak in [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60] or (new_streak > 60 and new_streak % 5 == 0):
                msg = f"Hit Streak extended to {new_streak} games!"
                if new_streak == 50:
                    msg = "What a milestone, 50 game hit-streak!"
                
                print(f"  *** {msg} ***")
                self.log_event("Batting Milestone", batter.name, msg)

    def log_event(self, event_type, player_name, description, pitch_log=""):
        half_str = "Top" if self.is_top else "Bottom"
        
        if event_type in ["Pitching Milestone", "Defensive Milestone"]:
            team_name = self.fielding_team.name
        else:
            team_name = self.batting_team.name
            
        # Capture the live score
        away_live = self.away_score + (self.runs if self.is_top else 0)
        home_live = self.home_score + (self.runs if not self.is_top else 0)

        # Capture base runners by name so the UI knows who to draw on the diamond
        r1 = self.bases[1].name if self.bases[1] else None
        r2 = self.bases[2].name if self.bases[2] else None
        r3 = self.bases[3].name if self.bases[3] else None
            
        self.game_events.append({
            "inning": self.inning_num,
            "half": half_str,
            "team": team_name,
            "type": event_type,
            "player": player_name,
            "desc": description,
            "pitch_log": pitch_log,
            "outs": self.outs,
            "away_score": away_live,
            "home_score": home_live,
            "r1": r1, "r2": r2, "r3": r3
        })

    # ==========================================
    # CORE ENGINE LOOP
    # ==========================================
    def play(self):
        """The main loop that runs until 3 outs are recorded or a walk-off occurs."""
        frame = "Top" if self.is_top else "Bottom"
        print(f"\n--- {frame} {self.inning_num} | {self.batting_team.name} Batting ---")
        
        t_bat = self.batting_team.stats["batting"]
        t_pit = self.fielding_team.stats["pitching"]
        t_fld = self.fielding_team.stats["defense"]
        
        last_ab_was_hr = False
        
        while self.outs < 3:
            # --- 1. PITCHING CHANGE LOGIC ---
            max_stam = self.pitcher.attributes.get('pitching', {}).get('stamina', 100)
            curr_stam = getattr(self.pitcher, 'current_stamina', max_stam)
            stam_pct = (curr_stam / max_stam) * 100
            
            threshold = self.fielding_team.hook_threshold
            uses_adrenaline = self.fielding_team.adrenaline_trigger
            
            runner_in_scoring_pos = (self.bases[2] is not None) or (self.bases[3] is not None)
            danger_zone = runner_in_scoring_pos or last_ab_was_hr
            
            is_exhausted = (threshold != -1 and stam_pct <= threshold) or (stam_pct <= 0.0)

            if is_exhausted:
                if uses_adrenaline and not danger_zone:
                    if stam_pct <= 0.0 and self.outs == 0: 
                        print(f"  [ADRENALINE] {self.pitcher.name}'s tank is empty, but he's rolling. Manager lets him ride!")
                else:
                    if self.inning_num <= 7: role = "Middle Reliever"
                    elif self.inning_num == 8: role = "Setup Man"
                    else: role = "Closer"
                    
                    if uses_adrenaline and danger_zone:
                        trigger_reason = "a runner reached scoring position" if runner_in_scoring_pos else "giving up a home run"
                        print(f"  [DANGER ZONE] After {trigger_reason}, the manager has seen enough.")

                    self.call_to_bullpen(failsafe_role=role)
                    last_ab_was_hr = False 

            # --- 2. AT-BAT INITIALIZATION ---
            batter = self.batting_team.get_next_batter()
            print(f"\nUp to bat: {batter.name} | Outs: {self.outs} | Bases: {self.get_bases_string()}")

            if getattr(batter, 'is_rookie', False) and batter.stats["batting"]["PA"] == 0:
                # Check if this is the inaugural 2026 season by looking at the league environment or game instance
                is_inaugural_year = False
                if self.game_instance and hasattr(self.game_instance, 'league_env'):
                    # If your league_env tracks the year, use it. Otherwise, default to True for now.
                    current_year = getattr(self.game_instance.league_env, 'current_year', 2026)
                    is_inaugural_year = (current_year == 2026)
                
                # Only announce debuts if we are past the inaugural season
                if not is_inaugural_year:
                    print(f"DEBUT ALERT: {batter.name} steps into the box for his first career at-bat!")
                    self.log_event("Debut", batter.name, "Welcome to the show! First career at-bat.")
            
            runs_at_start_of_ab = self.runs 
            p_bat = batter.stats["batting"]
            p_pit = self.pitcher.stats["pitching"]
            
            # --- 3. ATBAT RESOLUTION ---
            sim = AtBatSimulator(batter, self.pitcher, league_env=self.env, half_inning=self, is_home_batting=not self.is_top, weather=self.weather)
            outcome = sim.simulate_at_bat(defense=self.defense)
            event = outcome.get("event")

            # NEW: Variable to hold the play summary for the UI Database
            play_description = ""

            # Pitch Count Tracker
            if "pitches" in outcome: ab_pitches = outcome["pitches"]
            else:
                if event == "Strikeout": ab_pitches = random.randint(3, 7)
                elif event in ["Walk", "Hit By Pitch"]: ab_pitches = random.randint(4, 8)
                else: ab_pitches = random.randint(1, 6)
                
            t_pit["Pitches"] += ab_pitches
            p_pit["Pitches"] += ab_pitches

            last_ab_was_hr = (outcome.get("target") == "HR")
            
            if "log" in outcome:
                print("  [AT-BAT BROADCAST]")
                for log_entry in outcome["log"]:
                    print(f"    {log_entry}")
            
            # --- 4. ENGINE OUTCOME PARSER ---
            if event == "Inning Ending Steal":
                # NEW: Catch the steal in the play-by-play log
                self.log_event("Caught Stealing", batter.name, "Runner caught stealing to end the inning.")
                self.batting_team.batter_index -= 1
                if self.batting_team.batter_index < 0:
                    self.batting_team.batter_index = len(self.batting_team.lineup) - 1
                break 

            t_bat["PA"] += 1
            p_bat["PA"] += 1
            
            if event == "Strikeout":
                t_bat["AB"] += 1; p_bat["AB"] += 1
                t_bat["K"] += 1; p_bat["K"] += 1
                t_pit["K"] += 1; p_pit["K"] += 1
                play_description = "Strikeout." # <--- SET VAR
                print(f"  Result: Strikeout.")

            elif event in ["Walk", "Hit By Pitch"]:
                key = "BB" if event == "Walk" else "HBP"
                t_bat[key] += 1; p_bat[key] += 1
                t_pit[key] += 1; p_pit[key] += 1
                play_description = f"{event}." # <--- SET VAR
                print(f"  Result: {event}.")
                self.advance_all_forced(batter)
                
            elif event == "Ball in Play":
                t_bat["AB"] += 1; p_bat["AB"] += 1
                play_description = outcome.get("description", "Ball in play.") # <--- SET VAR
                print(f"  Result: {play_description}")
                
                target = outcome.get("target")
                
                if target == "Infield Grounder":
                    self.process_infield_grounder(batter, outcome)
                    if outcome.get("error"):
                        t_fld["E"] += 1
                        self.errors_in_inning += 1
                    elif outcome["safe"]:
                        t_bat["1B"] += 1; p_bat["1B"] += 1
                        t_bat["H"] += 1; p_bat["H"] += 1
                        t_pit["H"] += 1; p_pit["H"] += 1
                        
                        self.register_hit_milestones(batter, p_bat)
                        milestone = self.check_in_game_milestone(batter, "H", p_bat["H"])
                        if milestone:
                            for m in milestone:
                                print(f"  {m}")
                                self.log_event("Batting Milestone", batter.name, m)
                        
                else:
                    if not outcome["safe"]:
                        self.record_out()
                        if outcome.get("fielder_state") == "caught_in_air":
                            catcher_pos = outcome["hit_data"]["target_position"]
                            self.record_fielding_stat(catcher_pos, "PO")
                        
                        # TAG-UP LOGIC
                        if self.outs < 3 and outcome.get("fielder_state") == "caught_in_air":
                            hit_data = outcome.get("hit_data", {})
                            if hit_data.get("trajectory") == "Fly Ball":
                                distance = hit_data["distance"]
                                location = hit_data["location"]
                                f_arm_str = outcome.get("fielder_arm_str", 75)

                                if self.bases[3] and distance >= 240:
                                    runner = self.bases[3]
                                    r_speed = runner.attributes.get('baserunning', {}).get('sprint_speed', 75)
                                    print(f"  > {runner.name} tags up from third!")
                                    
                                    tag = sim.resolve_tag_up(r_speed, f_arm_str, distance, "Home", location)
                                    if tag["safe"]:
                                        print(f"  > {tag['reason']}")
                                        self.score_run(runner)
                                        self.bases[3] = None
                                        p_bat["RBI"] += 1
                                        t_bat["AB"] -= 1; p_bat["AB"] -= 1
                                        t_bat["SF"] = t_bat.get("SF", 0) + 1
                                        p_bat["SF"] = p_bat.get("SF", 0) + 1
                                    else:
                                        print(f"  > {tag['reason']} (Double Play!)" if self.outs == 2 else f"  > {tag['reason']}")
                                        self.record_out()
                                        self.bases[3] = None

                                elif self.bases[2] and not self.bases[3] and self.outs < 3:
                                    valid_locs = ["Dead Center", "Right Center Gap", "Dead Right Field", "Right Field Line"]
                                    if location in valid_locs and distance >= 280:
                                        runner = self.bases[2]
                                        r_speed = runner.attributes.get('baserunning', {}).get('sprint_speed', 75)
                                        print(f"  > {runner.name} tags up and heads for third!")
                                        
                                        tag = sim.resolve_tag_up(r_speed, f_arm_str, distance, "3B", location)
                                        if tag["safe"]:
                                            print(f"  > {tag['reason']}")
                                            self.bases[3] = runner
                                            self.bases[2] = None
                                        else:
                                            print(f"  > {tag['reason']}")
                                            self.record_out()
                                            self.bases[2] = None

                    else:
                        if outcome["target"] == "HR":
                            t_bat["HR"] += 1; p_bat["HR"] += 1
                            t_bat["H"] += 1; p_bat["H"] += 1
                            t_pit["H"] += 1; p_pit["H"] += 1
                            t_pit["HR"] += 1; p_pit["HR"] += 1
                            
                            milestone_h = self.check_in_game_milestone(batter, "H", p_bat["H"])
                            if milestone_h:
                                for m in milestone_h:
                                    print(f"  {m}")
                                    self.log_event("Batting Milestone", batter.name, m)
                                    
                            milestone_hr = self.check_in_game_milestone(batter, "HR", p_bat["HR"])
                            if milestone_hr:
                                for m in milestone_hr:
                                    print(f"  {m}")
                                    self.log_event("Batting Milestone", batter.name, m)
                            
                            self.clear_bases_for_home_run(batter)
                            
                        elif outcome.get("error"):
                            error_pos = outcome["hit_data"]["target_position"]
                            self.record_fielding_stat(error_pos, "E") 
                            self.errors_in_inning += 1
                            self.process_hit_advancement(batter, "1B")
                            
                        else:
                            target = outcome["target"]
                            hit_type = target if target in ["1B", "2B", "3B"] else "1B" 
                            t_bat[hit_type] += 1; p_bat[hit_type] += 1
                            t_bat["H"] += 1; p_bat["H"] += 1
                            t_pit["H"] += 1; p_pit["H"] += 1
                            
                            milestone = self.check_in_game_milestone(batter, "H", p_bat["H"])
                            if milestone:
                                for m in milestone:
                                    print(f"  {m}")
                                    self.log_event("Batting Milestone", batter.name, m)
                            
                            hit_location = outcome.get("location", "Center")
                            self.process_hit_advancement(batter, hit_type, hit_location)
            
            # --- 5. RBI & SCORING CALCULATIONS ---
            runs_scored_on_play = self.runs - runs_at_start_of_ab
            
            if runs_scored_on_play > 0:
                is_error = outcome.get("error", False) if event == "Ball in Play" else False
                rbi_awarded = 0 if is_error else runs_scored_on_play
                
                if rbi_awarded > 0:
                    p_bat["RBI"] += rbi_awarded
                    t_bat["RBI"] += rbi_awarded
                    
                    milestone_rbi = self.check_in_game_milestone(batter, "RBI", p_bat["RBI"])
                    if milestone_rbi:
                        for m in milestone_rbi:
                            print(f"  {m}")
                            self.log_event("Batting Milestone", batter.name, m)
                
                # Append scoring info to the main description instead of making a duplicate log
                play_description += f" ({runs_scored_on_play} Run{'s' if runs_scored_on_play > 1 else ''} Scored)"
            
            # ==========================================
            # NEW: THE MASTER AT-BAT LOGGER
            # ==========================================
            # This fires right before the Walk-Off check, ensuring self.bases and self.outs 
            # are perfectly updated for the UI diamond!
            if play_description:
                # Join the list of pitches with a pipe or HTML break
                pitch_sequence = "<br>".join(outcome.get("log", [])) if outcome else ""
                self.log_event("At-Bat", batter.name, play_description, pitch_sequence)

            # Walk-Off Check
            if not self.is_top and self.inning_num >= 9:
                if (self.home_score + self.runs) > self.away_score:
                    print(f"\n  *** WALK-OFF WINNER! {self.batting_team.name} WIN! ***")
                    self.is_walk_off = True  
                    break

        t_bat["R"] += self.runs
        self.batting_team.linescore.append(self.runs)
        print(f"\n--- {frame} {self.inning_num} OVER | Runs Scored: {self.runs} ---")

        # Half-Inning Stamina Deduction (Batters Only)
        for team in [self.batting_team, self.fielding_team]:
            for player in team.lineup:  
                max_stam = player.attributes.get('batting', {}).get('stamina', 100)
                curr_stam = getattr(player, 'current_stamina', max_stam)
                player.current_stamina = max(0, curr_stam - 1)

    # ==========================================
    # CORE BASERUNNING & TRACKING HELPERS
    # ==========================================
    def record_out(self):
        self.outs += 1
        self.fielding_team.stats["pitching"]["Outs"] += 1
        self.pitcher.stats["pitching"]["Outs"] += 1

    def score_run(self, player):
        self.runs += 1
        player.stats["batting"]["R"] += 1 
        self.pitcher.stats["pitching"]["R"] += 1 
        self.fielding_team.stats["pitching"]["R"] += 1
        
        if self.errors_in_inning == 0:
            self.pitcher.stats["pitching"]["ER"] += 1
            self.fielding_team.stats["pitching"]["ER"] += 1
        
        print(f"  *** {player.name} SCORES! ***")
        if self.game_instance:
            self.game_instance.evaluate_run_scored(self)

    def get_bases_string(self):
        b1 = "1B" if self.bases[1] else "--"
        b2 = "2B" if self.bases[2] else "--"
        b3 = "3B" if self.bases[3] else "--"
        return f"[{b1} | {b2} | {b3}]"

    def advance_all_forced(self, batter):
        if self.bases[1]:
            if self.bases[2]:
                if self.bases[3]:
                    self.score_run(self.bases[3]) 
                self.bases[3] = self.bases[2]
            self.bases[2] = self.bases[1]
        self.bases[1] = batter

    def clear_bases_for_home_run(self, batter):
        for base in [3, 2, 1]:
            if self.bases[base]:
                self.score_run(self.bases[base])
                self.bases[base] = None
        self.score_run(batter)

    def process_hit_advancement(self, batter, hit_type, hit_location="Center"):
        # Dynamic Outfielder Arm Extraction
        if hit_location in ["Left Field Line", "Dead Left Field", "Left Center Gap"]: pos = "LF"
        elif hit_location == "Dead Center": pos = "CF"
        else: pos = "RF"
        
        fielder = self.defense.get(pos)
        if fielder and hasattr(fielder, 'defense'):
            f_def = fielder.defense
            fielder_arm_str = f_def.get('arm_str', 75)
            fielder_arm_acc = f_def.get('arm_acc', 75)
        else:
            fielder_arm_str, fielder_arm_acc = 75, 75
        
        if hit_type == "3B":
            if self.bases[3]: self.score_run(self.bases[3])
            if self.bases[2]: self.score_run(self.bases[2])
            if self.bases[1]: self.score_run(self.bases[1])
            self.bases = {1: None, 2: None, 3: batter}
            
        elif hit_type == "2B":
            if self.bases[3]: self.score_run(self.bases[3])
            if self.bases[2]: self.score_run(self.bases[2])
            
            if self.bases[1]:
                runner = self.bases[1]
                runner_sprint = runner.attributes.get('baserunning', {}).get('sprint_speed', 75)
                
                print(f"  > {runner.name} rounds third, heading for home!")
                
                sim = AtBatSimulator(batter, self.pitcher, league_env=self.env, half_inning=self, is_home_batting=not self.is_top, weather=self.weather)
                outcome = sim.resolve_extra_base_attempt(runner_sprint, fielder_arm_str, fielder_arm_acc, hit_location, "Home")
                
                if outcome["safe"]:
                    print(f"  > {outcome['reason']}")
                    self.score_run(runner)
                    if outcome.get("error"):
                        self.fielding_team.stats["defense"]["E"] += 1
                        self.errors_in_inning += 1
                else:
                    print(f"  > {outcome['reason']}")
                    self.record_out()
                    
            self.bases[3] = None
            self.bases[2] = batter
            self.bases[1] = None
            
        elif hit_type == "1B":
            if self.bases[3]: self.score_run(self.bases[3])
            
            if self.bases[2]:
                runner = self.bases[2]
                runner_sprint = runner.attributes.get('baserunning', {}).get('sprint_speed', 75)
                
                print(f"  > {runner.name} challenges the arm, heading for home!")
                sim = AtBatSimulator(batter, self.pitcher, league_env=self.env, half_inning=self, is_home_batting=not self.is_top, weather=self.weather)
                outcome = sim.resolve_extra_base_attempt(runner_sprint, fielder_arm_str, fielder_arm_acc, hit_location, "Home")
                
                if outcome["safe"]:
                    print(f"  > {outcome['reason']}")
                    self.score_run(runner)
                    if outcome.get("error"):
                        self.fielding_team.stats["defense"]["E"] += 1
                        self.errors_in_inning += 1
                    self.bases[3] = None
                else:
                    print(f"  > {outcome['reason']}")
                    self.record_out()
                    self.bases[3] = None
            else:
                self.bases[3] = None

            if self.bases[1]:
                self.bases[2] = self.bases[1]
            else:
                self.bases[2] = None
                
            self.bases[1] = batter

    def process_infield_grounder(self, batter, outcome):
        target_base = outcome.get("target_base", 1)
        is_safe = outcome["safe"]
        is_dp = outcome.get("double_play", False)
        runner_held = outcome.get("runner_held", False)
        fielder_pos = outcome["hit_data"]["target_position"]
        
        if is_dp:
            self.record_out() 
            self.record_out()

            batter.stats["batting"]["GIDP"] = batter.stats["batting"].get("GIDP", 0) + 1
            self.batting_team.stats["batting"]["GIDP"] = self.batting_team.stats["batting"].get("GIDP", 0) + 1
            self.record_fielding_stat(fielder_pos, "A")
            self.record_fielding_stat(target_base, "PO")
            if target_base == 2:
                self.record_fielding_stat("2B", "A") 
                self.record_fielding_stat("1B", "PO")
            
            if target_base == 2: 
                if self.bases[3]: self.score_run(self.bases[3])
                if self.bases[2]: self.bases[3] = self.bases[2]
                self.bases[2] = None
                self.bases[1] = None 
                
            elif target_base == 3: 
                if self.bases[3]: self.score_run(self.bases[3])
                if self.bases[1]: self.bases[2] = self.bases[1] 
                self.bases[3] = None
                self.bases[1] = None
                
            elif target_base == 4: 
                if self.bases[2]: self.bases[3] = self.bases[2]
                if self.bases[1]: self.bases[2] = self.bases[1]
                self.bases[1] = None

        elif not is_safe:
            self.record_out()
            self.record_fielding_stat(fielder_pos, "A")
            self.record_fielding_stat(target_base, "PO")
            
            if target_base == 1:
                if runner_held: pass 
                else:
                    if self.bases[3]: self.score_run(self.bases[3])
                    if self.bases[2]: self.bases[3] = self.bases[2]
                    if self.bases[1]: self.bases[2] = self.bases[1]
                    self.bases[1] = None
            else:
                if target_base == 2:
                    if self.bases[3]: self.score_run(self.bases[3])
                    if self.bases[2]: self.bases[3] = self.bases[2]
                    self.bases[1] = batter 
                elif target_base == 3:
                    if self.bases[3]: self.score_run(self.bases[3])
                    self.bases[2] = self.bases[1]
                    self.bases[1] = batter
                elif target_base == 4:
                    self.bases[3] = self.bases[2]
                    self.bases[2] = self.bases[1]
                    self.bases[1] = batter
                    
        else:
            self.advance_all_forced(batter)

    def record_fielding_stat(self, position, stat_type):
        # 1. Handle integer bases (1, 2, 3, 4)
        if isinstance(position, int):
            base_map = {1: "1B", 2: "2B", 3: "3B", 4: "C"}
            position = base_map.get(position, "P")

        # 2. BULLETPROOF TRANSLATION MAP
        # Catches full words, hit locations, or slight variations and forces standard abbreviations
        safety_map = {
            "Catcher": "C", "First Base": "1B", "First Baseman": "1B",
            "Second Base": "2B", "Second Baseman": "2B",
            "Third Base": "3B", "Third Baseman": "3B",
            "Shortstop": "SS", "Left Field": "LF", "Left Fielder": "LF",
            "Center Field": "CF", "Center Fielder": "CF", "Center": "CF",
            "Right Field": "RF", "Right Fielder": "RF", "Pitcher": "P",
            "Dead Center": "CF", "Left Center Gap": "CF", "Right Center Gap": "CF",
            "Left Field Line": "LF", "Right Field Line": "RF"
        }
        
        # If the position matches a long word, convert it. Otherwise, keep it as is.
        clean_position = safety_map.get(position, position)

        # 3. Look up the fielder in the team's defense dictionary
        fielder = self.defense.get(clean_position)
        
        if fielder:
            fielder.stats["defense"][stat_type] += 1
            fielder.stats["defense"]["TC"] += 1
        else:
            # ---> ADD THIS PRINT STATEMENT <---
            print(f" 🚨 FIELDING ERROR: The engine tried to give a stat to '{clean_position}', but the team's valid positions are: {list(self.defense.keys())}")
            
        self.fielding_team.stats["defense"][stat_type] += 1
        self.fielding_team.stats["defense"]["TC"] += 1

    # ==========================================
    # BULLPEN MANAGEMENT
    # ==========================================
    def call_to_bullpen(self, failsafe_role=None):
        self.fielding_team.used_pitchers.append(self.pitcher)
        print(f"\n  *** PITCHING CHANGE ***")
        
        if failsafe_role:
            print(f"  [FAILSAFE TRIGGERED] {self.pitcher.name} is completely gassed.")
            print(f"  Manager makes the mandatory call to the bullpen for a {failsafe_role}.")
        else:
            print(f"  {self.pitcher.name} is visibly exhausted.")
            print(f"  The {self.fielding_team.name} manager makes the slow walk to the mound.")
        
        reliever = self._select_reliever()
        
        if reliever:
            score_diff = self.fielding_team.stats["batting"]["R"] - (self.batting_team.stats["batting"]["R"] + self.runs)
            tying_run_on_deck = (self.batting_team.stats["batting"]["R"] + self.runs) + 2 >= self.fielding_team.stats["batting"]["R"]
            
            if score_diff > 0 and (score_diff <= 3 or tying_run_on_deck):
                reliever.is_in_save_situation = True

            role_display = reliever.attributes.get('role', 'Reliever')
            id_slice = reliever.player_id[-4:] 
            
            print(f"  Now Pitching: {reliever.name} #{id_slice} ({role_display})\n")
            
            self.fielding_team.pitcher = reliever
            self.pitcher = reliever
            self.fielding_team.game_pitchers.append(reliever)
        else:
            print(f"  ...but the bullpen is completely empty! {self.pitcher.name} has to stay in!")
            self.fielding_team.hook_threshold = -1

    def _select_reliever(self):
        bullpen = self.fielding_team.bullpen
        if not bullpen: return None

        fielding_runs = self.fielding_team.stats["batting"]["R"]
        batting_runs = self.batting_team.stats["batting"]["R"]
        score_diff = fielding_runs - batting_runs
        inning = self.inning_num

        for p in bullpen:
            if hasattr(p, 'current_stamina'): p._temp_stam = p.current_stamina
            else:
                max_stam = p.attributes.get('pitching', {}).get('stamina', 100)
                p._temp_stam = p.attributes.get('pitching', {}).get('current_stamina', max_stam)

        starter_roles = ['SP1', 'SP2', 'SP3', 'SP4', 'SP5']
        available_relievers = [
            p for p in bullpen 
            if p.attributes.get('role', 'MR') not in starter_roles 
            and (p._temp_stam > 15 or inning > 9)
        ]

        available_relievers.sort(key=lambda x: x._temp_stam, reverse=True)

        if not available_relievers:
            print("  [BULLPEN DEPLETED] All relievers exhausted! Forcing best available arm.")
            desperate_roster = sorted(bullpen, key=lambda x: x._temp_stam, reverse=True)
            chosen = desperate_roster[0]
            bullpen.remove(chosen)
            return chosen

        if inning >= 9 and 1 <= score_diff <= 3: priority_list = ['CL', 'SU', 'LR', 'MR']
        elif inning in [7, 8] and 0 <= score_diff <= 3: priority_list = ['SU', 'LR', 'CL', 'MR']
        elif inning >= 6 and -2 <= score_diff <= 4: priority_list = ['LR', 'SU', 'MR', 'CL']
        else: priority_list = ['MR', 'LR', 'SU', 'CL']

        chosen_pitcher = None
        for target_role in priority_list:
            candidates = [p for p in available_relievers if p.attributes.get('role', 'MR') == target_role]
            if candidates:
                chosen_pitcher = candidates[0] 
                break
                
        if not chosen_pitcher: chosen_pitcher = available_relievers[0]

        bullpen.remove(chosen_pitcher)
        return chosen_pitcher