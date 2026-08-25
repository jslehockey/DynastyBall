# ==========================================
# model_bid.py
# ==========================================
# A strict data container representing contract 
# offers submitted to players during free agency.
# ==========================================
from extensions import db

class Bid:
    def __init__(self, team_id, team_tier, duration, yearly_value, is_former_team=False, competition_ovr=0):
        # --- CORE FINANCIALS ---
        self.team_id = team_id
        self.team_tier = team_tier
        self.duration = duration
        self.yearly_value = yearly_value
        self.total_value = duration * yearly_value
        
        # --- NEGOTIATION CONTEXT ---
        # Used to interact with player behavioral traits (e.g., Loyalty, PlayingTime)
        self.is_former_team = is_former_team  
        self.competition_ovr = competition_ovr

# --- DATABASE MODELS ---

class Contract(db.Model):
    __tablename__ = 'contracts'
    contract_id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players_base.player_id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    year_start = db.Column(db.Integer, nullable=False)
    year_end = db.Column(db.Integer, nullable=False)
    cost_per_season = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20)) # e.g., "Active", "Expired", "Waived"

class FABid(db.Model):
    __tablename__ = 'fa_bids'
    bid_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Removed the db.ForeignKey() from these two lines
    player_id = db.Column(db.Integer, nullable=False)
    team_id = db.Column(db.Integer, nullable=False)
    
    season = db.Column(db.Integer, nullable=False)
    years = db.Column(db.Integer, nullable=False)
    salary = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    decision_day = db.Column(db.Integer)