import random

class Player:
    """
    An expanded Player class driven by an attribute dictionary.
    Includes a structured Player ID, performance tracking, automated
    Free Agent pruning, and dynamic Sub-Stat calculations.
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
        
        # --- NEW: SYSTEM RETIREMENT METRICS ---
        self.seasons_in_fa = 0
        self.is_retired = False
        
        # RPG Elements
        self.form = 0 
        self.traits = self.attributes.get('traits', [])

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
        """
        A unified dictionary returning both raw sub-stats and calculated 
        top-level ratings for all defensive metrics.
        """
        d = self.attributes.get('defense', {})
        
        # Raw Sub-stats
        rng = d.get('def.range', 0)
        react = d.get('def.reaction', 0)
        glv = d.get('def.glove', 0)
        arm_str = d.get('def.ArmStr', 0)
        arm_acc = d.get('def.ArmAcc', 0)
        
        # Top-level Composites
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
        if isinstance(other, Player):
            return self.player_id == other.player_id
        return False

    def __hash__(self):
        return hash(self.player_id)

    def get_total_stat_sum(self):
        """Calculates the sum of all raw sub-stats to track overall degradation."""
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

        if self.age <= self.peak_age:
            pass # Normal growth phase
        elif self.age <= self.attributes.get('development', {}).get('last_peak_age', 32):
            self.apply_degradation_pass(mode="slow")
        else:
            self.apply_degradation_pass(mode="fast")
            
        if self.age > 41:
            self.apply_degradation_pass(mode="cliff")

        current_stat_sum = self.get_total_stat_sum()
        degradation_pct = 1.0 - (current_stat_sum / max(1, total_initial_stats))
        
        if degradation_pct >= 0.20:
            is_on_contract = (team and self in team.roster and getattr(self, 'contract_years_remaining', 0) > 0)
            if not is_on_contract:
                print(f"  [RETIREMENT] {self.name} is contemplating retirement after a 20% decline.")
                self.check_retirement(overall_rating=current_stat_sum/19, is_free_agent=True)
                
        # 4. Apply Physical Degradation if age > peak_age
        if self.age > self.peak_age:
            for category in ["batting", "pitching", "baserunning", "defense"]:
                for stat_name, current_val in self.attributes.get(category, {}).items():
                    if stat_name in ["stamina", "max_stamina"]: continue
                    self.attributes[category][stat_name] = self.apply_physical_degradation(category, stat_name, current_val)

    def apply_degradation_pass(self, mode):
        multipliers = {"slow": 0.05, "fast": 0.12, "cliff": 0.25}
        rate = multipliers.get(mode, 0.05)
        
        for cat in ["batting", "pitching", "defense", "baserunning"]:
            for stat in self.attributes.get(cat, {}):
                if stat in ["stamina", "max_stamina"]: continue
                self.attributes[cat][stat] = int(self.attributes[cat][stat] * (1 - rate))

    def apply_physical_degradation(self, category, stat_name, current_val):
        """Applies natural age-related decline. Physical stats degrade faster than Mental stats."""
        # NEW: Added def.range to the physical stats decay array
        physical_stats = ["strength", "bat_speed", "sprint_speed", "def.range", "def.reaction", "def.ArmStr", "arm_speed", "spin_rate"]
        is_physical = stat_name in physical_stats
        
        decline_amount = random.randint(2, 4) if is_physical else random.randint(0, 2)
        return max(1, current_val - decline_amount)

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
            if random.uniform(0, 100) < 8.0: 
                return min(99, current_stat + random.randint(3, 5))
            else:
                return min(99, current_stat + random.randint(1, 3))
        return current_stat

    def evaluate_minor_league_season(self):
        bonus_rolls = []
        b_stats = self.stats["batting"]
        p_stats = self.stats["pitching"]

        # --- EVALUATE HITTERS ---
        if b_stats["AB"] >= 100:
            avg = b_stats["H"] / b_stats["AB"]
            obp = (b_stats["H"] + b_stats["BB"] + b_stats.get("HBP", 0)) / b_stats["PA"] if b_stats["PA"] > 0 else 0
            
            # Grant bonuses to the underlying sub-stats
            if avg >= 0.290:
                bonus_rolls.extend(["timing", "barreling"])
            if b_stats["HR"] >= 12:
                bonus_rolls.extend(["strength", "bat_speed", "elevation"])
            if obp >= 0.360 or b_stats["BB"] >= 25:
                bonus_rolls.extend(["eye", "restraint"])

        # --- EVALUATE PITCHERS ---
        if p_stats["Outs"] >= 90:
            ip = p_stats["Outs"] / 3.0
            era = (p_stats["ER"] * 9) / ip
            k_per_9 = (p_stats["K"] * 9) / ip
            whip = (p_stats["BB"] + p_stats["H"]) / ip
            
            if era <= 3.50 or whip <= 1.20:
                bonus_rolls.extend(["accuracy", "command"])
            if k_per_9 >= 9.5:
                bonus_rolls.extend(["arm_speed", "deception", "spin_rate", "bite"])

        return bonus_rolls

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
    def __init__(self, name, lineup, pitcher, defense, hook_threshold=5.0, adrenaline_trigger=True):
        self.name = name
        self.lineup = lineup
        self.pitcher = pitcher
        self.defense = defense
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