import random

class Player:
    """
    An expanded Player class driven by an attribute dictionary.
    Includes a structured Player ID, performance tracking, automated
    Free Agent pruning, dynamic Sub-Stat calculations, and Form Momentum.
    """
    def __init__(self, player_id, name, attributes):
        self.player_id = str(player_id)  # e.g., "000100000001"
        self.name = name
        
        # Attributes now stores the raw SUB-STATS
        self.attributes = attributes
        
        # DEVELOPMENT & METRICS ARCHITECTURE
        dev_data = self.attributes.get('development', {})
        self.age = dev_data.get('age', 18)
        self.potential = dev_data.get('potential', 75)
        self.peak_age = dev_data.get('peak_age', 27)
        self.decline_rate = dev_data.get('decline_rate', 1.0)
        
        # SYSTEM RETIREMENT METRICS
        self.seasons_in_fa = 0
        self.is_retired = False

        self.primary_pos = self.attributes.get('primary_pos', 'DH')
        self.game_pos = self.attributes.get('game_pos', 'DH')
        
        # --- NEW: STREAKS & MOMENTUM MEMORY ---
        self.current_hit_streak = int(self.attributes.get('current_hit_streak', 0))
        self.longest_hit_streak = int(self.attributes.get('longest_hit_streak', 0))
        
        self.current_obp_streak = int(self.attributes.get('current_obp_streak', 0))
        self.longest_obp_streak = int(self.attributes.get('longest_obp_streak', 0))
        
        self.current_scoreless_outs = int(self.attributes.get('current_scoreless_outs', 0))
        self.longest_scoreless_outs = int(self.attributes.get('longest_scoreless_outs', 0))
        
        self.recent_form_str = str(self.attributes.get('recent_form', ""))
        
        # RPG Elements
        self.traits = self.attributes.get('traits', [])
        self.form = self.calculate_form() # Replaces the hardcoded 0 with a dynamic -3 to +3

        # GAME & SEASON STAT TRACKING
        self.stats = {
            "batting": {
                "PA": 0, "AB": 0, "R": 0, "H": 0, 
                "1B": 0, "2B": 0, "3B": 0, "HR": 0,
                "RBI": 0, "BB": 0, "HBP": 0, "K": 0,
                "SB": 0, "CS": 0
            },
            "pitching": {
                "Outs": 0,
                "H": 0, "R": 0, "ER": 0, "HR": 0,
                "BB": 0, "HBP": 0, "K": 0, "W": 0,
                "L": 0, "HLD": 0, "BS": 0, "SV": 0,
                "Pitches": 0
            },
            "defense": {
                "PO": 0,  # Putouts
                "A": 0,   # Assists
                "E": 0,   # Errors
                "TC": 0   # Total Chances
            }
        }
        
        self.total_outs_recorded = 0
        self.strikeouts = 0  
        self.hits_allowed = 0
        self.walks_allowed = 0
        self.runs_allowed = 0
        self.earned_runs = 0
        self.home_runs_allowed = 0

    # --- NEW: MOMENTUM CALCULATOR WITH TRAITS ---
    def calculate_form(self):
        """
        Parses the recent_form_str (e.g., "1-4, 2-5, 0-3" for hitters or "6.0-1, 7.0-0" for pitchers)
        and returns a momentum modifier from -3 to +3.
        """
        if not self.recent_form_str or self.recent_form_str.strip() == "":
            return 0
            
        games = [g.strip() for g in self.recent_form_str.split(',') if g.strip()]
        if not games: return 0
            
        if self.primary_pos == "P":
            # Pitcher format: "IP-ER" e.g., "6.0-2, 1.1-0"
            total_outs = 0
            total_er = 0
            for g in games:
                try:
                    ip_str, er_str = g.split('-')
                    parts = ip_str.split('.')
                    outs = int(parts[0]) * 3
                    if len(parts) > 1: outs += int(parts[1])
                    total_outs += outs
                    total_er += int(er_str)
                except ValueError:
                    continue
            
            if total_outs == 0: return 0
            ip = total_outs / 3.0
            era = (total_er * 9) / ip
            
            if era <= 1.00: form_val = 3
            elif era <= 2.50: form_val = 2
            elif era <= 3.50: form_val = 1
            elif era >= 7.00: form_val = -3
            elif era >= 5.50: form_val = -2
            elif era >= 4.50: form_val = -1
            else: form_val = 0
            
            # --- ICE IN THE VEINS TRAIT ---
            if form_val < 0 and "Ice in the Veins" in self.traits:
                form_val = max(form_val, -1)
                
            return form_val
            
        else:
            # Hitter format: "H-AB" e.g., "1-4, 2-3"
            total_h = 0
            total_ab = 0
            for g in games:
                try:
                    h_str, ab_str = g.split('-')
                    total_h += int(h_str)
                    total_ab += int(ab_str)
                except ValueError:
                    continue
                    
            if total_ab == 0: return 0
            avg = total_h / total_ab
            
            if avg >= 0.400: form_val = 3
            elif avg >= 0.330: form_val = 2
            elif avg >= 0.280: form_val = 1
            elif avg <= 0.100: form_val = -3
            elif avg <= 0.180: form_val = -2
            elif avg <= 0.220: form_val = -1
            else: form_val = 0
            
            # --- UNFAZED TRAIT ---
            if form_val < 0 and "Unfazed" in self.traits:
                form_val = max(form_val, -1)
                
            return form_val

    # DYNAMIC MAIN STAT CALCULATORS (Properties)
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
            "overall": overall,
            "range": rng,
            "reaction": react,
            "glove": glv,
            "arm_overall": arm_overall,
            "arm_str": arm_str,
            "arm_acc": arm_acc
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

    # UTILITY METHODS
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

    # OFFSEASON PROGRESSION & EVALUATION
    def process_offseason_aging(self, is_minor_leaguer=False, team=None):
        if self.is_retired: return
        self.age += 1

        total_initial_stats = self.get_total_stat_sum()
        last_peak = self.attributes.get('development', {}).get('last_peak_age', 32)

        # If they have passed their absolute peak, run the degradation math on every sub-stat
        if self.age > last_peak:
            for cat in ["batting", "pitching", "defense", "baserunning"]:
                for stat_name, current_val in self.attributes.get(cat, {}).items():
                    if stat_name in ["stamina", "max_stamina"]: continue
                    
                    new_val = self.attempt_stat_degradation(current_val, self.age, last_peak)
                    self.attributes[cat][stat_name] = new_val

        # RETIREMENT CHECK
        current_stat_sum = self.get_total_stat_sum()
        degradation_pct = 1.0 - (current_stat_sum / max(1, total_initial_stats))
        
        if degradation_pct >= 0.20:
            is_on_contract = (team and self in team.roster and getattr(self, 'contract_years_remaining', 0) > 0)
            if not is_on_contract:
                print(f"  [RETIREMENT] {self.name} is contemplating retirement after a 20% career decline.")
                self.check_retirement(overall_rating=current_stat_sum/19, is_free_agent=True)


    def attempt_stat_degradation(self, current_stat, age, last_peak_age):
        """Probability-based decline engine mirroring attempt_stat_growth."""
        if age <= last_peak_age: 
            return current_stat

        # THE CLIFF: Age 37+ (Automatic 1-6 point drop)
        if age >= 37:
            return max(1, current_stat - random.randint(1, 6))

        # THE TWILIGHT: Between end of peak and age 36
        years_past_peak = age - last_peak_age
        
        # Base probability is 30%, increasing slightly as the gap widens
        decline_prob = 30.0 + (years_past_peak * 4.0) 

        # Roll to see if degradation hits this specific sub-stat this year
        if random.uniform(0, 100) <= decline_prob:
            # Random drop of 0 to 5 points (0 means they rolled degradation but got lucky)
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
        if age >= peak_age: return current_stat 

        distance_to_max = 99 - current_stat
        base_growth_chance = (distance_to_max * 1.55) + 2.0 
        years_left = peak_age - age 
        age_multiplier = (years_left / 10.0) + 0.55 
        final_prob = base_growth_chance * age_multiplier

        if random.uniform(0, 100) <= final_prob:
            if random.uniform(0, 100) < 22.0: 
                return min(99, current_stat + random.randint(3, 9))
            else:
                return min(99, current_stat + random.randint(1, 6))
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
                    
class LeagueEnvironment:
    def __init__(self, power=1.0, contact=1.0, speed=1.0, pitching=1.0, defense=1.0, max_shift=0.015):
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
        for axis in self.era_modifiers:
            shift = random.uniform(-self.max_shift, self.max_shift)
            new_value = self.era_modifiers[axis] + shift
            floor, ceiling = self.bounds[axis]
            self.era_modifiers[axis] = max(floor, min(ceiling, new_value))

class Team:
    def __init__(self, name, lineup, pitcher, defense, stadium=None, hook_threshold=5.0, adrenaline_trigger=True):
        self.name = name
        self.lineup = lineup
        self.pitcher = pitcher
        self.defense = defense
        
        # --- NEW: STADIUM COMPOSITION ---
        # If the Exporter provides a stadium, use it. If not, build a default one automatically.
        self.stadium = stadium if stadium else Stadium(name=f"{self.name} Stadium")
        
        self.batter_index = 0
        self.hook_threshold = hook_threshold 
        self.adrenaline_trigger = adrenaline_trigger
        self.bullpen = [] 
        self.used_pitchers = [] 
        self.game_pitchers = [pitcher] 
        self.linescore = []
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

    def get_next_batter(self):
        batter = self.lineup[self.batter_index]
        self.batter_index = (self.batter_index + 1) % len(self.lineup)
        return batter