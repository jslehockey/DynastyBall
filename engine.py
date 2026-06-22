import random
from game_math import compress_rating, calculate_advantage_ratio, OOP_MATRIX
from base_running import calculate_steal_success, should_attempt_steal

class AtBatSimulator:
    def __init__(self, batter, pitcher, league_env=None, half_inning=None, is_home_batting=False, weather=None): 
        self.batter = batter
        self.pitcher = pitcher
        self.balls = 0
        self.strikes = 0
        self.pitch_count = 0
        self.half_inning = half_inning
        self.is_home_batting = is_home_batting
        self.env = league_env.era_modifiers if league_env else {"power": 1.0, "contact": 1.0, "speed": 1.0, "pitching": 1.0, "defense": 1.0}
        
        # --- WEATHER INITIALIZATION ---
        self.weather = weather if weather else {"temp": 70, "wind_speed": 0, "wind_direction": "Calm", "precipitation": "None"}

        # Marathon Man: Boost stamina once per game start.
        if "Marathon Man" in getattr(self.pitcher, 'traits', []) and not getattr(self.pitcher, 'marathon_boosted', False):
            self.pitcher.current_stamina += 20
            self.pitcher.marathon_boosted = True

        b_attr = self.batter.attributes.get('batting', {})
        p_attr = self.pitcher.attributes.get('pitching', {})

        base_timing = b_attr.get('timing', 50) * self.env["contact"]
        base_barreling = b_attr.get('barreling', 50) * self.env["contact"]
        base_eye = b_attr.get('eye', 50) * self.env["contact"]
        base_restraint = b_attr.get('restraint', 50) * self.env["contact"]
        base_strength = b_attr.get('strength', 50) * self.env["power"]
        base_bat_speed = b_attr.get('bat_speed', 50) * self.env["power"]
        base_elevation = b_attr.get('elevation', 50) * self.env["power"]
        
        base_arm_speed = p_attr.get('arm_speed', 50) * self.env["pitching"]
        base_deception = p_attr.get('deception', 50) * self.env["pitching"]
        base_accuracy = p_attr.get('accuracy', 50) * self.env["pitching"]
        base_command = p_attr.get('command', 50) * self.env["pitching"]
        base_spin = p_attr.get('spin_rate', 50) * self.env["pitching"]
        base_bite = p_attr.get('bite', 50) * self.env["pitching"]

        # --- WEATHER IMPACT ON BASE STATS ---
        if self.weather["temp"] < 50:
            base_accuracy = max(1, base_accuracy - 2)  # Cold fingers reduce control
            base_command = max(1, base_command - 2)
            base_strength = max(1, base_strength - 2)  # Cold deadens the ball
        elif self.weather["temp"] > 90:
            base_strength = min(99, base_strength + 2) # Hot air carries
        if self.weather.get("precipitation") == "Rain":
            rain_penalty = random.randint(2, 3)
            base_accuracy = max(1, base_accuracy - rain_penalty) # Slippery baseball
            base_command = max(1, base_command - rain_penalty)

        # --- PLATOON PUNISHER TRAIT INTEGRATION ---
        platoon_mod = -3 if self.pitcher.attributes.get('throws') == self.batter.attributes.get('bats') else 0
        if platoon_mod == 0 and "Platoon Punisher" in getattr(self.batter, 'traits', []):
            platoon_mod += 3 

        approach_slider = self.batter.attributes.get('strategy', {}).get('approach_slider', 0)
        attack_slider = self.pitcher.attributes.get('strategy', {}).get('attack_slider', 0)

        # Fatigue Logic
        stamina_penalty = 0
        max_b_stam = b_attr.get('stamina', 100)
        cur_b_stam = getattr(self.batter, 'current_stamina', max_b_stam)
        b_stam_pct = (cur_b_stam / max_b_stam) * 100

        if b_stam_pct < 40.0:
            safe_pct = max(0.0, b_stam_pct) 
            stamina_penalty = -(((40.0 - safe_pct) / 40.0) * 15.0)

        b_form = getattr(self.batter, 'form', 0) * 2
        p_form = getattr(self.pitcher, 'form', 0) * 2

        self.ab_timing = base_timing + platoon_mod + stamina_penalty - approach_slider + b_form
        self.ab_barreling = base_barreling + platoon_mod + stamina_penalty - approach_slider + b_form
        self.ab_eye = base_eye + stamina_penalty - approach_slider + b_form
        self.ab_restraint = base_restraint + stamina_penalty - approach_slider + b_form
        self.ab_strength = base_strength + platoon_mod + stamina_penalty + approach_slider + b_form
        self.ab_bat_speed = base_bat_speed + stamina_penalty + approach_slider + b_form
        self.ab_elevation = base_elevation + stamina_penalty + b_form
        
        self.ab_arm_speed = base_arm_speed + attack_slider + p_form
        self.ab_deception = base_deception + attack_slider + p_form
        self.ab_accuracy = base_accuracy - attack_slider + p_form
        self.ab_command = base_command - attack_slider + p_form
        self.ab_spin = base_spin + attack_slider + p_form
        self.ab_bite = base_bite + attack_slider + p_form

    def roll_rng(self):
        return int(random.gauss(0, 18))

    def simulate_single_pitch(self, is_bunting=False, allow_2_strike_bunt=False):
        dampener = 99
        hfa_batter_mod = 2.0 if self.is_home_batting else 0.0
        hfa_pitcher_mod = 2.0 if not self.is_home_batting else 0.0

        p_stamina_penalty = 0
        max_p_stam = self.pitcher.attributes.get('pitching', {}).get('stamina', 100)
        cur_p_stam = getattr(self.pitcher, 'current_stamina', max_p_stam)
        p_stam_pct = (cur_p_stam / max_p_stam) * 100

        if p_stam_pct < 50.0:
            p_stamina_penalty = -(((50.0 - p_stam_pct) / 50.0) * 15.0)

        count_leverage = 0
        if self.balls == 3: count_leverage += 4
        if self.strikes == 2: count_leverage -= 4

        timing = self.apply_trait_modifiers("timing", self.ab_timing + count_leverage + self.roll_rng(), False)
        barreling = self.apply_trait_modifiers("barreling", self.ab_barreling + count_leverage + self.roll_rng(), False)
        eye = self.apply_trait_modifiers("eye", self.ab_eye + count_leverage + self.roll_rng(), False)
        restraint = self.apply_trait_modifiers("restraint", self.ab_restraint + count_leverage + self.roll_rng(), False)
        strength = self.apply_trait_modifiers("strength", self.ab_strength + self.roll_rng(), False)
        bat_speed = self.apply_trait_modifiers("bat_speed", self.ab_bat_speed + self.roll_rng(), False)
        accuracy = self.apply_trait_modifiers("accuracy", self.ab_accuracy + p_stamina_penalty + self.roll_rng(), True)
        command = self.apply_trait_modifiers("command", self.ab_command + p_stamina_penalty + self.roll_rng(), True)
        arm_speed = self.apply_trait_modifiers("arm_speed", self.ab_arm_speed + p_stamina_penalty + self.roll_rng(), True)
        deception = self.apply_trait_modifiers("deception", self.ab_deception + p_stamina_penalty + self.roll_rng(), True)
        spin = self.apply_trait_modifiers("spin_rate", self.ab_spin + p_stamina_penalty + self.roll_rng(), True)
        bite = self.apply_trait_modifiers("bite", self.ab_bite + p_stamina_penalty + self.roll_rng(), True)

        # Rain drastically increases wild pitch/HBP risk
        hbp_chance = 0.50 if self.weather.get("precipitation") == "Rain" else 0.25
        if random.uniform(0, 100) <= hbp_chance:
            return {"result": "HBP", "details": "Pitch got away and hit the batter!"}

        if is_bunting:
            if self.strikes == 2 and not allow_2_strike_bunt: pass 
            else: return self.simulate_bunt_attempt(allow_2_strike_bunt)

        zone_prob = (48.0 * ((accuracy + command + dampener) / (150.0 + dampener))) + hfa_pitcher_mod
        in_zone = random.uniform(0, 100) <= zone_prob
        pitch_call = "Strike" if in_zone else "Ball"

        if self.half_inning:
            bases = self.half_inning.bases
            runner_on_1st, runner_on_2nd, runner_on_3rd = bases[1], bases[2], bases[3]
            
            catcher = self.half_inning.defense.get("C")
            if catcher and hasattr(catcher, 'defense'):
                c_def = catcher.defense
                c_arm_str = c_def.get('arm_str', 75)
                c_arm_acc = c_def.get('arm_acc', 75)
                c_reaction = c_def.get('reaction', 75)
            else:
                c_arm_str, c_arm_acc, c_reaction = 75, 75, 75
            
            strategy = self.half_inning.batting_team.lineup[0].attributes.get('strategy', {})
            manager_slider_2nd = strategy.get('steal_2nd_slider', 3) 
            manager_slider_3rd = strategy.get('steal_3rd_slider', 3)
            speed_threshold_2nd = strategy.get('steal_2nd_threshold', 0)
            speed_threshold_3rd = strategy.get('steal_3rd_threshold', 0)
            
            can_steal_2nd = (runner_on_1st is not None) and (runner_on_2nd is None)
            can_steal_3rd = (runner_on_2nd is not None) and (runner_on_3rd is None)

            attempt_steal, target_base, stealing_runner = False, None, None

            if self.strikes < 2:
                if can_steal_3rd:
                    r_base = runner_on_2nd.attributes.get('baserunning', {})
                    r_sprint = r_base.get('sprint_speed', 75)
                    r_instincts = r_base.get('instincts', 75)
                    
                    if should_attempt_steal(r_sprint, r_instincts, 3, manager_slider_3rd, speed_threshold_3rd):
                        attempt_steal, target_base, stealing_runner = True, 3, runner_on_2nd
                        
                elif can_steal_2nd and not attempt_steal:
                    r_base = runner_on_1st.attributes.get('baserunning', {})
                    r_sprint = r_base.get('sprint_speed', 75)
                    r_instincts = r_base.get('instincts', 75)
                    
                    if should_attempt_steal(r_sprint, r_instincts, 2, manager_slider_2nd, speed_threshold_2nd):
                        attempt_steal, target_base, stealing_runner = True, 2, runner_on_1st

            if attempt_steal:
                r_base = stealing_runner.attributes.get('baserunning', {})
                r_sprint = r_base.get('sprint_speed', 75)
                r_instincts = r_base.get('instincts', 75)
                
                # --- WEATHER: RAIN MODIFIES STEAL ATTEMPTS ---
                if self.weather.get("precipitation") == "Rain":
                    r_sprint = max(1, r_sprint - 5) # Wet dirt slows the runner's jump
                
                is_safe = calculate_steal_success(r_sprint, r_instincts, c_arm_str, c_arm_acc, c_reaction, target_base)
                
                if is_safe: 
                    stealing_runner.stats["batting"]["SB"] += 1
                else: 
                    stealing_runner.stats["batting"]["CS"] += 1

                return {
                    "result": "Steal Attempt", "is_safe": is_safe, "target_base": target_base,
                    "stealing_runner": stealing_runner, "pitch_call": pitch_call,
                    "details": f"\n    *** STEAL ATTEMPT! ***\n    {stealing_runner.name} takes off for base {target_base}!\n    Result: {'SAFE' if is_safe else 'OUT'} at base {target_base}. Pitch was a {pitch_call}."
                }
            
        if in_zone:
            raw_swing = 67.0 * ((arm_speed + dampener) / (eye + dampener))
            swing_prob = min(max(raw_swing, 40.0), 92.0) 
        else:
            raw_swing = 30.0 * ((deception + bite + dampener) / (restraint + eye + dampener))
            swing_prob = min(max(raw_swing, 15.0), 55.0)

        if random.uniform(0, 100) > swing_prob:
             return {"result": pitch_call, "details": f"Took a {pitch_call.lower()}."}

        pitch_nastiness = (arm_speed * 0.6) + (deception * 0.4)
        batter_quickness = (timing * 0.6) + (bat_speed * 0.4)
        
        raw_contact = 70.0 * ((batter_quickness + dampener) / (pitch_nastiness + dampener)) 
        contact_prob = min(max(raw_contact + hfa_batter_mod, 55.0), 95.0)
        
        if random.uniform(0, 100) > contact_prob:
            return {"result": "Strike", "details": "Swung and missed!"}

        pitch_movement = (spin * 0.5) + (bite * 0.5)
        raw_in_play = 55.0 * ((barreling + dampener) / (pitch_movement + dampener)) 
        in_play_prob = min(max(raw_in_play + hfa_batter_mod, 40.0), 80.0)
        
        if random.uniform(0, 100) > in_play_prob:
            return {"result": "Foul", "details": "Tipped foul."}

        raw_quality = (strength / (strength + spin)) * 100
        quality_threshold = min(max(raw_quality + hfa_batter_mod, 10.0), 60.0)
        quality_roll = random.randint(1, 100)

        if quality_roll <= (quality_threshold * 0.25): hit_quality = "Crushed!"
        elif quality_roll <= quality_threshold: hit_quality = "Solid Contact"
        else: hit_quality = "Weak Contact"

        hit_data = self.calculate_hit_location(hit_quality, self.ab_strength, self.ab_timing, self.ab_arm_speed, self.ab_spin)

        return {
            "result": "In Play", 
            "details": f"{hit_data['quality']}, hit {hit_data['display_location']} ({hit_data['tendency']} tendency)",
            "hit_data": hit_data 
        }
    
    def apply_post_at_bat_fatigue(self):
        max_stam = self.batter.attributes.get('batting', {}).get('stamina', 100)
        curr_stam = getattr(self.batter, 'current_stamina', max_stam)
        self.batter.current_stamina = max(0, curr_stam - 2)

    def apply_post_at_bat_pitcher_fatigue(self):
        max_stamina = self.pitcher.attributes.get('pitching', {}).get('stamina', 100)
        curr_stamina = getattr(self.pitcher, 'current_stamina', max_stamina)
        
        drain = self.pitch_count
        # --- WEATHER: HEAT MULTIPLIES DRAIN ---
        if self.weather["temp"] >= 90:
            drain *= 1.15
            
        self.pitcher.current_stamina = max(0, curr_stamina - drain)

    def simulate_at_bat(self, bunt_attempt=False, allow_2_strike_bunt=False, defense=None):
        play_log = []
        final_outcome = None  
        
        while self.balls < 4 and self.strikes < 3:
            self.pitch_count += 1

            if "Pitch to Contact" in getattr(self.pitcher, 'traits', []) and random.uniform(0, 100) <= 10.0:
                self.pitch_count -= 1 

            pitch = self.simulate_single_pitch(is_bunting=bunt_attempt, allow_2_strike_bunt=allow_2_strike_bunt)
            
            if pitch["result"] == "Steal Attempt":
                if pitch["pitch_call"] == "Ball": self.balls += 1
                else: self.strikes += 1
                    
                target = pitch["target_base"]
                runner_name = pitch["stealing_runner"].name
                safe_str = "SAFE" if pitch["is_safe"] else "OUT"
                
                log_str = f"Pitch {self.pitch_count}: [STEAL ATTEMPT] {runner_name} goes for {target}B... {safe_str}! (Pitch was a {pitch['pitch_call']}) ({self.balls}-{self.strikes})"
                play_log.append(f"    {log_str}")
                
                if pitch["is_safe"]:
                    self.half_inning.bases[target] = pitch["stealing_runner"]
                    self.half_inning.bases[target - 1] = None
                else:
                    self.half_inning.bases[target - 1] = None
                    self.half_inning.record_out()
                    if self.half_inning.outs >= 3:
                        play_log.append("    [OUT] Inning over on caught stealing.")
                        final_outcome = {"event": "Inning Ending Steal", "log": play_log}
                        break
                continue

            if pitch["result"] == "HBP":
                play_log.append(f"Pitch {self.pitch_count}: {pitch['details']} (Hit By Pitch!)")
                final_outcome = {"event": "Hit By Pitch", "log": play_log}
                break
            elif pitch["result"] == "Ball":
                self.balls += 1
                play_log.append(f"Pitch {self.pitch_count}: {pitch['details']} ({self.balls}-{self.strikes})")
            elif pitch["result"] == "Strike":
                self.strikes += 1
                play_log.append(f"Pitch {self.pitch_count}: {pitch['details']} ({self.balls}-{self.strikes})")
            elif pitch["result"] == "Strikeout":
                play_log.append(f"Pitch {self.pitch_count}: {pitch['details']} - STRIKEOUT!")
                self.pitcher.stats["pitching"]["K"] += 1 
                final_outcome = {"event": "Strikeout", "log": play_log}
                break
            elif pitch["result"] == "Foul":
                if self.strikes < 2: self.strikes += 1
                play_log.append(f"Pitch {self.pitch_count}: {pitch['details']} ({self.balls}-{self.strikes})")
            elif pitch["result"] == "In Play":
                play_log.append(f"Pitch {self.pitch_count}: {pitch['details']}")
                play_outcome = self.resolve_defense(pitch["hit_data"], defense)
                
                state = play_outcome.get("fielder_state")
                target = pitch["hit_data"]["target_position"] 
                is_safe, is_error = True, False
                description = play_outcome["reason"]
                
                batter_sprint = self.batter.attributes.get('baserunning', {}).get('sprint_speed', 75)
                if "Speed Demon" in getattr(self.batter, 'traits', []):
                    batter_sprint += 7
                fielder_arm_str = play_outcome.get("fielder_arm_str", 75)
                fielder_arm_acc = play_outcome.get("fielder_arm_acc", 75)

                if state == "home_run": target = "HR"
                elif state in ["clean_hit_outfield", "past_infielder", "clean_gather_outfield"]:
                    target = self.resolve_batter_hit_type(pitch["hit_data"], batter_sprint, fielder_arm_str)
                elif state == "caught_in_air": is_safe = False 
                elif state == "clean_gather_infield":
                    throw_outcome = self.resolve_infield_throw(pitch["hit_data"], fielder_arm_str, fielder_arm_acc, batter_sprint, target)
                    final_outcome = {
                        "event": "Ball in Play", "target": "Infield Grounder", "safe": throw_outcome["safe"],
                        "error": throw_outcome["error"], "description": description + " " + throw_outcome["reason"],
                        "location": pitch["hit_data"]["display_location"], "log": play_log,
                        "hit_data": pitch["hit_data"], "fielder_state": state,
                        "target_base": throw_outcome.get("target_base", 1),
                        "double_play": throw_outcome.get("double_play", False),
                        "runner_held": throw_outcome.get("runner_held", False)
                    }
                    break
                elif state == "error":
                    is_error = True
                    target = pitch["hit_data"]["target_position"]

                final_outcome = {
                    "event": "Ball in Play", "safe": is_safe, "target": target, "error": is_error,
                    "description": description, "location": pitch["hit_data"]["display_location"], 
                    "log": play_log, "hit_data": pitch["hit_data"], "fielder_state": state,
                    "fielder_arm_str": fielder_arm_str, "fielder_arm_acc": fielder_arm_acc
                }
                break

        if final_outcome is None:
            if self.balls >= 4:
                play_log.append("  [WALK] Batter takes his base.")
                final_outcome = {"event": "Walk", "log": play_log}
            elif self.strikes >= 3:
                play_log.append("  [STRIKEOUT] Batter goes down swinging.")
                self.pitcher.stats["pitching"]["K"] += 1 
                final_outcome = {"event": "Strikeout", "log": play_log}

        self.apply_post_at_bat_fatigue()
        self.apply_post_at_bat_pitcher_fatigue()
        return final_outcome

    def simulate_bunt_attempt(self, allow_2_strike_bunt=False):
        zone_prob = 48.0 * (self.ab_control / 75.0)
        in_zone = random.uniform(0, 100) <= zone_prob
        swing_prob = 85.0 if in_zone else 45.0
        
        if random.uniform(0, 100) > swing_prob:
            return {"result": "Strike" if in_zone else "Ball", "details": f"Bunt attempt pulled back, {'pitch was in the zone' if in_zone else 'ball in the dirt'}."}

        contact_prob = 90.0 * (self.ab_contact / self.ab_velocity)
        if random.uniform(0, 100) > contact_prob:
            return {"result": "Strike", "details": "Swung right through the bunt attempt!"}

        in_play_prob = 65.0 * (self.ab_contact / self.ab_movement) 
        if random.uniform(0, 100) > in_play_prob:
            if self.strikes == 2: return {"result": "Strikeout", "details": "Bunted foul with two strikes!"}
            return {"result": "Foul", "details": "Bunted foul into the backstop."}

        return {"result": "In Play", "details": "Hit Quality: Bunt"}

    def calculate_hit_location(self, hit_quality, strength, timing, arm_speed, spin):
        pitcher_timing = arm_speed + (spin * 0.5) + self.roll_rng()
        batter_timing = timing + (strength * 0.5) + self.roll_rng()
        margin = batter_timing - pitcher_timing
        
        if margin >= 5: timing_tendency = "Pull"
        elif margin <= -5: timing_tendency = "Oppo"
        else: timing_tendency = "Center"

        spray_charts = {
            "Pull":   [15, 25, 35, 15, 7, 2, 1],
            "Oppo":   [1, 2, 7, 15, 35, 25, 15],
            "Center": [4, 10, 16, 40, 16, 10, 4]
        }

        batter_handedness = self.batter.attributes.get('bats', 'R')
        if batter_handedness == 'L':
            if timing_tendency == "Pull": weights = spray_charts["Oppo"]
            elif timing_tendency == "Oppo": weights = spray_charts["Pull"]
            else: weights = spray_charts["Center"]
        else:
            weights = spray_charts[timing_tendency]

        locations = ["Left Field Line", "Dead Left Field", "Left Center Gap", "Dead Center", "Right Center Gap", "Dead Right Field", "Right Field Line"]
        final_location = random.choices(locations, weights=weights, k=1)[0]

        # --- DYNAMIC STADIUM DIMENSIONS HOOKUP ---
        if self.half_inning:
            home_team = self.half_inning.batting_team if self.is_home_batting else self.half_inning.fielding_team
            park_dimensions = home_team.stadium.dimensions
        else:
            park_dimensions = {
                "Left Field Line": 340, "Dead Left Field": 360, "Left Center Gap": 380,
                "Dead Center": 400, "Right Center Gap": 380, "Dead Right Field": 360, "Right Field Line": 340
            }
        
        wall_distance = park_dimensions[final_location]
        elev = self.ab_elevation

        if hit_quality == "Crushed!":
            if elev >= 75: trajectory_weights = [0, 20, 80]
            elif elev <= 40: trajectory_weights = [30, 70, 0]
            else: trajectory_weights = [0, 40, 60] 
            trajectory = random.choices(["Ground Ball", "Over-Infield Line Drive", "Fly Ball"], weights=trajectory_weights)[0]
            power_transfer = 1.0
        elif hit_quality == "Solid Contact":
            if elev >= 75: trajectory_weights = [20, 10, 25, 45]
            elif elev <= 40: trajectory_weights = [70, 20, 10, 0]
            else: trajectory_weights = [45, 15, 15, 25]
            trajectory = random.choices(["Ground Ball", "Player-Height Line Drive", "Over-Infield Line Drive", "Fly Ball"], weights=trajectory_weights)[0]
            power_transfer = 0.75
        else:
            if elev >= 70: trajectory_weights = [40, 55, 5]
            elif elev <= 40: trajectory_weights = [80, 15, 5]
            else: trajectory_weights = [60, 35, 5]
            trajectory = random.choices(["Ground Ball", "Pop Up", "Player-Height Line Drive"], weights=trajectory_weights)[0]
            power_transfer = 0.40

        if "Groundball Guru" in getattr(self.pitcher, 'traits', []) and trajectory in ["Over-Infield Line Drive", "Player-Height Line Drive"]:
            if random.uniform(0, 100) <= 10.0:
                trajectory = "Ground Ball"
                power_transfer = 0.40
                
        if "Launch Angle God" in getattr(self.batter, 'traits', []) and trajectory == "Ground Ball":
            if random.uniform(0, 100) <= 10.0:
                trajectory = random.choice(["Player-Height Line Drive", "Fly Ball"])
                power_transfer = 0.75

        baseline_distance = (strength * 5.2) * power_transfer

        if trajectory == "Ground Ball": raw_distance = baseline_distance * random.uniform(0.05, 0.28) 
        elif trajectory == "Player-Height Line Drive": raw_distance = baseline_distance * random.uniform(0.3, 0.5)
        elif trajectory == "Pop Up": raw_distance = baseline_distance * random.uniform(0.1, 0.3)
        elif trajectory == "Over-Infield Line Drive": raw_distance = baseline_distance * random.uniform(0.6, 0.8)
        else: raw_distance = baseline_distance * random.uniform(0.85, 1.0)

        distance_with_variance = raw_distance + (self.roll_rng() * 1.5)

        # --- WEATHER: WIND MODIFIER ---
        if trajectory in ["Fly Ball", "Over-Infield Line Drive"]:
            wind_effect = self.weather.get("wind_speed", 0) * 0.8
            direction = self.weather.get("wind_direction", "Calm")
            if direction == "Blowing In":
                distance_with_variance -= wind_effect
            elif direction == "Blowing Out":
                distance_with_variance += wind_effect

        final_distance = int(max(5, min(distance_with_variance, 515)))

        target_position, hit_type = None, "In Play"
        display_location = f"to {final_location}" 

        if final_distance >= wall_distance and trajectory in ["Fly Ball", "Over-Infield Line Drive"]:
            target_position, hit_type = "Bleachers", "Home Run"
            location_map = {
                "Left Field Line": "Deep Left Field Line", "Dead Left Field": "Deep Left Field",
                "Left Center Gap": "Deep Left Center", "Dead Center": "Deep Center Field",
                "Right Center Gap": "Deep Right Center", "Dead Right Field": "Deep Right Field",
                "Right Field Line": "Deep Right Field Line"
            }
            display_location = f"{final_distance} feet to {location_map.get(final_location, 'the bleachers')}"
        elif final_distance <= 130:
            if final_location == "Left Field Line": target_position, display_location = "3B", "down the third base line"
            elif final_location == "Dead Left Field": target_position, display_location = "3B", "into the 5-6 hole"
            elif final_location == "Left Center Gap": target_position, display_location = "SS", "to the left side of the infield"
            elif final_location == "Dead Center": target_position, display_location = "SS", "up the middle"
            elif final_location == "Right Center Gap": target_position, display_location = "2B", "to the right side of the infield"
            elif final_location == "Dead Right Field": target_position, display_location = "2B", "into the 3-4 hole"
            elif final_location == "Right Field Line": target_position, display_location = "1B", "down the first base line"
        else:
            if final_location in ["Left Field Line", "Dead Left Field", "Left Center Gap"]: target_position = "LF"
            elif final_location == "Dead Center": target_position = "CF"
            elif final_location in ["Right Center Gap", "Dead Right Field", "Right Field Line"]: target_position = "RF"

        return {
            "tendency": timing_tendency, "location": final_location, "display_location": display_location,  
            "quality": hit_quality, "trajectory": trajectory, "distance": final_distance,
            "target_position": target_position, "hit_type": hit_type
        }
    
    def resolve_defense(self, hit_data, defense):
        position = hit_data["target_position"]
        
        if hit_data["hit_type"] == "Home Run":
            return {
                "fielder_state": "home_run", "out_recorded_on_catch": False, 
                "reason": f"HOME RUN! ({hit_data['distance']}ft to {hit_data['location']})"
            }

        distance, location, trajectory = hit_data["distance"], hit_data["location"], hit_data["trajectory"]
        
        bloop_mapping = {
            "Left Field Line":  {"if": "3B", "if_path": "direct",   "of": ["LF"],       "of_path": "direct"},
            "Dead Left Field":  {"if": "SS", "if_path": "direct",   "of": ["LF"],       "of_path": "direct"},
            "Left Center Gap":  {"if": "SS", "if_path": "diagonal", "of": ["LF", "CF"], "of_path": "diagonal"},
            "Dead Center":      {"if": "SS", "if_path": "direct",   "of": ["CF"],       "of_path": "direct"}, 
            "Right Center Gap": {"if": "2B", "if_path": "diagonal", "of": ["CF", "RF"], "of_path": "diagonal"},
            "Dead Right Field": {"if": "2B", "if_path": "direct",   "of": ["RF"],       "of_path": "direct"},
            "Right Field Line": {"if": "1B", "if_path": "direct",   "of": ["RF"],       "of_path": "direct"}
        }

        mapping = bloop_mapping.get(location)
        
        def get_fielder_speed(pos):
            fielder = defense.get(pos)
            if fielder and hasattr(fielder, 'attributes'):
                return fielder.attributes.get('baserunning', {}).get('sprint_speed', 75)
            return 75

        if_speed = get_fielder_speed(mapping["if"])
        of_speeds = [get_fielder_speed(pos) for pos in mapping["of"]]
        of_speed = max(of_speeds)

        if_delta, of_delta = if_speed - 75, of_speed - 75
        if_shift = if_delta if mapping["if_path"] == "direct" else (if_delta / 2.0)
        of_shift = of_delta if mapping["of_path"] == "direct" else (of_delta / 2.0)

        dynamic_min, dynamic_max = 145 + if_shift, 180 - of_shift
        is_sprinting_catch = False

        if trajectory != "Pop Up":
            if dynamic_min < distance < dynamic_max:
                 return {
                     "fielder_state": "clean_hit_outfield", "out_recorded_on_catch": False, 
                     "reason": f"Hit! Bloops perfectly into shallow {location} ({distance}ft)."
                 }
            elif 145 < distance < 180:
                is_sprinting_catch = True

        if position in ["LF", "CF", "RF"]:
            if hit_data["trajectory"] in ["Ground Ball", "Player-Height Line Drive"]:
                 return {
                     "fielder_state": "clean_hit_outfield", "out_recorded_on_catch": False, 
                     "reason": f"Hit! Sneaks through the infield into {hit_data['location']} ({hit_data['distance']}ft)."
                 }
            elif 145 < hit_data["distance"] < 180 and hit_data["trajectory"] != "Pop Up":
                 return {
                     "fielder_state": "clean_hit_outfield", "out_recorded_on_catch": False, 
                     "reason": f"Hit! Bloops perfectly into shallow {hit_data['location']} ({hit_data['distance']}ft)."
                 }

        fielder_obj = defense.get(position)
        
        if fielder_obj and hasattr(fielder_obj, 'defense'):
            f_def = fielder_obj.defense
            r_attr = fielder_obj.attributes.get('baserunning', {})
            
            f_reaction = f_def.get('reaction', 75)
            f_range = f_def.get('range', 75)
            f_glove = f_def.get('glove', 75)
            f_arm_str = f_def.get('arm_str', 75)
            f_arm_acc = f_def.get('arm_acc', 75)
            f_sprint = r_attr.get('sprint_speed', 75)

            f_primary = getattr(fielder_obj, 'primary_pos', position)
            oop_mod = OOP_MATRIX.get(f_primary, {}).get(position, 0.50)
            
            f_reaction *= oop_mod
            f_range *= oop_mod
            f_glove *= oop_mod
            f_arm_str *= max(0.75, oop_mod)
            f_arm_acc *= oop_mod
            
            f_max_stam = fielder_obj.attributes.get('batting', {}).get('stamina', 100)
            f_cur_stam = getattr(fielder_obj, 'current_stamina', f_max_stam)
            f_stam_pct = (f_cur_stam / f_max_stam) * 100
            
            if f_stam_pct < 40.0:
                safe_f_pct = max(0.0, f_stam_pct)
                f_penalty = ((40.0 - safe_f_pct) / 40.0) * 15.0
                
                f_reaction = max(1, f_reaction - f_penalty)
                f_range = max(1, f_range - f_penalty)
                f_sprint = max(1, f_sprint - f_penalty)
                f_glove = max(1, f_glove - f_penalty)
                f_arm_str = max(1, f_arm_str - f_penalty)
                f_arm_acc = max(1, f_arm_acc - f_penalty)
        else:
            f_reaction, f_range, f_sprint, f_glove, f_arm_str, f_arm_acc = 75, 75, 75, 75, 75, 75 

        def_mod = self.env.get("defense", 1.0)
        f_reaction *= def_mod
        f_range *= def_mod
        f_sprint *= def_mod
        f_glove *= def_mod
        f_arm_str *= def_mod
        f_arm_acc *= def_mod

        effective_range = (f_reaction * 0.4) + (f_range * 0.6)

        if hit_data["quality"] == "Crushed!": difficulty = 87 if hit_data["trajectory"] == "Player-Height Line Drive" else 81
        elif hit_data["quality"] == "Solid Contact": difficulty = 69
        else: difficulty = 45 if hit_data["trajectory"] == "Ground Ball" else 25 

        if hit_data["trajectory"] == "Ground Ball" and hit_data["location"] in ["Left Center Gap", "Right Center Gap"]:
            difficulty += 13

        range_roll = effective_range + self.roll_rng()
        if range_roll < difficulty:
            if hit_data["trajectory"] == "Ground Ball" and position in ["1B", "2B", "3B", "SS"]:
                return {
                    "fielder_state": "past_infielder", "out_recorded_on_catch": False,
                    "reason": f"Hit! Grounder sneaks past the {position} into the outfield."
                }
            else:
                return {
                    "fielder_state": "clean_hit_outfield", "out_recorded_on_catch": False,
                    "reason": f"Hit! Drops in or gets past the {position} ({hit_data['distance']}ft)."
                }

        effective_glove = max(50, min(100, f_glove))
        base_error_prob = 12.0 * ((100 - effective_glove) / 50.0) ** 1.25
        
        if hit_data["trajectory"] == "Player-Height Line Drive": error_prob = base_error_prob * 2.0  
        elif hit_data["trajectory"] in ["Fly Ball", "Pop Up"]: error_prob = base_error_prob * 0.2  
        else: error_prob = base_error_prob       

        if hit_data["quality"] == "Crushed!": error_prob *= 1.5 
        if is_sprinting_catch: error_prob += 3.5 
        
        # --- WEATHER: RAIN INCREASES ERROR PROBABILITY ---
        if self.weather.get("precipitation") == "Rain":
            error_prob *= 1.045

        if random.uniform(0, 100) < error_prob:
            action = "dropped" if hit_data["trajectory"] in ["Fly Ball", "Pop Up"] else "booted"
            reason_prefix = "On the run, " if is_sprinting_catch else ""
            return {
                "fielder_state": "error", "out_recorded_on_catch": False, 
                "reason": f"Error! {reason_prefix}{position} {action} the ball in {hit_data['location']}."
            }
        
        if hit_data["trajectory"] in ["Fly Ball", "Pop Up", "Over-Infield Line Drive", "Player-Height Line Drive"]:
            out_types = {
                "Fly Ball": "Flyout", "Over-Infield Line Drive": "Lineout",
                "Player-Height Line Drive": "Lineout", "Pop Up": "Popout"
            }
            out_result = out_types.get(hit_data["trajectory"], "Caught")
            
            return {
                "fielder_state": "caught_in_air", "out_recorded_on_catch": True,
                "reason": f"{out_result} to {position} ({hit_data['distance']}ft)."
            }
            
        elif hit_data["trajectory"] == "Ground Ball":
            if position in ["1B", "2B", "3B", "SS"]:
                return {
                    "fielder_state": "clean_gather_infield", "out_recorded_on_catch": False, 
                    "fielder_arm_str": f_arm_str, "fielder_arm_acc": f_arm_acc, 
                    "reason": f"Fielded cleanly by {position}, prepping to throw."
                }
            else:
                return {
                    "fielder_state": "clean_gather_outfield", "out_recorded_on_catch": False, 
                    "fielder_arm_str": f_arm_str, "fielder_arm_acc": f_arm_acc, 
                    "reason": f"Fielded cleanly in the outfield by {position}."
                }
            
    def resolve_infield_throw(self, hit_data, fielder_arm_str, fielder_arm_acc, batter_sprint, position):
        bases, outs, inning = self.half_inning.bases, self.half_inning.outs, self.half_inning.inning_num
        distance, quality = hit_data["distance"], hit_data.get("quality", "Weak Contact")
        
        run_diff = abs(self.half_inning.batting_team.stats["batting"]["R"] - self.half_inning.fielding_team.stats["batting"]["R"])
        is_late_game_pressure = inning >= 9 and run_diff <= 2
        initial_bobble = random.uniform(0, 100) < 6.0 
        
        force_at_2b = bases[1] is not None
        force_at_3b = force_at_2b and bases[2] is not None
        force_at_home = force_at_3b and bases[3] is not None

        target_base, is_force, attempt_dp = 1, True, False
        target_runner, runner_held, play_profile = self.batter, False, "Standard"

        if initial_bobble:
            target_base, play_profile = 1, "Bobble"
        else:
            if force_at_home and outs == 0 and (is_late_game_pressure or quality in ["Solid Contact", "Crushed!"]):
                target_base, target_runner, attempt_dp, play_profile = 4, bases[3], True, "Home-to-1st DP"
            elif force_at_3b and position == "3B" and outs < 2 and quality in ["Solid Contact", "Crushed!"]:
                target_base, target_runner, attempt_dp, play_profile = 3, bases[2], True, "5-3 DP"
            elif is_late_game_pressure and outs < 2:
                if outs == 1 and force_at_2b and position in ["SS", "2B", "3B"]: target_base, target_runner, attempt_dp = 2, bases[1], True
                elif force_at_home: target_base, target_runner = 4, bases[3]
                elif force_at_3b: target_base, target_runner = 3, bases[2]
                elif force_at_2b: target_base, target_runner, attempt_dp = 2, bases[1], True
            elif force_at_home and outs < 2: target_base, target_runner, attempt_dp = 4, bases[3], True
            elif force_at_3b and outs < 2:
                if position == "3B" or distance < 90: target_base, target_runner, attempt_dp = 3, bases[2], True
                else: target_base = 1
            elif force_at_2b and outs < 2: target_base, target_runner, attempt_dp = 2, bases[1], True
            elif bases[2] is not None and not force_at_3b and outs < 2:
                if position in ["SS", "3B"] and distance < 100: runner_held, target_base, target_runner, play_profile = True, 1, self.batter, "Runner held"
                else: target_base = 1

        runner_speed = target_runner.attributes.get('baserunning', {}).get('sprint_speed', 75) if target_runner != self.batter else batter_sprint
        if target_runner != self.batter and "Speed Demon" in getattr(target_runner, 'traits', []):
            runner_speed += 7

        effective_arm_acc = max(50, min(100, fielder_arm_acc))
        throw_error_prob = 12.0 * ((100 - effective_arm_acc) / 50.0) ** 1.25
        
        if distance > 110: throw_error_prob *= 1.5 
        elif distance < 70: throw_error_prob *= 0.5 

        if random.uniform(0, 100) < throw_error_prob:
            base_str = "Home" if target_base == 4 else f"{target_base}B"
            return {
                "safe": True, "error": True, "double_play": False, "target_base": target_base,
                "reason": f"Throwing Error! {position} sailed the throw to {base_str}."
            }

        distance_advantage = (distance - 90) * 0.4 
        runner_score = runner_speed + distance_advantage + self.roll_rng()
        
        base_throw_advantage = 25 
        tag_penalty = 0 if is_force else 15 
        fielder_throw_score = fielder_arm_str + base_throw_advantage - tag_penalty + self.roll_rng()
        
        base_str = "Home" if target_base == 4 else f"{target_base}B"
        play_type_str = "Force out" if is_force else "Tag applied"
        
        if initial_bobble: primary_out_reason = f"Bobble by {position}, but recovers in time to get the out at {base_str}."
        elif runner_held: primary_out_reason = f"Runner holds at 2nd. {position} throws to 1st for the out."
        else: primary_out_reason = f"{play_type_str} at {base_str}."

        if runner_score >= fielder_throw_score:
            reason_str = f"Infield Hit! {position} bobbled the transfer and {target_runner.name} is safe at {base_str}." if initial_bobble else f"Infield Hit! {target_runner.name} beats the throw to {base_str}."
            return {
                "safe": True, "error": False, "double_play": False, "target_base": target_base, 
                "runner_held": runner_held, "reason": reason_str
            }
        else:
            dp_result = False
            if attempt_dp and is_force:
                if random.uniform(0, 100) < 10.0:
                    primary_out_reason = f"Fielder's Choice! {position} gets the out at {base_str}, but bobbles the pivot! Batter safe at 1st."
                else:
                    pivot_tax = 15 if play_profile == "5-3 DP" else 20 
                    batter_run_score = batter_sprint + self.roll_rng() + pivot_tax
                    relay_arm_score = fielder_arm_str + base_throw_advantage + self.roll_rng() 
                    
                    if batter_run_score < relay_arm_score:
                        dp_result = True
                        if play_profile == "5-3 DP": primary_out_reason = "5-3 Double Play! Steps on third, fires to first."
                        elif play_profile == "Home-to-1st DP": primary_out_reason = "1-2-3 Double Play! Fires home, catcher turns it to first!"
                        elif position in ["SS", "2B"]: primary_out_reason = f"6-4-3 Double Play!" 
                        else: primary_out_reason = f"Double Play turned by {position}!"
                    else:
                        primary_out_reason = f"Fielder's Choice. Out at {base_str}, but batter beats the relay to 1st."

            return {
                "safe": False, "error": False, "double_play": dp_result, "target_base": target_base, 
                "runner_held": runner_held, "reason": primary_out_reason
            }
    
    def resolve_extra_base_attempt(self, runner_sprint, fielder_arm_str, fielder_arm_acc, hit_location, target_base, is_hit_and_run=False, runner_traits=None):
        if runner_traits and "Speed Demon" in runner_traits:
            runner_sprint += 7
        safe_prob = 60 + ((runner_sprint - fielder_arm_str) * 0.5)
        if is_hit_and_run: safe_prob += 20 

        location_throw_advantages = {
            "LF_to_2B": 15, "CF_to_2B": 10, "RF_to_2B": 10,
            "LF_to_3B": 25, "CF_to_3B": 15, "RF_to_3B": -5,  
            "LF_to_Home": 10, "CF_to_Home": 5, "RF_to_Home": 0 
        }

        throw_scenario = ""
        if hit_location in ["Left Field Line", "Dead Left Field", "Left Center Gap"]: throw_scenario = f"LF_to_{target_base}"
        elif hit_location == "Dead Center": throw_scenario = f"CF_to_{target_base}"
        elif hit_location in ["Right Center Gap", "Dead Right Field", "Right Field Line"]: throw_scenario = f"RF_to_{target_base}"

        safe_prob = max(5, min(95, safe_prob - (location_throw_advantages.get(throw_scenario, 10) * 0.75)))
        
        effective_arm = max(50, min(100, fielder_arm_acc))
        throw_error_prob = 12.0 * ((100 - effective_arm) / 50.0) ** 1.25
        
        if random.uniform(0, 100) < throw_error_prob:
            return {"safe": True, "error": True, "reason": f"SAFE at {target_base}! The throw from {hit_location} was wide."}

        if random.uniform(0, 100) <= safe_prob:
            return {"safe": True, "error": False, "reason": f"SAFE at {target_base}! Runner beats the tag from {hit_location}."}
        else:
            return {"safe": False, "error": False, "reason": f"OUT at {target_base}! Gunned down by the outfielder."}
    
    def resolve_tag_up(self, runner_sprint, fielder_arm_str, distance, target_base, hit_location, runner_traits=None):
        if runner_traits and "Speed Demon" in runner_traits:
            runner_sprint += 7
        safe_prob = 50.0 + ((runner_sprint - fielder_arm_str) * 0.62) + ((distance - 270) * 0.3)

        if target_base == "3B" and hit_location in ["Left Field Line", "Dead Left Field", "Left Center Gap"]:
            safe_prob -= 35 

        safe_prob = max(5, min(95, safe_prob))

        if random.uniform(0, 100) <= safe_prob:
            return {"safe": True, "reason": f"SAFE at {target_base}! Beats the throw from the outfield."}
        else:
            return {"safe": False, "reason": f"OUT at {target_base}! Gunned down trying to tag up."}
            
    def resolve_batter_hit_type(self, hit_data, batter_sprint, fielder_arm_str):
        distance, location = hit_data["distance"], hit_data["location"]
        is_gap_or_line = location in ["Left Field Line", "Right Field Line", "Left Center Gap", "Right Center Gap"]
        
        if distance < 210: return "1B"
            
        if distance >= 300 and is_gap_or_line:
            if (batter_sprint + self.roll_rng()) > (fielder_arm_str + 15 + self.roll_rng()): return "3B"
            return "2B"
        elif distance >= 230 and is_gap_or_line:
            return "2B"
        elif distance >= 280 and not is_gap_or_line:
            if (batter_sprint + self.roll_rng()) > (fielder_arm_str + 10 + self.roll_rng()): return "2B"
            return "1B"
            
        return "1B"
    
    def apply_trait_modifiers(self, attr_name, value, is_pitcher):
        target = self.pitcher if is_pitcher else self.batter
        traits = getattr(target, 'traits', [])
        
        # PITCHER TRAITS (Dynamic)
        if is_pitcher:
            if "Escape Artist" in traits and self.half_inning and any(self.half_inning.bases[b] for b in [2, 3]):
                if attr_name in ["accuracy", "bite"]: value += 6
            if "Putaway Pitcher" in traits and self.strikes == 2:
                if attr_name in ["arm_speed", "deception"]: value += 6
            if "Lights Out" in traits and self.half_inning and self.half_inning.inning_num >= 8:
                run_diff = abs(self.half_inning.batting_team.stats["batting"]["R"] - self.half_inning.fielding_team.stats["batting"]["R"])
                if run_diff <= 3: value += 4
        
        # BATTER TRAITS (Dynamic)
        else:
            if "Clutch" in traits and self.half_inning and any(self.half_inning.bases[b] for b in [1, 2, 3]):
                if attr_name in ["timing", "strength"]: value += 6
            if "Table Setter" in traits and self.half_inning and self.half_inning.outs == 0:
                if attr_name in ["eye", "restraint"]: value += 7
            if "First Pitch Killer" in traits and self.balls == 0 and self.strikes == 0:
                if attr_name in ["barreling", "bat_speed"]: value += 7
                elif attr_name == "restraint": value -= 7
                
        return value