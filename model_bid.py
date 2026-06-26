# ==========================================
# model_bid.py
# ==========================================
# A strict data container representing contract 
# offers submitted to players during free agency.
# ==========================================

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