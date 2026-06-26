def calculate_match_attendance(stadium_capacity, actual_ticket_price, home_tier, away_tier, 
                               match_type, team_prestige, current_win_pct, 
                               opponent_prestige, opponent_win_pct, active_superstars):

    # Calculates the exact fan attendance and revenue for a single home game.
    # 1. Base Prices by Tier (What an average team charges to fill the stadium)
    tier_base_prices = {1: 45.00, 2: 30.00, 3: 20.00, 4: 12.00, 5: 8.00}
    base_price = tier_base_prices.get(home_tier, 8.00)

    # 2. Match Type & "Giant Killing" Multipliers
    if "FA_Cup" in match_type:
        # Default FA Cup interest
        if match_type == "FA_Cup_Early":
            match_mult = 0.8  # Default: early cup games draw less interest
        elif match_type == "FA_Cup_Late":
            match_mult = 1.3
        else: # FA_Cup_Final
            match_mult = 2.0
            
        # THE MAGIC OF THE CUP: Underdog hosting a bigger club
        if home_tier > away_tier: 
            tier_difference = home_tier - away_tier
            # Add a massive 40% bump to demand for every tier of difference
            giant_killing_bonus = tier_difference * 0.4
            match_mult += giant_killing_bonus
            
    else:
        # Regular Season or Standard Playoffs
        match_multipliers = {"Regular": 1.0, "Playoffs": 1.5}
        match_mult = match_multipliers.get(match_type, 1.0)

    # 3. Calculate Demand Factors
    # Prestige adds up to a 50% bump (100 / 200 = 0.5)
    prestige_factor = team_prestige / 200.0 
    
    # Winning adds up to a 50% bump
    form_factor = current_win_pct / 2.0 
    
    # Playing a great opponent adds up to a 20% bump
    opponent_factor = ((opponent_prestige * 0.6) + (opponent_win_pct * 100 * 0.4)) / 500.0
    
    # Superstars draw crowds (flat $2 bump per 90+ OVR player on either team)
    superstar_premium = active_superstars * 2.0

    # 4. Final Optimal Price Calculation
    optimal_price = (base_price * match_mult) * (1.0 + prestige_factor + form_factor + opponent_factor)
    optimal_price += superstar_premium

    # 5. The Elasticity Curve (Punishing Greed)
    if actual_ticket_price <= optimal_price:
        # It's a deal! The stadium sells out.
        attendance_pct = 1.0
    else:
        # Manager is overcharging. Exponential drop-off in fans.
        # Elasticity of 2.5 means a 25% price hike drops attendance by ~43%
        price_ratio = optimal_price / actual_ticket_price
        attendance_pct = price_ratio ** 2.5

    # 6. Final Tally (Cap at stadium maximum)
    raw_attendance = int(stadium_capacity * attendance_pct)
    final_attendance = min(stadium_capacity, max(100, raw_attendance)) # At least 100 people show up
    game_revenue = final_attendance * actual_ticket_price

    return {
        "optimal_price": round(optimal_price, 2),
        "actual_price": actual_ticket_price,
        "attendance": final_attendance,
        "attendance_pct": round(attendance_pct * 100, 1),
        "game_revenue": game_revenue
    }