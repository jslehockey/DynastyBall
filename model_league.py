# ==========================================
# model_league.py
# ==========================================
# Manages macro-level league environments, era modifiers, 
# and seasonal statistical shifts.
# ==========================================
import random
from extensions import db

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

# --- DATABASE MODELS ---

class World(db.Model):
    __tablename__ = 'worlds'
    world_id = db.Column(db.Integer, primary_key=True)
    world_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class SeasonResult(db.Model):
    __tablename__ = 'season_results'
    game_id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    competition = db.Column(db.String(50))
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    away_score = db.Column(db.Integer, default=0)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    home_score = db.Column(db.Integer, default=0)