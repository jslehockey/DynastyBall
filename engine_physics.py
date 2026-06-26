# ==========================================
# engine_physics.py
# ==========================================
# Handles hit quality, spray charts, trajectories, 
# distance calculations, and bunting logic.
# ==========================================
import random

def simulate_bunt_attempt(sim, allow_2_strike_bunt=False):
    # NOTE: Relies on sim.ab_control, sim.ab_contact, etc., being calculated in the main engine
    zone_prob = 48.0 * (getattr(sim, 'ab_control', 50) / 75.0)
    in_zone = random.uniform(0, 100) <= zone_prob
    swing_prob = 85.0 if in_zone else 45.0
    
    if random.uniform(0, 100) > swing_prob:
        return {"result": "Strike" if in_zone else "Ball", "details": f"Bunt attempt pulled back, {'pitch was in the zone' if in_zone else 'ball in the dirt'}."}

    contact_prob = 90.0 * (getattr(sim, 'ab_contact', 50) / max(1, getattr(sim, 'ab_velocity', 50)))
    if random.uniform(0, 100) > contact_prob:
        return {"result": "Strike", "details": "Swung right through the bunt attempt!"}

    in_play_prob = 65.0 * (getattr(sim, 'ab_contact', 50) / max(1, getattr(sim, 'ab_movement', 50))) 
    if random.uniform(0, 100) > in_play_prob:
        if sim.strikes == 2: return {"result": "Strikeout", "details": "Bunted foul with two strikes!"}
        return {"result": "Foul", "details": "Bunted foul into the backstop."}

    return {"result": "In Play", "details": "Hit Quality: Bunt"}

def calculate_hit_location(sim, hit_quality, strength, timing, arm_speed, spin):
    pitcher_timing = arm_speed + (spin * 0.5) + sim.roll_rng()
    batter_timing = timing + (strength * 0.5) + sim.roll_rng()
    margin = batter_timing - pitcher_timing
    
    if margin >= 5: timing_tendency = "Pull"
    elif margin <= -5: timing_tendency = "Oppo"
    else: timing_tendency = "Center"

    spray_charts = {
        "Pull":   [15, 25, 35, 15, 7, 2, 1],
        "Oppo":   [1, 2, 7, 15, 35, 25, 15],
        "Center": [4, 10, 16, 40, 16, 10, 4]
    }

    batter_handedness = sim.batter.attributes.get('bats', 'R')
    if batter_handedness == 'L':
        if timing_tendency == "Pull": weights = spray_charts["Oppo"]
        elif timing_tendency == "Oppo": weights = spray_charts["Pull"]
        else: weights = spray_charts["Center"]
    else:
        weights = spray_charts[timing_tendency]

    locations = ["Left Field Line", "Dead Left Field", "Left Center Gap", "Dead Center", "Right Center Gap", "Dead Right Field", "Right Field Line"]
    final_location = random.choices(locations, weights=weights, k=1)[0]

    # --- DYNAMIC STADIUM DIMENSIONS & HEIGHTS HOOKUP ---
    if sim.half_inning:
        home_team = sim.half_inning.batting_team if sim.is_home_batting else sim.half_inning.fielding_team
        park_dimensions = getattr(home_team.stadium, 'dimensions', {loc: 330 for loc in locations})
        park_heights = getattr(home_team.stadium, 'heights', {loc: 10 for loc in locations})
    else:
        park_dimensions = {
            "Left Field Line": 340, "Dead Left Field": 360, "Left Center Gap": 380,
            "Dead Center": 400, "Right Center Gap": 380, "Dead Right Field": 360, "Right Field Line": 340
        }
        park_heights = {loc: 10 for loc in locations}
    
    wall_distance = park_dimensions[final_location]
    wall_height = park_heights[final_location]
    elev = sim.ab_elevation

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

    if "Groundball Guru" in getattr(sim.pitcher, 'traits', []) and trajectory in ["Over-Infield Line Drive", "Player-Height Line Drive"]:
        if random.uniform(0, 100) <= 10.0:
            trajectory = "Ground Ball"
            power_transfer = 0.40
            
    if "Launch Angle God" in getattr(sim.batter, 'traits', []) and trajectory == "Ground Ball":
        if random.uniform(0, 100) <= 10.0:
            trajectory = random.choice(["Player-Height Line Drive", "Fly Ball"])
            power_transfer = 0.75

    baseline_distance = (strength * 5.2) * power_transfer

    if trajectory == "Ground Ball": raw_distance = baseline_distance * random.uniform(0.05, 0.28) 
    elif trajectory == "Player-Height Line Drive": raw_distance = baseline_distance * random.uniform(0.3, 0.5)
    elif trajectory == "Pop Up": raw_distance = baseline_distance * random.uniform(0.1, 0.3)
    elif trajectory == "Over-Infield Line Drive": raw_distance = baseline_distance * random.uniform(0.6, 0.8)
    else: raw_distance = baseline_distance * random.uniform(0.85, 1.0)

    distance_with_variance = raw_distance + (sim.roll_rng() * 1.5)

    if trajectory in ["Fly Ball", "Over-Infield Line Drive"]:
        wind_effect = sim.weather.get("wind_speed", 0) * 0.8
        direction = sim.weather.get("wind_direction", "Calm")
        if direction == "Blowing In":
            distance_with_variance -= wind_effect
        elif direction == "Blowing Out":
            distance_with_variance += wind_effect

    final_distance = int(max(5, min(distance_with_variance, 515)))

    target_position, hit_type = None, "In Play"
    display_location = f"to {final_location}" 
    rob_opportunity = False

    # --- WALL HEIGHT PHYSICS AND ROB LOGIC ---
    if final_distance >= wall_distance and trajectory in ["Fly Ball", "Over-Infield Line Drive"]:
        clearance = final_distance - wall_distance
        
        required_clearance = (wall_height * 1.2) if trajectory == "Over-Infield Line Drive" else (wall_height * 0.4)
        
        if clearance < required_clearance:
            hit_type = "Off the Wall"
            display_location = f"off the {wall_height}-foot wall in {final_location}"
            
            if final_location in ["Left Field Line", "Dead Left Field", "Left Center Gap"]: target_position = "LF"
            elif final_location == "Dead Center": target_position = "CF"
            elif final_location in ["Right Center Gap", "Dead Right Field", "Right Field Line"]: target_position = "RF"
        else:
            if wall_height <= 15:
                if (trajectory == "Fly Ball" and clearance <= 4) or (trajectory == "Over-Infield Line Drive" and clearance <= 12):
                    rob_opportunity = True

            target_position = "Bleachers"
            hit_type = "Home Run"
            
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
        "target_position": target_position, "hit_type": hit_type, "wall_height": wall_height,
        "rob_opportunity": rob_opportunity
    }

def resolve_batter_hit_type(sim, hit_data, batter_sprint, fielder_arm_str):
    distance, location = hit_data["distance"], hit_data["location"]
    is_gap_or_line = location in ["Left Field Line", "Right Field Line", "Left Center Gap", "Right Center Gap"]
    
    if distance < 210: return "1B"
        
    if distance >= 300 and is_gap_or_line:
        if (batter_sprint + sim.roll_rng()) > (fielder_arm_str + 15 + sim.roll_rng()): return "3B"
        return "2B"
    elif distance >= 230 and is_gap_or_line:
        return "2B"
    elif distance >= 280 and not is_gap_or_line:
        if (batter_sprint + sim.roll_rng()) > (fielder_arm_str + 10 + sim.roll_rng()): return "2B"
        return "1B"
        
    return "1B"