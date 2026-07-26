# ==========================================
# model_player.py
# ==========================================
# Core entity class. Handles 1-99 attribute scales, 
# advanced sub-stats, career progression, and contract logic.
# ==========================================
import random
# NOTE: If type checking requires the Bid class, uncomment the line below:
# from model_bid import Bid

class Player:
    def __init__(self, player_id, name, attributes):
        # --- IDENTITY ---
        self.player_id = str(player_id)  # e.g., "000100000001"
        self.name = name
        
        # --- PREMIUM SCOUTING & SUB-STATS ---
        # Houses the detailed granular ratings visible primarily as a premium perk.
        self.attributes = attributes
        
        # --- DEVELOPMENT ARCHITECTURE ---
        dev_data = self.attributes.get('development', {})
        self.age = dev_data.get('age', 18)
        self.potential = dev_data.get('potential', 75)
        self.peak_age = dev_data.get('peak_age', 27)
        self.decline_rate = dev_data.get('decline_rate', 1.0)
        
        # --- CAREER STATUS ---
        self.seasons_in_fa = 0
        self.is_retired = False
        self.primary_pos = self.attributes.get('primary_pos', 'DH')
        self.game_pos = self.attributes.get('game_pos', 'DH')
        
        # --- STREAKS & MOMENTUM MEMORY ---
        self.current_hit_streak = int(self.attributes.get('current_hit_streak', 0))
        self.longest_hit_streak = int(self.attributes.get('longest_hit_streak', 0))
        
        self.current_obp_streak = int(self.attributes.get('current_obp_streak', 0))
        self.longest_obp_streak = int(self.attributes.get('longest_obp_streak', 0))
        
        self.current_scoreless_outs = int(self.attributes.get('current_scoreless_outs', 0))
        self.longest_scoreless_outs = int(self.attributes.get('longest_scoreless_outs', 0))
        
        self.recent_form_str = str(self.attributes.get('recent_form', ""))
        
        # --- RPG & BEHAVIORAL ELEMENTS ---
        self.traits = self.attributes.get('traits', [])
        self.form = self.calculate_form() # Dynamic -3 to +3 form modifier
        
        # --- FREE AGENCY STATE ---
        self.contract_trait = self.attributes.get('contract_trait', 'MoneyHungry')
        self.contract_length = self.attributes.get('contract_length', 1) 
        self.contract_salary = self.attributes.get('contract_salary', 750000)
        self.years_remaining = self.attributes.get('years_remaining', self.contract_length)
        
        self.next_decision_time = None
        self.offers = []

        # --- LIVE GAME STAT TRACKING ---
        self.stats = {
            "batting": {
                "PA": 0, "AB": 0, "R": 0, "H": 0, 
                "1B": 0, "2B": 0, "3B": 0, "HR": 0,
                "RBI": 0, "BB": 0, "HBP": 0, "K": 0,
                "SB": 0, "CS": 0,
                "SF": 0, "GIDP": 0
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
        
        self.total_outs_recorded = 0
        self.strikeouts = 0  
        self.hits_allowed = 0
        self.walks_allowed = 0
        self.runs_allowed = 0
        self.earned_runs = 0
        self.home_runs_allowed = 0

    # ==========================================
    # OVERALL RATING & FINANCES
    # ==========================================
    def get_ovr(self):
        """Calculates a rough Overall Rating (50-99) to determine market value."""
        if self.assigned_pos == "P":
            stats = self.attributes["pitching"]
            return int(sum([stats["arm_speed"], stats["deception"], stats["accuracy"], 
                            stats["command"], stats["spin_rate"], stats["bite"]]) / 6)
        else:
            stats = self.attributes["batting"]
            hit_avg = sum([stats["timing"], stats["barreling"], stats["strength"], 
                           stats["bat_speed"], stats["elevation"], stats["eye"]]) / 6
            return int((hit_avg * 0.8) + (self.attributes["defense"]["def.glove"] * 0.1) + (self.attributes["baserunning"]["sprint_speed"] * 0.1))

    def get_salary_demands(self, league_tier=1, current_game=0, total_games=80, is_offseason=True):
        """Calculates expected AAV and length. Adapts to time of year."""
        ovr = self.get_ovr()
        
        # 1. Base AAV Curve (from your pseudo-code)
        base_aav = 750000 + (max(0, (ovr - 55)) ** 2.5) * 3500 
        tier_multiplier = max(0.2, 1.0 - (0.4 * (league_tier - 1)))
        base_aav *= tier_multiplier
        
        # 2. Timing Leverage (NEW)
        if is_offseason:
            # The "Bidding War" Premium: Top players demand slightly more in the winter
            if ovr > 80:
                base_aav *= 1.15 
        else:
            # The "Desperation" Decay: Value drops as the season progresses
            # At game 1, they want ~85% of their value. By game 80, they'll take ~40%.
            games_remaining_pct = (total_games - current_game) / total_games
            desperation_multiplier = 0.40 + (0.45 * games_remaining_pct)
            base_aav *= desperation_multiplier

        # 3. Base Length based on Age
        if self.age < 26: base_length = 5
        elif self.age < 30: base_length = 4
        elif self.age < 33: base_length = 3
        elif self.age < 36: base_length = 2
        else: base_length = 1
        
        # 3. Apply Trait Modifiers
        expected_aav = base_aav
        expected_length = base_length

        if self.contract_trait == "MoneyHungry":
            expected_aav *= 1.15
        elif self.contract_trait == "SecuritySeeker":
            expected_aav *= 0.90 
            expected_length = min(7, expected_length + 2)
        elif self.contract_trait == "BetOnYourself":
            expected_aav *= 1.10
            expected_length = 1 
        elif self.contract_trait == "Pioneer":
            expected_aav *= 1.05 
            
        return {"aav": int(expected_aav), "length": expected_length}

    # ==========================================
    # MOMENTUM & FORM CALCULATOR
    # ==========================================
    def calculate_form(self):
        """Parses recent performance and returns a momentum modifier from -3 to +3."""
        if not self.recent_form_str or self.recent_form_str.strip() == "":
            return 0
            
        games = [g.strip() for g in self.recent_form_str.split(',') if g.strip()]
        if not games: return 0
            
        if self.primary_pos == "P" or self.game_pos == "P":
            total_score = 0
            total_outs = 0
            for g in games:
                try:
                    score_str, outs_str = g.split('-')
                    total_score += int(score_str)
                    total_outs += int(outs_str)
                except ValueError: continue
            
            if total_outs == 0: return 0
            
            # Normalize to a "Points per 9 Innings (27 Outs)" scale
            score_per_9 = (total_score / total_outs) * 27
            
            if score_per_9 >= 32.0: form_val = 3       # Dominant
            elif score_per_9 >= 24.0: form_val = 2     # Great
            elif score_per_9 >= 16.0: form_val = 1     # Good
            elif score_per_9 <= -5.0: form_val = -3    # Getting shelled
            elif score_per_9 <= 2.0: form_val = -2     # Very bad
            elif score_per_9 <= 8.0: form_val = -1     # Struggling
            else: form_val = 0
            
            if form_val < 0 and "Ice in the Veins" in self.traits:
                form_val = max(form_val, -1)
                
            return form_val
            
        else:
            # Hitter Evaluation
            total_score = 0
            for g in games:
                try: total_score += int(g)
                except ValueError: continue
                    
            if total_score >= 18: form_val = 3       # En fuego
            elif total_score >= 12: form_val = 2     # Very Hot
            elif total_score >= 6: form_val = 1      # Heating Up
            elif total_score <= -5: form_val = -3    # Ice Cold
            elif total_score <= -2: form_val = -2    # Slumping
            elif total_score <= 1: form_val = -1     # Struggling
            else: form_val = 0
            
            if form_val < 0 and "Unfazed" in self.traits:
                form_val = max(form_val, -1)
                
            return form_val
            

    # ==========================================
    # DYNAMIC MAIN STAT CALCULATORS (PROPERTIES)
    # ==========================================
    @property
    def contact(self):
        b = self.attributes.get('batting', {})
        return int((b.get('timing', 0) + b.get('barreling', 0)) / 2)

    @property
    def power(self):
        b = self.attributes.get('batting', {})
        return int((b.get('strength', 0) + b.get('bat_speed', 0) + b.get('elevation', 0)) / 3)

    @property
    def discipline(self):
        b = self.attributes.get('batting', {})
        return int((b.get('eye', 0) + b.get('restraint', 0)) / 2)

    @property
    def speed(self):
        r = self.attributes.get('baserunning', {})
        return int((r.get('sprint_speed', 0) + r.get('instincts', 0)) / 2)

    @property
    def defense(self):
        d = self.attributes.get('defense', {})
        rng = d.get('def.range', 0)
        react = d.get('def.reaction', 0)
        glv = d.get('def.glove', 0)
        arm_str = d.get('def.ArmStr', 0)
        arm_acc = d.get('def.ArmAcc', 0)
        
        arm_overall = int((arm_str + arm_acc) / 2)
        overall = int((rng + glv + arm_overall) / 3) if rng else 0
        
        return {
            "overall": overall, "range": rng, "reaction": react, 
            "glove": glv, "arm_overall": arm_overall, 
            "arm_str": arm_str, "arm_acc": arm_acc
        }

    @property
    def velocity(self):
        p = self.attributes.get('pitching', {})
        return int((p.get('arm_speed', 0) + p.get('deception', 0)) / 2)

    @property
    def control(self):
        p = self.attributes.get('pitching', {})
        return int((p.get('accuracy', 0) + p.get('command', 0)) / 2)

    @property
    def movement(self):
        p = self.attributes.get('pitching', {})
        return int((p.get('spin_rate', 0) + p.get('bite', 0)) / 2)

    # ==========================================
    # UTILITY METHODS
    # ==========================================
    def __eq__(self, other):
        if isinstance(other, Player): return self.player_id == other.player_id
        return False

    def __hash__(self):
        return hash(self.player_id)

    def get_total_stat_sum(self):
        total = 0
        for cat in ["batting", "pitching", "defense", "baserunning"]:
            for stat_val in self.attributes.get(cat, {}).values():
                total += stat_val
        return total

    # ==========================================
    # OFFSEASON PROGRESSION & EVALUATION
    # ==========================================
    def process_offseason_aging(self, is_minor_leaguer=False, team=None):
        if self.is_retired: return
        self.age += 1

        total_initial_stats = self.get_total_stat_sum()
        last_peak = self.attributes.get('development', {}).get('last_peak_age', 32)

        if self.age > last_peak:
            for cat in ["batting", "pitching", "defense", "baserunning"]:
                for stat_name, current_val in self.attributes.get(cat, {}).items():
                    if stat_name in ["stamina", "max_stamina"]: continue
                    new_val = self.attempt_stat_degradation(current_val, self.age, last_peak)
                    self.attributes[cat][stat_name] = new_val

        current_stat_sum = self.get_total_stat_sum()
        degradation_pct = 1.0 - (current_stat_sum / max(1, total_initial_stats))
        
        if degradation_pct >= 0.20:
            is_on_contract = (team and self in team.roster and getattr(self, 'contract_years_remaining', 0) > 0)
            if not is_on_contract:
                print(f"  [RETIREMENT] {self.name} is contemplating retirement after a 20% career decline.")
                self.check_retirement(overall_rating=current_stat_sum/19, is_free_agent=True)

    def attempt_stat_degradation(self, current_stat, age, last_peak_age):
        if age <= last_peak_age: return current_stat
        if age >= 37: return max(1, current_stat - random.randint(1, 6))

        years_past_peak = age - last_peak_age
        decline_prob = 30.0 + (years_past_peak * 4.0) 

        if random.uniform(0, 100) <= decline_prob:
            return max(1, current_stat - random.randint(0, 5))
        return current_stat

    def check_retirement(self, overall_rating, is_free_agent=False):
        if self.is_retired: return True

        if is_free_agent: self.seasons_in_fa += 1
        else: self.seasons_in_fa = 0

        roll = random.uniform(0, 100)

        if not is_free_agent and self.age >= 35:
            retirement_chance = 15 + ((self.age - 35) * 15)
            if roll <= retirement_chance:
                self.is_retired = True
                return True

        if is_free_agent:
            if self.seasons_in_fa >= 2 and overall_rating < 65:
                self.is_retired = True
                return True
            
            if self.age >= 32:
                fa_vet_chance = 35 + ((self.age - 32) * 15) + (self.seasons_in_fa * 20)
                if roll <= fa_vet_chance:
                    self.is_retired = True
                    return True
                    
            if self.seasons_in_fa >= 3:
                self.is_retired = True
                return True

        return False
    
    def attempt_stat_growth(self, current_stat, age, peak_age):
        # Stop growing entirely once they hit their peak
        if age >= peak_age: return current_stat 

        # 1. The Governor: Check how much room they have left before their ceiling
        distance_to_cap = self.potential - current_stat
        
        if distance_to_cap <= 0:
            # If they hit their biological ceiling, only a tiny 2% chance to eke out 1 more point
            if random.uniform(0, 100) < 2.0:
                return min(99, current_stat + 1)
            return current_stat

        # 2. Base Probability: Further away from potential = higher chance to grow
        # A player 30 points away from potential has a massive 75% baseline chance to learn
        base_growth_chance = (distance_to_cap * 2.0) + 15.0 
        
        # 3. Age Accelerator: Young players absorb training much faster
        if age <= 22: age_multiplier = 1.30
        elif age <= 25: age_multiplier = 1.00
        else: age_multiplier = 0.75 
        
        final_prob = min(95.0, base_growth_chance * age_multiplier)

        # 4. The "Boom or Bust" Payload Dice Roll
        if random.uniform(0, 100) <= final_prob:
            roll = random.uniform(0, 100)
            
            if roll < 10.0:
                # BOOM (10%): Massive breakout leap (The Superstar mechanic)
                return min(99, current_stat + random.randint(7, 14))
            elif roll < 20.0:
                # BUST (10%): Plateau year (injury, bad mechanics, etc.)
                return current_stat
            elif roll < 50.0:
                # SOLID (30%): Great developmental progress
                return min(99, current_stat + random.randint(4, 7))
            else:
                # GRIND (50%): Standard minor progress
                return min(99, current_stat + random.randint(1, 4))
                
        return current_stat

    def evaluate_minor_league_season(self):
        bonus_rolls = []
        b_stats = self.stats["batting"]
        p_stats = self.stats["pitching"]

        if b_stats["AB"] >= 100:
            avg = b_stats["H"] / b_stats["AB"]
            obp = (b_stats["H"] + b_stats["BB"] + b_stats.get("HBP", 0)) / b_stats["PA"] if b_stats["PA"] > 0 else 0
            
            if avg >= 0.290: bonus_rolls.extend(["timing", "barreling"])
            if b_stats["HR"] >= 12: bonus_rolls.extend(["strength", "bat_speed", "elevation"])
            if obp >= 0.360 or b_stats["BB"] >= 25: bonus_rolls.extend(["eye", "restraint"])

        if p_stats["Outs"] >= 90:
            ip = p_stats["Outs"] / 3.0
            era = (p_stats["ER"] * 9) / ip
            k_per_9 = (p_stats["K"] * 9) / ip
            whip = (p_stats["BB"] + p_stats["H"]) / ip
            
            if era <= 3.50 or whip <= 1.20: bonus_rolls.extend(["accuracy", "command"])
            if k_per_9 >= 9.5: bonus_rolls.extend(["arm_speed", "deception", "spin_rate", "bite"])

        return bonus_rolls
        
    def evaluate_offers(self):
        """Evaluates all current bids in self.offers."""
        if not self.offers: return None
            
        demands = self.get_salary_demands()
        minimum_acceptable_aav = demands["aav"] * 0.75 
        
        best_bid = None
        highest_score = 0
        
        for bid in self.offers:
            if bid.yearly_value < minimum_acceptable_aav: continue
                
            score = bid.yearly_value
            
            if self.contract_trait == "MoneyHungry":
                pass 
            elif self.contract_trait == "SecuritySeeker":
                score = (bid.total_value * 0.8) + (bid.yearly_value * 0.2)
            elif self.contract_trait == "BetOnYourself":
                if bid.duration == 1: score *= 1.5
                else: score *= 0.5 
            elif self.contract_trait == "Loyalty":
                if bid.is_former_team: score *= 1.3 
            elif self.contract_trait == "Performance":
                if bid.team_tier == 1: score *= 1.4
                elif bid.team_tier == 2: score *= 0.9 
            elif self.contract_trait == "Pioneer":
                if bid.team_tier > 1: score *= 1.3
            elif self.contract_trait == "PlayingTime":
                my_ovr = self.get_ovr()
                ovr_difference = my_ovr - bid.competition_ovr
                
                if ovr_difference > 10: score *= 1.25 
                elif ovr_difference < 0: score *= 0.60 

            if score > highest_score:
                highest_score = score
                best_bid = bid
                
        return best_bid

    def sign_contract(self, winning_bid):
        """Converts the winning bid into the active contract."""
        self.contract_length = winning_bid.duration
        self.years_remaining = winning_bid.duration
        self.contract_salary = winning_bid.yearly_value
        
        self.offers = []
        self.next_decision_time = None
        
        return f"{self.name} has signed a {self.contract_length}-year, ${self.contract_salary:,.0f}/yr deal with Team {winning_bid.team_id}!"