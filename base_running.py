import random

def calculate_steal_success(r_sprint, r_instincts, c_arm_str, c_arm_acc, c_reaction, target_base):
    """
    Determines the outcome of a stolen base attempt using granular sub-stats.
    """
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

def should_attempt_steal(r_sprint, r_instincts, target_base, manager_slider=3, speed_threshold=0):
    """
    Blends player instinct (speed + instincts curve) with managerial philosophy.
    """
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