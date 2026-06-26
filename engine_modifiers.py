# ==========================================
# engine_modifiers.py
# ==========================================
# Isolates standalone modifiers, homefield advantage, 
# and situational trait boosts.
# ==========================================

def get_homefield_modifiers(attendance):
    """
    Translates raw attendance into temporary in-game stat modifiers.
    Returns a dictionary of buffs and debuffs to apply during the game.
    """
    modifiers = {
        "atmosphere": "Quiet",
        "home_hitter": {"bat_speed": 0, "timing": 0, "eye": 0},
        "home_pitcher": {"arm_speed": 0, "spin_rate": 0}, 
        "away_hitter": {"eye": 0, "restraint": 0},        
        "away_pitcher": {"command": 0, "accuracy": 0}
    }
    
    if attendance >= 45000:
        modifiers["atmosphere"] = "Deafening"
        modifiers["home_hitter"] = {"bat_speed": 2, "timing": 2, "eye": 1}
        modifiers["home_pitcher"] = {"arm_speed": 1, "spin_rate": 1}
        modifiers["away_hitter"] = {"eye": -2, "restraint": -1}
        modifiers["away_pitcher"] = {"command": -2, "accuracy": -2}
        
    elif attendance >= 30000:
        modifiers["atmosphere"] = "Electric"
        modifiers["home_hitter"] = {"bat_speed": 1, "timing": 1, "eye": 0}
        modifiers["home_pitcher"] = {"arm_speed": 1, "spin_rate": 0}
        modifiers["away_hitter"] = {"eye": -1, "restraint": -1}
        modifiers["away_pitcher"] = {"command": -1, "accuracy": -1}
        
    elif attendance >= 15000:
        modifiers["atmosphere"] = "Loud"
        modifiers["away_pitcher"] = {"command": -1, "accuracy": 0}
        modifiers["away_hitter"] = {"eye": -1, "restraint": 0}
        
    else:
        modifiers["atmosphere"] = "Neutral"
        
    return modifiers

def apply_trait_modifiers(sim, attr_name, value, is_pitcher):
    """
    Applies situational trait boosts dynamically.
    Takes the AtBatSimulator instance (`sim`) to read the game state.
    """
    target = sim.pitcher if is_pitcher else sim.batter
    traits = getattr(target, 'traits', [])
    
    if is_pitcher:
        if "Escape Artist" in traits and sim.half_inning and any(sim.half_inning.bases[b] for b in [2, 3]):
            if attr_name in ["accuracy", "bite"]: value += 6
        if "Putaway Pitcher" in traits and sim.strikes == 2:
            if attr_name in ["arm_speed", "deception"]: value += 6
        if "Lights Out" in traits and sim.half_inning and sim.half_inning.inning_num >= 8:
            run_diff = abs(sim.half_inning.batting_team.stats["batting"]["R"] - sim.half_inning.fielding_team.stats["batting"]["R"])
            if run_diff <= 3: value += 4
    else:
        if "Clutch" in traits and sim.half_inning and any(sim.half_inning.bases[b] for b in [1, 2, 3]):
            if attr_name in ["timing", "strength"]: value += 6
        if "Table Setter" in traits and sim.half_inning and sim.half_inning.outs == 0:
            if attr_name in ["eye", "restraint"]: value += 7
        if "First Pitch Killer" in traits and sim.balls == 0 and sim.strikes == 0:
            if attr_name in ["barreling", "bat_speed"]: value += 7
            elif attr_name == "restraint": value -= 7
            
    return value