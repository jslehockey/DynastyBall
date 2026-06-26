# ==========================================
# model_team.py
# ==========================================
# Manages rosters, active lineups, pitching rotations,
# and game-level team states for the engine loop.
# ==========================================
from model_stadium import Stadium
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