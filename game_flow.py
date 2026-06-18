import random
from engine import AtBatSimulator

class HalfInning:
    """
    Manages the game state for a single half-inning. 
    Tracks bases, outs, runs, and routes the At-Bat outcomes.
    """
    def __init__(self, batting_team, fielding_team, league_env, inning_num, is_top, away_score, home_score, scoring_plays, game_instance=None):
        self.batting_team = batting_team
        self.fielding_team = fielding_team
        self.env = league_env
        self.inning_num = inning_num
        self.is_top = is_top
        self.away_score = away_score
        self.home_score = home_score
        self.scoring_plays = scoring_plays 
        self.game_instance = game_instance 
        self.pitcher = fielding_team.pitcher
        self.defense = fielding_team.defense
        self.outs = 0
        self.runs = 0
        self.bases = {1: None, 2: None, 3: None}
        self.errors_in_inning = 0

    def play(self):
        """The main loop that runs until 3 outs are recorded or a walk-off occurs."""
        frame = "Top" if self.is_top else "Bottom"
        print(f"\n--- {frame} {self.inning_num} | {self.batting_team.name} Batting ---")
        
        t_bat = self.batting_team.stats["batting"]
        t_pit = self.fielding_team.stats["pitching"]
        t_fld = self.fielding_team.stats["defense"]
        
        last_ab_was_hr = False
        
        while self.outs < 3:
            # PITCHING CHANGE LOGIC
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

            # AT-BAT LOGIC
            batter = self.batting_team.get_next_batter()
            print(f"\nUp to bat: {batter.name} | Outs: {self.outs} | Bases: {self.get_bases_string()}")
            
            runs_at_start_of_ab = self.runs 
            p_bat = batter.stats["batting"]
            p_pit = self.pitcher.stats["pitching"]
            
            sim = AtBatSimulator(batter, self.pitcher, league_env=self.env, half_inning=self, is_home_batting=not self.is_top)
            outcome = sim.simulate_at_bat(defense=self.defense)
            event = outcome.get("event")

            # PITCH COUNT TRACKER
            if "pitches" in outcome: ab_pitches = outcome["pitches"]
            else:
                if event == "Strikeout": ab_pitches = random.randint(3, 7)
                elif event == "Walk": ab_pitches = random.randint(4, 8)
                elif event == "Hit By Pitch": ab_pitches = random.randint(1, 4)
                else: ab_pitches = random.randint(1, 6)
                
            t_pit["Pitches"] += ab_pitches
            p_pit["Pitches"] += ab_pitches

            last_ab_was_hr = (outcome.get("target") == "HR")
            
            if "log" in outcome:
                print("  [AT-BAT BROADCAST]")
                for log_entry in outcome["log"]:
                    print(f"    {log_entry}")
            
            # INNING ENDING STEAL LOGIC
            if event == "Inning Ending Steal":
                self.batting_team.batter_index -= 1
                if self.batting_team.batter_index < 0:
                    self.batting_team.batter_index = len(self.batting_team.lineup) - 1
                break 

            # STAT DISTRIBUTION & RBI LOGIC
            t_bat["PA"] += 1
            p_bat["PA"] += 1
            
            if event == "Strikeout":
                t_bat["AB"] += 1; p_bat["AB"] += 1
                t_bat["K"] += 1; p_bat["K"] += 1
                t_pit["K"] += 1; p_pit["K"] += 1
                print(f"  Result: Strikeout.")
                self.record_fielding_stat("C", "PO")
                self.record_out()
                
            elif event in ["Walk", "Hit By Pitch"]:
                key = "BB" if event == "Walk" else "HBP"
                t_bat[key] += 1; p_bat[key] += 1
                t_pit[key] += 1; p_pit[key] += 1
                print(f"  Result: {event}.")
                self.advance_all_forced(batter)
                
            elif event == "Ball in Play":
                t_bat["AB"] += 1; p_bat["AB"] += 1
                print(f"  Result: {outcome.get('description', 'Ball in play.')}")
                
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
                            
                            hit_location = outcome.get("location", "Center")
                            self.process_hit_advancement(batter, hit_type, hit_location)
            
            # THE RBI CALCULATOR
            runs_scored_on_play = self.runs - runs_at_start_of_ab
            
            if runs_scored_on_play > 0:
                is_error = outcome.get("error", False) if event == "Ball in Play" else False
                rbi_awarded = 0 if is_error else runs_scored_on_play
                
                if rbi_awarded > 0:
                    p_bat["RBI"] += rbi_awarded
                    t_bat["RBI"] += rbi_awarded
                
                hit_type = outcome.get("target", event)
                location = outcome.get("location", "the field")
                rbi_text = f", driving in {rbi_awarded} run(s)!" if rbi_awarded > 0 else " (Runs scored on error!)"
                
                if hit_type == "HR": desc = f"{batter.name} hits a Home Run to {location}{rbi_text}"
                else: desc = f"{batter.name} hits a {hit_type} to {location}{rbi_text}"
                
                play_record = {
                    "inning": self.inning_num, "half": "Top" if self.is_top else "Bottom",
                    "batter": batter.name, "event": hit_type, "rbi": rbi_awarded, "description": desc
                }
                self.scoring_plays.append(play_record)
            
            # WALK-OFF CHECK
            if not self.is_top and self.inning_num >= 9:
                if (self.home_score + self.runs) > self.away_score:
                    print(f"\n  *** WALK-OFF WINNER! {self.batting_team.name} WIN! ***")
                    self.is_walk_off = True  
                    break

        t_bat["R"] += self.runs
        self.batting_team.linescore.append(self.runs)
        print(f"\n--- {frame} {self.inning_num} OVER | Runs Scored: {self.runs} ---")

        # HALF-INNING STAMINA DEDUCTION (BATTERS ONLY)
        for team in [self.batting_team, self.fielding_team]:
            for player in team.lineup:  
                max_stam = player.attributes.get('batting', {}).get('stamina', 100)
                curr_stam = getattr(player, 'current_stamina', max_stam)
                player.current_stamina = max(0, curr_stam - 1)
    
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

    # BASERUNNING HELPERS
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
        # DYNAMIC OUTFIELDER ARM EXTRACTION
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
                sim = AtBatSimulator(batter, self.pitcher, league_env=self.env, half_inning=self, is_home_batting=not self.is_top)
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
                sim = AtBatSimulator(batter, self.pitcher, league_env=self.env, half_inning=self, is_home_batting=not self.is_top)
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
            
    def process_infield_grounder(self, batter, outcome):
        target_base = outcome.get("target_base", 1)
        is_safe = outcome["safe"]
        is_dp = outcome.get("double_play", False)
        runner_held = outcome.get("runner_held", False)
        fielder_pos = outcome["hit_data"]["target_position"]
        
        if is_dp:
            self.record_out() 
            self.record_out() 

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
        if isinstance(position, int):
            base_map = {1: "1B", 2: "2B", 3: "3B", 4: "C"}
            position = base_map.get(position, "P")

        fielder = self.defense.get(position)
        if fielder:
            fielder.stats["defense"][stat_type] += 1
            fielder.stats["defense"]["TC"] += 1
            
        self.fielding_team.stats["defense"][stat_type] += 1
        self.fielding_team.stats["defense"]["TC"] += 1

class FullGame:
    """Manages the 9-inning game flow between two Team objects."""
    def __init__(self, away_team, home_team, league_env):
        self.away = away_team
        self.home = home_team
        self.env = league_env
        self.inning = 1
        self.scoring_plays = []
        
        self.current_lead = "Tie"
        self.away_por = self.away.pitcher 
        self.home_por = self.home.pitcher 
        
        self.away_starter = self.away.pitcher
        self.home_starter = self.home.pitcher

    def evaluate_run_scored(self, half_inning_obj):
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

    def play_game(self):
        print(f"\n========== PLAY BALL! ==========")
        print(f"{self.away.name} vs. {self.home.name}")
        print(f"================================\n")
        
        while self.inning <= 9 or self.away.stats["batting"]["R"] == self.home.stats["batting"]["R"]:
            
            top_half = HalfInning(self.away, self.home, self.env, self.inning, True, 
                                  self.away.stats["batting"]["R"], self.home.stats["batting"]["R"], 
                                  self.scoring_plays, self)
            top_half.play()
            
            if self.inning >= 9 and self.home.stats["batting"]["R"] > self.away.stats["batting"]["R"]:
                self.home.linescore.append(None)
                break
                
            bottom_half = HalfInning(self.home, self.away, self.env, self.inning, False, 
                                     self.away.stats["batting"]["R"], self.home.stats["batting"]["R"], 
                                     self.scoring_plays, self) 
            bottom_half.play()
            
            self.inning += 1
            
        print(f"\n========== BALLGAME ==========")
        print(f"FINAL SCORE: {self.away.name} {self.away.stats['batting']['R']} - {self.home.name} {self.home.stats['batting']['R']}")
        
        self.award_pitching_decisions()
        print(f"==============================\n")
    
    def check_milestones(self):
        milestones = []
        
        for team, opponent in [(self.away, self.home), (self.home, self.away)]:
            if opponent.stats["batting"]["H"] == 0:
                if opponent.stats["batting"]["BB"] == 0 and opponent.stats["batting"]["HBP"] == 0 and team.stats["defense"]["E"] == 0:
                    milestones.append(f"PERFECT GAME: {team.name} pitching staff!")
                else:
                    milestones.append(f"NO-HITTER: {team.name} pitching staff!")
            elif opponent.stats["batting"]["R"] == 0:
                milestones.append(f"SHUTOUT: {team.name} blanks the opponent.")

            for player in team.lineup:
                stats = player.stats["batting"]
                
                if stats["1B"] >= 1 and stats["2B"] >= 1 and stats["3B"] >= 1 and stats["HR"] >= 1:
                    milestones.append(f"CYCLE: {player.name} hits for the cycle!")
                if stats["HR"] >= 4: milestones.append(f"4-HR GAME: {player.name} hits {stats['HR']} home runs!")
                if stats["RBI"] >= 8: milestones.append(f"8-RBI GAME: {player.name} drives in {stats['RBI']} runs!")
                if stats["H"] >= 5: milestones.append(f"5-HIT GAME: {player.name} collects {stats['H']} hits!")

        return milestones