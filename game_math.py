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
    "C":  {"C": 1.00, "1B": 0.85, "2B": 0.55, "3B": 0.80, "SS": 0.55, "LF": 0.70, "CF": 0.55, "RF": 0.55},
    "1B": {"C": 0.45, "1B": 1.00, "2B": 0.65, "3B": 0.65, "SS": 0.55, "LF": 0.70, "CF": 0.60, "RF": 0.60},
    "2B": {"C": 0.45, "1B": 0.92, "2B": 1.00, "3B": 0.90, "SS": 0.77, "LF": 0.80, "CF": 0.65, "RF": 0.70},
    "3B": {"C": 0.45, "1B": 0.92, "2B": 0.90, "3B": 1.00, "SS": 0.77, "LF": 0.80, "CF": 0.65, "RF": 0.70},
    "SS": {"C": 0.45, "1B": 0.92, "2B": 0.95, "3B": 0.95, "SS": 1.00, "LF": 0.80, "CF": 0.70, "RF": 0.80},
    "LF": {"C": 0.45, "1B": 0.85, "2B": 0.75, "3B": 0.75, "SS": 0.60, "LF": 1.00, "CF": 0.85, "RF": 0.95},
    "CF": {"C": 0.45, "1B": 0.85, "2B": 0.80, "3B": 0.75, "SS": 0.77, "LF": 0.97, "CF": 1.00, "RF": 0.95},
    "RF": {"C": 0.45, "1B": 0.85, "2B": 0.70, "3B": 0.75, "SS": 0.82, "LF": 0.94, "CF": 0.85, "RF": 1.00},
    "P":  {"C": 0.20, "1B": 0.91, "2B": 0.25, "3B": 0.20, "SS": 0.10, "LF": 0.20, "CF": 0.10, "RF": 0.20}
}