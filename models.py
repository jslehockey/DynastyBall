import random

class Player:
    """
    An expanded Player class driven by an attribute dictionary.
    Includes a structured Player ID, performance tracking, and automated
    Free Agent pruning to prevent simulation bloat.
    """
    def __init__(self, player_id, name, attributes):
        self.player_id = str(player_id)  # e.g., "000100000001"
        self.name = name
        self.attributes = attributes
        
        # ==========================================
        # DEVELOPMENT & METRICS ARCHITECTURE
        # ==========================================
        dev_data = self.attributes.get('development', {})
        self.age = dev_data.get('age', 18)
        self.potential = dev_data.get('potential', 75)
        self.peak_age = dev_data.get('peak_age', 27)
        self.decline_rate = dev_data.get('decline_rate', 1.0)
        
        # --- NEW: SYSTEM RETIREMENT METRICS ---
        self.seasons_in_fa = 0  # Tracks consecutive seasons without a team
        self.is_retired = False
        
        # RPG Elements
        self.form = 0 
        self.traits = self.attributes.get('traits', [])

        # ==========================================
        # GAME & SEASON STAT TRACKING
        # ==========================================
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
            "fielding": {
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

    def __eq__(self, other):
        """Forces the engine to use the unique ID for list removals, comparisons, and equivalence."""
        if isinstance(other, Player):
            return self.player_id == other.player_id
        return False

    def __hash__(self):
        """Allows Player objects to be used safely in sets or as dictionary keys based on ID."""
        return hash(self.player_id)

    def process_offseason_aging(self, team=None):
        if self.is_retired: return
        self.age += 1

        # Track total stats for the 20% calculation
        total_initial_stats = self.get_total_stat_sum()

        # STAGE 1: Standard Progression/Degradation
        if self.age <= self.development['peak_age']:
            # Normal growth phase
            pass 
        elif self.age <= self.development['last_peak_age']:
            # Maintenance phase (slow decline)
            self.apply_degradation(mode="slow")
        else:
            # Steep decline phase
            self.apply_degradation(mode="fast")
            
        # STAGE 2: The Age 41 Cliff
        if self.age > 41:
            self.apply_degradation(mode="cliff")

        # STAGE 3: Retirement Contemplation
        current_stat_sum = self.get_total_stat_sum()
        degradation_pct = 1.0 - (current_stat_sum / total_initial_stats)
        
        if degradation_pct >= 0.20:
            # If they are on contract, they stay. If not, retirement chance spikes.
            is_on_contract = (team and self in team.roster and self.contract_years_remaining > 0)
            
            if not is_on_contract:
                print(f"  [RETIREMENT] {self.name} is contemplating retirement after a 20% decline.")
                self.check_retirement(overall_rating=..., is_free_agent=True)
    
    def apply_degradation(self, mode):
        multipliers = {"slow": 0.05, "fast": 0.12, "cliff": 0.25}
        rate = multipliers.get(mode, 0.05)
        
        # Apply rate to all scalable stats
        for cat in ["batting", "pitching", "fielding"]:
            for stat in self.attributes.get(cat, {}):
                if stat in ["stamina", "speed"]: continue # Special handling
                self.attributes[cat][stat] = int(self.attributes[cat][stat] * (1 - rate))

    def check_retirement(self, overall_rating, is_free_agent=False):
        """
        Runs an end-of-season check to determine if a player retires.
        Incorporates aggressive pruning for unsigned free agents to prevent FA bloat.
        """
        if self.is_retired:
            return True

        # Track consecutive free agency status
        if is_free_agent:
            self.seasons_in_fa += 1
        else:
            self.seasons_in_fa = 0 # Reset if they are signed

        roll = random.uniform(0, 100)

        # --- RULE 1: STANDARD AGE RETIREMENT (Roster Players) ---
        if not is_free_agent and self.age >= 35:
            retirement_chance = 15 + ((self.age - 35) * 15)
            if roll <= retirement_chance:
                self.is_retired = True
                return True

        # --- RULE 2: FREE AGENT POOL PRUNING (The "Spikes On The Wall" Rule) ---
        if is_free_agent:
            # Undrafted Rookies or low-tier players who sit for 2 full seasons lose hope
            if self.seasons_in_fa >= 2 and overall_rating < 65:
                self.is_retired = True
                return True
            
            # Aging veterans dumped into FA from dead teams
            if self.age >= 32:
                # Sitting in FA for even 1 year at an advanced age triggers high retirement odds
                fa_vet_chance = 35 + ((self.age - 32) * 15) + (self.seasons_in_fa * 20)
                if roll <= fa_vet_chance:
                    self.is_retired = True
                    return True
                    
            # Absolute baseline: No matter the age, if you rot in FA for 3 seasons, you retire.
            if self.seasons_in_fa >= 3:
                self.is_retired = True
                return True

        return False
    
    # ==========================================
    # OFFSEASON PROGRESSION & EVALUATION
    # ==========================================
    def attempt_stat_growth(self, current_stat, age, peak_age):
        """
        Baseline organic growth. Tightened by ~5% to accommodate performance bonuses.
        """
        if age >= peak_age:
            return current_stat 

        distance_to_max = 99 - current_stat
        # TIGHTENED: Lowered multiplier to 1.55 and floor to 2.0
        base_growth_chance = (distance_to_max * 1.55) + 2.0 

        years_left = peak_age - age 
        # TIGHTENED: Lowered age floor to 0.55
        age_multiplier = (years_left / 10.0) + 0.55 

        final_prob = base_growth_chance * age_multiplier

        if random.uniform(0, 100) <= final_prob:
            if random.uniform(0, 100) < 8.0: 
                return min(99, current_stat + random.randint(3, 5)) # Breakout
            else:
                return min(99, current_stat + random.randint(1, 3)) # Standard
        else:
            return current_stat

    def evaluate_minor_league_season(self):
        """
        Scans an 80-game season stat line. Returns a list of strings representing 
        which attributes earned a 'Performance Bonus Roll'.
        """
        bonus_rolls = []
        
        b_stats = self.stats["batting"]
        p_stats = self.stats["pitching"]

        # --- EVALUATE HITTERS ---
        # Require a minimum of 100 At-Bats so 1-for-1 call-ups don't get massive boosts
        if b_stats["AB"] >= 100:
            avg = b_stats["H"] / b_stats["AB"]
            obp = (b_stats["H"] + b_stats["BB"] + b_stats["HBP"]) / b_stats["PA"] if b_stats["PA"] > 0 else 0
            
            if avg >= 0.290:
                bonus_rolls.append("contact")
            if b_stats["HR"] >= 12:
                bonus_rolls.append("power")
            if obp >= 0.360 or b_stats["BB"] >= 25:
                bonus_rolls.append("discipline")

        # --- EVALUATE PITCHERS ---
        # Require a minimum of 90 Outs (30 Innings)
        if p_stats["Outs"] >= 90:
            ip = p_stats["Outs"] / 3.0
            era = (p_stats["ER"] * 9) / ip
            k_per_9 = (p_stats["K"] * 9) / ip
            whip = (p_stats["BB"] + p_stats["H"]) / ip
            
            if era <= 3.50 or whip <= 1.20:
                bonus_rolls.append("control")
            if k_per_9 >= 9.5:
                bonus_rolls.append("velocity")
                bonus_rolls.append("movement")

        return bonus_rolls

    def apply_degradation(self, category, stat_name, current_val):
        """
        Applies natural age-related decline.
        Physical stats degrade faster than Mental stats.
        """
        # Determine if stat is physical or mental
        is_physical = stat_name in ["speed", "range", "arm", "velocity"]
        
        # Calculate years past peak
        years_past = self.age - self.peak_age
        
        # Degradation math:
        # Physical stats: 2-4 pts/year
        # Mental stats: 0-2 pts/year
        decline_amount = random.randint(2, 4) if is_physical else random.randint(0, 2)
        
        # Apply degradation
        new_val = max(1, current_val - decline_amount)
        return new_val

    # --- Update your process_offseason_aging step 4 ---
    def process_offseason_aging(self, is_minor_leaguer=False):
        # ... (steps 1, 2, and 3 stay as you wrote them) ...

        # 4. Apply Physical Degradation if age > peak_age
        if self.age > self.peak_age:
            for category in ["batting", "pitching", "baserunning", "fielding"]:
                for stat_name, current_val in self.attributes.get(category, {}).items():
                    # Skip stamina (handled elsewhere)
                    if stat_name in ["stamina", "max_stamina"]: continue
                    
                    self.attributes[category][stat_name] = self.apply_degradation(category, stat_name, current_val)
    
class LeagueEnvironment:
    """
    Holds the multi-axis era modifiers. 1.0 is the neutral baseline.
    Each axis now has dedicated floor and ceiling caps to prevent mathematical anomalies.
    """
    def __init__(self, power=1.0, contact=1.0, speed=1.0, pitching=1.0, defense=1.0, max_shift=0.015):
        self.era_modifiers = {
            "power": power,     
            "contact": contact,   
            "speed": speed,     
            "pitching": pitching,
            "defense": defense    # NEW: Defense axis added
        }
        
        # NEW: Custom boundaries for each axis (Floor, Ceiling)
        self.bounds = {
            "power": (0.93, 1.07),
            "contact": (0.93, 1.07),
            "speed": (0.93, 1.07),
            "pitching": (0.93, 1.07),
            "defense": (0.96, 1.05)  # Asymmetrical bounds specifically for the quadratic curve
        }
        self.max_shift = max_shift

    def advance_season(self):
        """Applies an independent random walk to every axis respecting its specific bounds."""
        for axis in self.era_modifiers:
            shift = random.uniform(-self.max_shift, self.max_shift)
            new_value = self.era_modifiers[axis] + shift
            
            # Clamp between the specific floor and ceiling for this axis
            floor, ceiling = self.bounds[axis]
            self.era_modifiers[axis] = max(floor, min(ceiling, new_value))

class Team:
    """Holds roster data, current batting order state, and team box score."""
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
        
        # ==========================================
        # NESTED TEAM STAT TRACKING
        # ==========================================
        self.stats = {
            "batting": {
                "PA": 0, "AB": 0, "R": 0, "H": 0, 
                "1B": 0, "2B": 0, "3B": 0, "HR": 0,
                "RBI": 0, "BB": 0, "HBP": 0, "K": 0
            },
            "pitching": {
                "Outs": 0,
                "H": 0, "R": 0, "ER": 0, "HR": 0,
                "BB": 0, "HBP": 0, "K": 0, "W": 0,
                "L": 0, "HLD": 0, "BS": 0, "SV": 0,
                "Pitches": 0
            },
            "fielding": {
                "PO": 0,  # Putouts
                "A": 0,   # Assists
                "E": 0,   # Errors
                "TC": 0   # Total Chances
            }
        }

    def get_next_batter(self):
        batter = self.lineup[self.batter_index]
        self.batter_index = (self.batter_index + 1) % len(self.lineup)
        return batter