# ==========================================
# model_stadium.py
# ==========================================
# Handles all physical park dimensions, wall heights, 
# and environmental factors for the simulation.
# ==========================================
from extensions import db

DEFAULT_DIMENSIONS = {
    "Left Field Line": 340, 
    "Dead Left Field": 360, 
    "Left Center Gap": 380,
    "Dead Center": 400, 
    "Right Center Gap": 380, 
    "Dead Right Field": 360, 
    "Right Field Line": 340
}

class Stadium:
    def __init__(self, name="Generic Park", custom_dimensions=None, custom_heights=None):
        self.name = name
        self.dimensions = DEFAULT_DIMENSIONS.copy()
        
        # --- PARK DIMENSIONS & PHYSICS ---
        # Default all wall heights to a standard 10 feet
        self.heights = {sector: 10 for sector in DEFAULT_DIMENSIONS.keys()}
        
        # Process Custom Dimensions
        if custom_dimensions and isinstance(custom_dimensions, dict):
            for sector, distance in custom_dimensions.items():
                if distance and int(distance) > 0:
                    self.dimensions[sector] = int(distance)
                    
        # Process Custom Heights
        if custom_heights and isinstance(custom_heights, dict):
            for sector, height in custom_heights.items():
                if height and int(height) > 0:
                    self.heights[sector] = int(height)

# --- DATABASE MODELS ---

class Park(db.Model):
    __tablename__ = 'parks'
    park_id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    seasons_played = db.Column(db.Integer, default=0)
    record_w = db.Column(db.Integer, default=0)
    record_l = db.Column(db.Integer, default=0)
    population = db.Column(db.Integer)
    # Dimensions (Distance and Wall Height)
    dim_lf_line = db.Column(db.Integer)
    dim_lf_height = db.Column(db.Integer)
    dim_dead_lf = db.Column(db.Integer)
    dim_dead_lf_height = db.Column(db.Integer)
    dim_lc_gap = db.Column(db.Integer)
    dim_lc_height = db.Column(db.Integer)
    dim_dead_center = db.Column(db.Integer)
    dim_dead_center_height = db.Column(db.Integer)
    dim_rc_gap = db.Column(db.Integer)
    dim_rc_height = db.Column(db.Integer)
    dim_dead_rf = db.Column(db.Integer)
    dim_dead_rf_height = db.Column(db.Integer)
    dim_rf_line = db.Column(db.Integer)
    dim_rf_height = db.Column(db.Integer)