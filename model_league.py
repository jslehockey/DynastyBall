# ==========================================
# model_league.py
# ==========================================
# Manages macro-level league environments, era modifiers, 
# and seasonal statistical shifts.
# ==========================================
import random

class LeagueEnvironment:
    def __init__(self, power=1.0, contact=1.0, speed=1.0, pitching=1.0, defense=1.0, max_shift=0.015):
        # --- ERA MODIFIERS ---
        self.era_modifiers = {
            "power": power,     
            "contact": contact,   
            "speed": speed,     
            "pitching": pitching,
            "defense": defense
        }
        self.bounds = {
            "power": (0.93, 1.07),
            "contact": (0.93, 1.07),
            "speed": (0.93, 1.07),
            "pitching": (0.93, 1.07),
            "defense": (0.96, 1.05)
        }
        self.max_shift = max_shift

    def advance_season(self):
        # --- YEARLY EVOLUTION ---
        for axis in self.era_modifiers:
            shift = random.uniform(-self.max_shift, self.max_shift)
            new_value = self.era_modifiers[axis] + shift
            floor, ceiling = self.bounds[axis]
            self.era_modifiers[axis] = max(floor, min(ceiling, new_value))