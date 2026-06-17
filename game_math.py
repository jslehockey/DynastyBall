# game_math.py

def compress_rating(rating):
    """Normalizes player ratings around 75 to prevent extreme blowouts."""
    if rating >= 75:
        return 75 + ((rating - 75) * 0.40)
    else:
        return 75 - ((75 - rating) * 0.40)

def calculate_advantage_ratio(power, movement):
    """Calculates the matchup advantage for the hitter."""
    adj_power = compress_rating(power)
    adj_movement = compress_rating(movement)
    # The '10' is your pitching bias constant
    return adj_power / (adj_movement + 10)