# ==========================================
# engine_defense.py
# ==========================================
# Resolves complex defensive logic, including robs, 
# diving plays, errors, and infield relays/double plays.
# ==========================================
import random
from game_math import OOP_MATRIX

def resolve_defense(sim, hit_data, defense):
    position = hit_data["target_position"]
    
    def get_fielder_arm(pos):
        fld = defense.get(pos)
        if fld and hasattr(fld, 'defense'):
            return fld.defense.get('arm_str', 75), fld.defense.get('arm_acc', 75)
        return 75, 75

    # --- ROBBED HOME RUN LOGIC ---
    if hit_data["hit_type"] == "Home Run":
        if hit_data.get("rob_opportunity"):
            pos_map = {"Left Field Line": "LF", "Dead Left Field": "LF", "Left Center Gap": "CF", "Dead Center": "CF", "Right Center Gap": "CF", "Dead Right Field": "RF", "Right Field Line": "RF"}
            of_pos = pos_map.get(hit_data["location"], "CF")
            fielder = defense.get(of_pos)
            
            f_glove = 75; f_sprint = 75; f_react = 75
            if fielder and hasattr(fielder, 'defense'):
                f_glove = fielder.defense.get('glove', 75)
                f_react = fielder.defense.get('reaction', 75)
                f_sprint = fielder.attributes.get('baserunning', {}).get('sprint_speed', 75) 
            
            rob_prob = (f_glove * 0.4) + (f_react * 0.3) + (f_sprint * 0.3) - 40 
            rob_prob = max(1.0, min(rob_prob, 35.0)) 
            
            if sim.weather.get("precipitation") == "Rain":
                rob_prob *= 0.50 
                
            if random.uniform(0, 100) <= rob_prob:
                return {
                    "fielder_state": "caught_in_air", "out_recorded_on_catch": True,
                    "reason": f"ROBBED! {of_pos} times the leap perfectly at the {hit_data['wall_height']}-foot wall and brings it back! Unbelievable catch!"
                }
            else:
                return {
                    "fielder_state": "home_run", "out_recorded_on_catch": False,
                    "reason": f"HOME RUN! {of_pos} goes back, leaps... but it's just out of reach into the front row! ({hit_data['distance']}ft to {hit_data['location']})"
                }

        return {
            "fielder_state": "home_run", "out_recorded_on_catch": False, 
            "reason": f"HOME RUN! ({hit_data['distance']}ft to {hit_data['location']})"
        }

    # --- OFF THE WALL LOGIC ---
    if hit_data["hit_type"] == "Off the Wall":
        arm_str, arm_acc = get_fielder_arm(position)
        return {
            "fielder_state": "clean_hit_outfield", "out_recorded_on_catch": False,
            "fielder_arm_str": arm_str, "fielder_arm_acc": arm_acc,
            "reason": f"Hit! It smacks high off the {hit_data['wall_height']}-foot wall in {hit_data['location']} and bounces back!"
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

    def_mod = sim.env.get("defense", 1.0)
    f_reaction *= def_mod
    f_range *= def_mod
    f_sprint *= def_mod
    f_glove *= def_mod
    f_arm_str *= def_mod
    f_arm_acc *= def_mod

    effective_range = (f_reaction * 0.4) + (f_range * 0.6)
    effective_glove = max(50, min(100, f_glove)) 

    if hit_data["quality"] == "Crushed!": difficulty = 87 if hit_data["trajectory"] == "Player-Height Line Drive" else 81
    elif hit_data["quality"] == "Solid Contact": difficulty = 69
    else: difficulty = 45 if hit_data["trajectory"] == "Ground Ball" else 25 

    if hit_data["trajectory"] == "Ground Ball" and hit_data["location"] in ["Left Center Gap", "Right Center Gap"]:
        difficulty += 13

    range_roll = effective_range + sim.roll_rng()
    
    if range_roll < difficulty:
        miss_margin = difficulty - range_roll
        
        if 0 < miss_margin <= 15 and hit_data["trajectory"] != "Pop Up":
            dive_success_prob = max(5.0, (effective_glove * 0.6 + f_reaction * 0.4) - miss_margin)
            
            if random.uniform(0, 100) < dive_success_prob:
                if hit_data["trajectory"] == "Ground Ball" and position in ["1B", "2B", "3B", "SS"]:
                    return {
                        "fielder_state": "clean_gather_infield", "out_recorded_on_catch": False, 
                        "fielder_arm_str": f_arm_str, "fielder_arm_acc": f_arm_acc, 
                        "reason": f"Spectacular diving stop by {position}! Quickly to their feet."
                    }
                else:
                    out_type = "Diving catch" if hit_data["trajectory"] in ["Fly Ball", "Player-Height Line Drive", "Over-Infield Line Drive"] else "Caught"
                    return {
                        "fielder_state": "caught_in_air", "out_recorded_on_catch": True,
                        "reason": f"Top play! {position} lays out and makes a {out_type.lower()} ({hit_data['distance']}ft)!"
                    }
            else:
                dive_error_prob = 4.25 * ((100 - effective_glove) / 50.0)
                if sim.weather.get("precipitation") == "Rain": dive_error_prob *= 1.20
                    
                if random.uniform(0, 100) < dive_error_prob:
                    return {
                        "fielder_state": "error", "out_recorded_on_catch": False, 
                        "reason": f"Error! {position} dives but it deflects off the glove in {hit_data['location']}."
                    }
                else:
                    if position in ["LF", "CF", "RF"]:
                        hit_data["distance"] = min(hit_data["distance"] + 60, 400) 
                        return {
                            "fielder_state": "clean_hit_outfield", "out_recorded_on_catch": False,
                            "reason": f"Hit! {position} dives and comes up empty. The ball rolls past them in {hit_data['location']}!"
                        }
                    else:
                        return {
                            "fielder_state": "past_infielder", "out_recorded_on_catch": False,
                            "reason": f"Hit! {position} lays out but it's just out of reach into the outfield."
                        }

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

    base_error_prob = 8.5 * ((100 - effective_glove) / 50.0) ** 1.25
    
    if hit_data["trajectory"] == "Player-Height Line Drive": error_prob = base_error_prob * 2.0  
    elif hit_data["trajectory"] in ["Fly Ball", "Pop Up"]: error_prob = base_error_prob * 0.2  
    else: error_prob = base_error_prob       

    if hit_data["quality"] == "Crushed!": error_prob *= 1.5 
    if is_sprinting_catch: error_prob += 3.5 
    
    if sim.weather.get("precipitation") == "Rain":
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
            
def resolve_infield_throw(sim, hit_data, fielder_arm_str, fielder_arm_acc, batter_sprint, position):
    bases, outs, inning = sim.half_inning.bases, sim.half_inning.outs, sim.half_inning.inning_num
    distance, quality = hit_data["distance"], hit_data.get("quality", "Weak Contact")
    
    run_diff = abs(sim.half_inning.batting_team.stats["batting"]["R"] - sim.half_inning.fielding_team.stats["batting"]["R"])
    is_late_game_pressure = inning >= 9 and run_diff <= 2
    initial_bobble = random.uniform(0, 100) < 6.0 
    
    force_at_2b = bases[1] is not None
    force_at_3b = force_at_2b and bases[2] is not None
    force_at_home = force_at_3b and bases[3] is not None

    target_base, is_force, attempt_dp = 1, True, False
    target_runner, runner_held, play_profile = sim.batter, False, "Standard"

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
            if position in ["SS", "3B"] and distance < 100: runner_held, target_base, target_runner, play_profile = True, 1, sim.batter, "Runner held"
            else: target_base = 1

    runner_speed = target_runner.attributes.get('baserunning', {}).get('sprint_speed', 75) if target_runner != sim.batter else batter_sprint
    if target_runner != sim.batter and "Speed Demon" in getattr(target_runner, 'traits', []):
        runner_speed += 7

    effective_arm_acc = max(50, min(100, fielder_arm_acc))
    throw_error_prob = 8.5 * ((100 - effective_arm_acc) / 50.0) ** 1.25
    
    if distance > 110: throw_error_prob *= 1.5 
    elif distance < 70: throw_error_prob *= 0.5 

    if random.uniform(0, 100) < throw_error_prob:
        base_str = "Home" if target_base == 4 else f"{target_base}B"
        return {
            "safe": True, "error": True, "double_play": False, "target_base": target_base,
            "reason": f"Throwing Error! {position} sailed the throw to {base_str}."
        }

    distance_advantage = (distance - 90) * 0.4 
    runner_score = runner_speed + distance_advantage + sim.roll_rng()
    
    base_throw_advantage = 25 
    tag_penalty = 0 if is_force else 15 
    fielder_throw_score = fielder_arm_str + base_throw_advantage - tag_penalty + sim.roll_rng()
    
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
                batter_run_score = batter_sprint + sim.roll_rng() + pivot_tax
                relay_arm_score = fielder_arm_str + base_throw_advantage + sim.roll_rng() 
                
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