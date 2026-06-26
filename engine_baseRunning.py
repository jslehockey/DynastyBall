# ==========================================
# engine_baseRunning.py
# ==========================================
# Resolves all baserunning decisions and outcomes, 
# including pre-pitch steals and in-play extra bases.
# ==========================================
import random

# ==========================================
# PRE-PITCH BASERUNNING (STEALS)
# ==========================================
def should_attempt_steal(r_sprint, r_instincts, target_base, manager_slider=3, speed_threshold=0, runner_traits=None):
    """
    Blends player instinct (speed + instincts curve) with managerial philosophy.
    """
    # --- SPEED DEMON TRAIT ---
    if runner_traits and "Speed Demon" in runner_traits:
        r_sprint += 7
        
    runner_jump = (r_sprint * 0.7) + (r_instincts * 0.3)
    speed_factor = (runner_jump / 100.0) ** 4 
    
    if target_base == 2:
        max_intent = 0.15 
    elif target_base == 3:
        max_intent = 0.05 
    else:
        return False
        
    base_prob = max_intent * speed_factor
    
    threshold_modifier = 1.0
    if speed_threshold > 0:
        if runner_jump >= speed_threshold:
            threshold_modifier = 1.2  
        else:
            threshold_modifier = 0.1  

    if manager_slider == 1: aggression_multiplier = 0.25
    elif manager_slider == 2: aggression_multiplier = 0.50
    elif manager_slider == 3: aggression_multiplier = 1.00
    elif manager_slider == 4: aggression_multiplier = 1.50
    elif manager_slider >= 5: aggression_multiplier = 2.00
    else: aggression_multiplier = 1.00

    adjusted_prob = base_prob * threshold_modifier * aggression_multiplier
    
    rng_factor = random.gauss(0, 0.005)
    final_prob = max(0.001, min(0.99, adjusted_prob + rng_factor))
    
    return random.random() < final_prob

def calculate_steal_success(r_sprint, r_instincts, c_arm_str, c_arm_acc, c_reaction, target_base, runner_traits=None):
    """
    Determines the outcome of a stolen base attempt using granular sub-stats.
    """
    # --- SPEED DEMON TRAIT ---
    if runner_traits and "Speed Demon" in runner_traits:
        r_sprint += 7

    # 1. Establish the baseline success rate (Modern MLB averages)
    if target_base == 2:
        baseline_prob = 0.65  
    elif target_base == 3:
        baseline_prob = 0.53  
    else:
        return False 
        
    # 2. Blend the sub-stats
    runner_jump = (r_sprint * 0.7) + (r_instincts * 0.3)
    catcher_pop = (c_arm_str * 0.5) + (c_reaction * 0.3) + (c_arm_acc * 0.2)
    
    # 3. Calculate stat differential
    stat_diff = runner_jump - catcher_pop
    
    k = 0.015 
    adjusted_prob = baseline_prob + (stat_diff * k)
    
    rng_factor = random.gauss(0, 0.05)
    final_prob = max(0.01, min(0.99, adjusted_prob + rng_factor))
    
    return random.random() < final_prob

# ==========================================
# IN-PLAY BASERUNNING (TAG-UPS & EXTRA BASES)
# ==========================================
def resolve_extra_base_attempt(sim, runner_sprint, fielder_arm_str, fielder_arm_acc, hit_location, target_base, is_hit_and_run=False, runner_traits=None):
    """
    Determines if a runner safely stretches a hit into an extra base.
    """
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

def resolve_tag_up(sim, runner_sprint, fielder_arm_str, distance, target_base, hit_location, runner_traits=None):
    """
    Determines if a runner successfully tags up on a caught fly ball.
    """
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