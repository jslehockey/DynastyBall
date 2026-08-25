# ==========================================
# model_team.py
# ==========================================
# Manages rosters, active lineups, pitching rotations,
# and game-level team states for the engine loop.
# ==========================================
from model_stadium import Stadium
from extensions import db
# NOTE: Depending on your engine setup, you may also need:
# from model_player import Player 

class Team:
    def __init__(self, name, lineup, pitcher, defense, stadium=None, hook_threshold=5.0, adrenaline_trigger=True):
        # --- IDENTITY & PERSONNEL ---
        self.name = name
        self.lineup = lineup
        self.pitcher = pitcher
        self.defense = defense
        
        # --- STADIUM COMPOSITION ---
        # If the Exporter provides a stadium, use it. If not, build a default one automatically.
        self.stadium = stadium if stadium else Stadium(name=f"{self.name} Stadium")
        
        # --- GAME STATE (ENGINE LOOP) ---
        # Tracks current at-bats and pitching changes during the simulation while-loop
        self.batter_index = 0
        self.hook_threshold = hook_threshold 
        self.adrenaline_trigger = adrenaline_trigger
        
        self.bullpen = [] 
        self.used_pitchers = [] 
        self.game_pitchers = [pitcher] 
        self.linescore = []
        
        # --- LIVE GAME STATS ---
        self.stats = {
            "batting": {
                "PA": 0, "AB": 0, "R": 0, "H": 0, 
                "1B": 0, "2B": 0, "3B": 0, "HR": 0,
                "RBI": 0, "BB": 0, "HBP": 0, "K": 0
            },
            "pitching": {
                "Outs": 0, "H": 0, "R": 0, "ER": 0, "HR": 0,
                "BB": 0, "HBP": 0, "K": 0, "W": 0,
                "L": 0, "HLD": 0, "BS": 0, "SV": 0, "Pitches": 0
            },
            "defense": {
                "PO": 0, "A": 0, "E": 0, "TC": 0
            }
        }

    # ==========================================
    # ENGINE LOOP HELPERS
    # ==========================================
    def get_next_batter(self):
        """Advances the lineup order and returns the active batter."""
        batter = self.lineup[self.batter_index]
        self.batter_index = (self.batter_index + 1) % len(self.lineup)
        return batter

# --- DATABASE MODELS ---

class TeamDB(db.Model):
    __tablename__ = 'teams'
    team_id = db.Column(db.Integer, primary_key=True)
    world_id = db.Column(db.Integer, db.ForeignKey('worlds.world_id'), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(100), nullable=False)
    manager = db.Column(db.String(100))
    status = db.Column(db.String(20))
    user_email = db.Column(db.String(120), unique=True, nullable=True)
    user_pw = db.Column(db.String(255))
    sub_status = db.Column(db.Integer, default=0)
    color_primary = db.Column(db.String(7))
    color_secondary = db.Column(db.String(7))
    prestige = db.Column(db.Integer, default=0)

class TeamFinancials(db.Model):
    __tablename__ = 'team_financials'
    financial_id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    season = db.Column(db.Integer, nullable=False)
    balance = db.Column(db.Integer, default=0)
    players_on_contract = db.Column(db.Integer, default=0)
    cost_players = db.Column(db.Integer, default=0)
    income_fa_cup = db.Column(db.Integer, default=0)
    income_media = db.Column(db.Integer, default=0)
    income_adwatch = db.Column(db.Integer, default=0)
    income_attendance = db.Column(db.Integer, default=0)