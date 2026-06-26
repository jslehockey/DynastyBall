# ==========================================
# engine.py
# ==========================================
# The core simulation hub. Manages the At-Bat while-loop, 
# pitch counts, and delegates math/physics to external modules.
# ==========================================
import random

# --- NEW REFACTORED DOMAINS ---
import engine_modifiers
import engine_baseRunning
import engine_physics
import engine_defense

# Expose homefield modifiers so other files can still import it from 'engine'
from engine_modifiers import get_homefield_modifiers

# Create local aliases so the engine loop can easily call the steal functions
calculate_steal_success = engine_baseRunning.calculate_steal_success
should_attempt_steal = engine_baseRunning.should_attempt_steal

class AtBatSimulator:
    def __init__(self, batter, pitcher, league_env=None, half_inning=None, is_home_batting=False, weather=None): 
        # --- GAME STATE ---
        self.batter = batter
        self.pitcher = pitcher
        self.balls = 0
        self.strikes = 0
        self.pitch_count = 0
        self.half_inning = half_inning
        self.is_home_batting = is_home_batting
        self.env = league_env.era_modifiers if league_env else {"power": 1.0, "contact": 1.0, "speed": 1.0, "pitching": 1.0, "defense": 1.0}
        self.weather = weather if weather else {"temp": 70, "wind_speed": 0, "wind_direction": "Calm", "precipitation": "None"}

        # --- PRE-GAME TRAIT INJECTIONS ---
        if "Marathon Man" in getattr(self.pitcher, 'traits', []) and not getattr(self.pitcher, 'marathon_boosted', False):
            self.pitcher.current_stamina += 15
            self.pitcher.marathon_boosted = True

        # --- BASE RATING EXTRACTION ---
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

        # --- WEATHER & PLATOON IMPACT ---
        if self.weather["temp"] < 50:
            base_accuracy = max(1, base_accuracy - 2)  
            base_command = max(1, base_command - 2)
            base_strength = max(1, base_strength - 2)  
        elif self.weather["temp"] > 90:
            base_strength = min(99, base_strength + 2) 
            
        if self.weather.get("precipitation") == "Rain":
            rain_penalty = random.randint(2, 3)
            base_accuracy = max(1, base_accuracy - rain_penalty) 
            base_command = max(1, base_command - rain_penalty)

        platoon_mod = -3 if self.pitcher.attributes.get('throws') == self.batter.attributes.get('bats') else 0
        if platoon_mod == 0 and "Platoon Punisher" in getattr(self.batter, 'traits', []):
            platoon_mod += 3 

        approach_slider = self.batter.attributes.get('strategy', {}).get('approach_slider', 0)
        attack_slider = self.pitcher.attributes.get('strategy', {}).get('attack_slider', 0)

        # --- FATIGUE & FORM ---
        stamina_penalty = 0
        max_b_stam = b_attr.get('stamina', 100)
        cur_b_stam = getattr(self.batter, 'current_stamina', max_b_stam)
        b_stam_pct = (cur_b_stam / max_b_stam) * 100

        if b_stam_pct < 28.0:
            safe_pct = max(0.0, b_stam_pct) 
            stamina_penalty = -(((40.0 - safe_pct) / 40.0) * 15.0)

        b_form = getattr(self.batter, 'form', 0) * 2
        p_form = getattr(self.pitcher, 'form', 0) * 2

        # --- FINAL ACTIVE AT-BAT RATINGS ---
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

    # ==========================================
    # MICRO-SIMULATION: THE SINGLE PITCH
    # ==========================================
    def simulate_single_pitch(self, is_bunting=False, allow_2_strike_bunt=False):
        dampener = 99
        hfa_batter_mod = 2.0 if self.is_home_batting else 0.0
        hfa_pitcher_mod = 2.0 if not self.is_home_batting else 0.0

        max_p_stam = self.pitcher.attributes.get('pitching', {}).get('stamina', 100)
        cur_p_stam = getattr(self.pitcher, 'current_stamina', max_p_stam)
        p_stam_pct = (cur_p_stam / max_p_stam)

        if p_stam_pct < 0.40:
            # Pitchers start losing command below 60%
            fatigue_factor = ((0.40 - p_stam_pct) / 0.40) ** 1.05
            p_stamina_penalty = -(fatigue_factor * 17.5) 
        else:
            p_stamina_penalty = 0

        count_leverage = 0
        if self.balls == 3: count_leverage += 4
        if self.strikes == 2: count_leverage -= 4

        # DELEGATION: Trait Modifiers
        timing = engine_modifiers.apply_trait_modifiers(self, "timing", self.ab_timing + count_leverage + self.roll_rng(), False)
        barreling = engine_modifiers.apply_trait_modifiers(self, "barreling", self.ab_barreling + count_leverage + self.roll_rng(), False)
        eye = engine_modifiers.apply_trait_modifiers(self, "eye", self.ab_eye + count_leverage + self.roll_rng(), False)
        restraint = engine_modifiers.apply_trait_modifiers(self, "restraint", self.ab_restraint + count_leverage + self.roll_rng(), False)
        strength = engine_modifiers.apply_trait_modifiers(self, "strength", self.ab_strength + self.roll_rng(), False)
        bat_speed = engine_modifiers.apply_trait_modifiers(self, "bat_speed", self.ab_bat_speed + self.roll_rng(), False)
        
        accuracy = engine_modifiers.apply_trait_modifiers(self, "accuracy", self.ab_accuracy + p_stamina_penalty + self.roll_rng(), True)
        command = engine_modifiers.apply_trait_modifiers(self, "command", self.ab_command + p_stamina_penalty + self.roll_rng(), True)
        arm_speed = engine_modifiers.apply_trait_modifiers(self, "arm_speed", self.ab_arm_speed + p_stamina_penalty + self.roll_rng(), True)
        deception = engine_modifiers.apply_trait_modifiers(self, "deception", self.ab_deception + p_stamina_penalty + self.roll_rng(), True)
        spin = engine_modifiers.apply_trait_modifiers(self, "spin_rate", self.ab_spin + p_stamina_penalty + self.roll_rng(), True)
        bite = engine_modifiers.apply_trait_modifiers(self, "bite", self.ab_bite + p_stamina_penalty + self.roll_rng(), True)

        hbp_chance = 0.50 if self.weather.get("precipitation") == "Rain" else 0.25
        if random.uniform(0, 100) <= hbp_chance:
            return {"result": "HBP", "details": "Pitch got away and hit the batter!"}

        # DELEGATION: Bunt Physics
        if is_bunting:
            if self.strikes == 2 and not allow_2_strike_bunt: pass 
            else: return engine_physics.simulate_bunt_attempt(self, allow_2_strike_bunt)

        zone_prob = (48.0 * ((accuracy + command + dampener) / (150.0 + dampener))) + hfa_pitcher_mod
        in_zone = random.uniform(0, 100) <= zone_prob
        pitch_call = "Strike" if in_zone else "Ball"

        # --- STEAL ATTEMPT INTERCEPT ---
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
                
                if self.weather.get("precipitation") == "Rain":
                    r_sprint = max(1, r_sprint - 5) 
                
                is_safe = calculate_steal_success(r_sprint, r_instincts, c_arm_str, c_arm_acc, c_reaction, target_base)
                
                if is_safe: stealing_runner.stats["batting"]["SB"] += 1
                else: stealing_runner.stats["batting"]["CS"] += 1

                return {
                    "result": "Steal Attempt", "is_safe": is_safe, "target_base": target_base,
                    "stealing_runner": stealing_runner, "pitch_call": pitch_call,
                    "details": f"\n    *** STEAL ATTEMPT! ***\n    {stealing_runner.name} takes off for base {target_base}!\n    Result: {'SAFE' if is_safe else 'OUT'} at base {target_base}. Pitch was a {pitch_call}."
                }
            
        # --- SWING & MISS PHYSICS ---
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

        # DELEGATION: Trajectory and Location Physics
        hit_data = engine_physics.calculate_hit_location(self, hit_quality, self.ab_strength, self.ab_timing, self.ab_arm_speed, self.ab_spin)

        return {
            "result": "In Play", 
            "details": f"{hit_data['quality']}, hit {hit_data['display_location']} ({hit_data['tendency']} tendency)",
            "hit_data": hit_data 
        }

    # ==========================================
    # MACRO-SIMULATION: THE AT-BAT LOOP
    # ==========================================
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
                final_outcome = {"event": "Strikeout", "log": play_log}
                break
            elif pitch["result"] == "Foul":
                if self.strikes < 2: self.strikes += 1
                play_log.append(f"Pitch {self.pitch_count}: {pitch['details']} ({self.balls}-{self.strikes})")
            elif pitch["result"] == "In Play":
                play_log.append(f"Pitch {self.pitch_count}: {pitch['details']}")
                
                # DELEGATION: Outfield Defense & Robs
                play_outcome = engine_defense.resolve_defense(self, pitch["hit_data"], defense)
                
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
                    # DELEGATION: Gap distances and stretching logic
                    target = engine_physics.resolve_batter_hit_type(self, pitch["hit_data"], batter_sprint, fielder_arm_str)
                elif state == "caught_in_air": is_safe = False 
                elif state == "clean_gather_infield":
                    # DELEGATION: Infield throws, double plays, fielding errors
                    throw_outcome = engine_defense.resolve_infield_throw(self, pitch["hit_data"], fielder_arm_str, fielder_arm_acc, batter_sprint, target)
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

        # --- FALLBACK RESOLUTION ---
        if final_outcome is None:
            if self.balls >= 4:
                play_log.append("  [WALK] Batter takes his base.")
                final_outcome = {"event": "Walk", "log": play_log}
                
            elif self.strikes >= 3:
                play_log.append("  [STRIKEOUT] Batter goes down swinging.")
                final_outcome = {"event": "Strikeout", "log": play_log}

        self.apply_post_at_bat_fatigue()
        self.apply_post_at_bat_pitcher_fatigue()
        return final_outcome

    # ==========================================
    # UTILITY & END OF PLAY FATIGUE
    # ==========================================
    def apply_post_at_bat_fatigue(self):
        max_stam = self.batter.attributes.get('batting', {}).get('stamina', 100)
        curr_stam = getattr(self.batter, 'current_stamina', max_stam)
        self.batter.current_stamina = max(0, curr_stam - 2)

    def apply_post_at_bat_pitcher_fatigue(self):
        max_stamina = self.pitcher.attributes.get('pitching', {}).get('stamina', 100)
        curr_stamina = getattr(self.pitcher, 'current_stamina', max_stamina)
        
        drain = self.pitch_count
        if self.weather["temp"] >= 90:
            drain *= 1.07
            
        self.pitcher.current_stamina = max(0, curr_stamina - drain)

    # ==========================================
    # EXPOSED API FOR DOWNSTREAM GAME FLOW
    # ==========================================
    def resolve_extra_base_attempt(self, runner_sprint, fielder_arm_str, fielder_arm_acc, hit_location, target_base, is_hit_and_run=False, runner_traits=None):
        """Pass-through to engine_baserunning to prevent import breaks in flow_half_inning.py"""
        return engine_baseRunning.resolve_extra_base_attempt(self, runner_sprint, fielder_arm_str, fielder_arm_acc, hit_location, target_base, is_hit_and_run, runner_traits)

    def resolve_tag_up(self, runner_sprint, fielder_arm_str, distance, target_base, hit_location, runner_traits=None):
        """Pass-through to engine_baserunning to prevent import breaks in flow_half_inning.py"""
        return engine_baseRunning.resolve_tag_up(self, runner_sprint, fielder_arm_str, distance, target_base, hit_location, runner_traits)