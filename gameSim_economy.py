# ==========================================
# gameSim_economy.py
# ==========================================
# Handles ticket pricing, attendance generation, 
# and homefield advantage modifiers.
# ==========================================

def calculate_match_attendance(capacity, actual_price, home_tier, away_tier, 
                               match_type, home_prestige, home_win_pct, 
                               away_prestige, away_win_pct, active_superstars):
    
    tier_base_prices = {1: 45.00, 2: 30.00, 3: 20.00, 4: 12.00, 5: 8.00}
    base_price = tier_base_prices.get(home_tier, 8.00)

    # Match Type & "Giant Killing" Multipliers
    if "FA_Cup" in match_type:
        if match_type == "FA_Cup_Early": match_mult = 0.8
        elif match_type == "FA_Cup_Late": match_mult = 1.3
        else: match_mult = 2.0
            
        if home_tier > away_tier: 
            match_mult += ((home_tier - away_tier) * 0.4)
    else:
        match_mult = 1.5 if match_type == "Playoffs" else 1.0

    # Demand Factors
    prestige_factor = home_prestige / 200.0 
    form_factor = home_win_pct / 2.0 
    opponent_factor = ((away_prestige * 0.6) + (away_win_pct * 100 * 0.4)) / 500.0
    superstar_premium = active_superstars * 2.0

    optimal_price = (base_price * match_mult) * (1.0 + prestige_factor + form_factor + opponent_factor) + superstar_premium

    # Elasticity Curve
    if actual_price <= optimal_price:
        attendance_pct = 1.0
    else:
        attendance_pct = (optimal_price / actual_price) ** 2.5

    raw_attendance = int(capacity * attendance_pct)
    final_attendance = min(capacity, max(100, raw_attendance))
    game_revenue = final_attendance * actual_price

    return {
        "optimal_price": round(optimal_price, 2),
        "actual_price": actual_price,
        "attendance": final_attendance,
        "attendance_pct": round(attendance_pct * 100, 1),
        "game_revenue": game_revenue
    }

def get_homefield_modifiers(attendance):
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