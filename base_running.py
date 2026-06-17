import random

def calculate_steal_success(runner_speed, catcher_defense, target_base):
    """
    Determines the outcome of a stolen base attempt.
    Returns True if safe, False if out.
    """
    # 1. Establish the baseline success rate
    if target_base == 2:
        baseline_prob = 0.40  # 40% success for 2nd base at even stats
    elif target_base == 3:
        baseline_prob = 0.25  # 25% success for 3rd base at even stats
    else:
        # Failsafe if anything else is passed
        return False 
        
    # 2. Calculate the stat differential
    stat_diff = runner_speed - catcher_defense
    
    # 3. Apply the differential to the probability
    # k = 0.015 means a 1.5% shift in probability per rating point difference
    k = 0.015 
    adjusted_prob = baseline_prob + (stat_diff * k)
    
    # 4. Inject RNG (Gaussian Noise) to simulate the "jump" or a bad throw
    # Mean of 0, standard deviation of 0.05 (roughly a +/- 5% random swing)
    rng_factor = random.gauss(0, 0.05)
    final_prob = adjusted_prob + rng_factor
    
    # 5. Cap the probabilities so they never exceed 99% or drop below 1%
    final_prob = max(0.01, min(0.99, final_prob))
    
    # 6. Roll the dice
    roll = random.random()
    
    return roll < final_prob

def should_attempt_steal(runner_speed, target_base, manager_slider=3, speed_threshold=0):
    """
    Blends player instinct (speed curve) with managerial philosophy.
    manager_slider: 1 (Very Conservative) to 5 (Very Aggressive). 3 is Neutral.
    speed_threshold: If > 0, drastically reduces intent for slower players.
    """
    # ==========================================
    # 1. PLAYER INSTINCT (The Default Engine)
    # ==========================================
    speed_factor = (runner_speed / 100.0) ** 4 
    
    if target_base == 2:
        max_intent = 0.15  # Up to 15% chance to run PER PITCH
    elif target_base == 3:
        max_intent = 0.05  # Up to 5% chance to run PER PITCH
    else:
        return False
        
    base_prob = max_intent * speed_factor
    
    # ==========================================
    # 2. MANAGERIAL GUARDRAILS
    # ==========================================
    # A. The Threshold Check
    threshold_modifier = 1.0
    if speed_threshold > 0:
        if runner_speed >= speed_threshold:
            threshold_modifier = 1.2  # Green light! Slight boost to instinct.
        else:
            threshold_modifier = 0.1  # Red light! Manager holds them back (90% penalty).

    # B. The Aggression Slider
    # 3 is Neutral (1.0x), meaning the manager lets the player's instinct run the show.
    if manager_slider == 1: aggression_multiplier = 0.25
    elif manager_slider == 2: aggression_multiplier = 0.50
    elif manager_slider == 3: aggression_multiplier = 1.00
    elif manager_slider == 4: aggression_multiplier = 1.50
    elif manager_slider >= 5: aggression_multiplier = 2.00
    else: aggression_multiplier = 1.00

    # ==========================================
    # 3. FINAL EXECUTION
    # ==========================================
    adjusted_prob = base_prob * threshold_modifier * aggression_multiplier
    
    # Inject RNG to keep it unpredictable
    rng_factor = random.gauss(0, 0.005)
    final_prob = adjusted_prob + rng_factor
    
    # Cap bounds to prevent weird math anomalies
    final_prob = max(0.001, min(0.99, final_prob))
    
    return random.random() < final_prob