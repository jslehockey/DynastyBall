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

OOP_MATRIX = {
    "C":  {"C": 1.00, "1B": 0.80, "2B": 0.40, "3B": 0.70, "SS": 0.30, "LF": 0.50, "CF": 0.30, "RF": 0.50},
    "1B": {"C": 0.25, "1B": 1.00, "2B": 0.50, "3B": 0.50, "SS": 0.30, "LF": 0.50, "CF": 0.30, "RF": 0.50},
    "2B": {"C": 0.25, "1B": 0.90, "2B": 1.00, "3B": 0.90, "SS": 0.70, "LF": 0.60, "CF": 0.50, "RF": 0.60},
    "3B": {"C": 0.25, "1B": 0.90, "2B": 0.90, "3B": 1.00, "SS": 0.70, "LF": 0.60, "CF": 0.50, "RF": 0.60},
    "SS": {"C": 0.25, "1B": 0.90, "2B": 0.95, "3B": 0.95, "SS": 1.00, "LF": 0.70, "CF": 0.60, "RF": 0.70},
    "LF": {"C": 0.25, "1B": 0.80, "2B": 0.50, "3B": 0.50, "SS": 0.40, "LF": 1.00, "CF": 0.75, "RF": 0.90},
    "CF": {"C": 0.25, "1B": 0.80, "2B": 0.60, "3B": 0.50, "SS": 0.50, "LF": 0.95, "CF": 1.00, "RF": 0.95},
    "RF": {"C": 0.25, "1B": 0.80, "2B": 0.50, "3B": 0.50, "SS": 0.40, "LF": 0.90, "CF": 0.75, "RF": 1.00},
    "P":  {"C": 0.20, "1B": 0.30, "2B": 0.20, "3B": 0.20, "SS": 0.10, "LF": 0.20, "CF": 0.10, "RF": 0.20}
}