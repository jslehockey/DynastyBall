import random
from models import Player

class PlayerFactory:
    def __init__(self, current_season):
        self.current_season = current_season
        self.sequence_tracker = 0
        
        self.first_names = [
            # Normal Names
            "Michael", "Christopher", "Matthew", "Joshua", "David", "Andrew", "Daniel", "James", "Justin", "Joseph", 
            "Ryan", "John", "Robert", "Nicholas", "Anthony", "William", "Jonathan", "Kyle", "Brandon", "Jacob", 
            "Tyler", "Zachary", "Kevin", "Eric", "Steven", "Thomas", "Richard", "Brian", "Mark", "Jim",
            "Babe", "Ty", "Mickey", "Willie", "Hank", "Jackie", "Lou", "Stan", "Nolan", "Cy"
        ]

        # 30 Common American + 10 Baseball Legends
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", 
            "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", 
            "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Walker",
            "Ruth", "Mantle", "Mays", "Aaron", "Gehrig", "Ryan", "Ripken", "Gwynn", "Griffey", "Bonds"
        ]

        # ==========================================
        # HITTER ARCHETYPES (Scale 50-99, 75 is Average)
        # ==========================================
        self.positional_archetypes = {
            "C": {
                "Bench":  {"contact": 75, "power": 86, "discipline": 72, "speed": 40, "range": 50, "glove": 84, "arm": 90},
                "Mauer":  {"contact": 88, "power": 68, "discipline": 82, "speed": 55, "range": 55, "glove": 80, "arm": 78},
                "Molina": {"contact": 72, "power": 60, "discipline": 70, "speed": 35, "range": 60, "glove": 92, "arm": 92}
            },
            "1B": {
                "Gehrig": {"contact": 88, "power": 88, "discipline": 82, "speed": 50, "range": 55, "glove": 75, "arm": 65},
                "Pujols": {"contact": 84, "power": 90, "discipline": 84, "speed": 30, "range": 50, "glove": 84, "arm": 70},
                "Keith":  {"contact": 82, "power": 65, "discipline": 80, "speed": 45, "range": 65, "glove": 92, "arm": 75}
            },
            "2B": {
                "Morgan": {"contact": 80, "power": 78, "discipline": 90, "speed": 85, "range": 75, "glove": 82, "arm": 70},
                "Alomar": {"contact": 85, "power": 68, "discipline": 78, "speed": 82, "range": 85, "glove": 88, "arm": 78},
                "Kent":   {"contact": 78, "power": 85, "discipline": 72, "speed": 45, "range": 65, "glove": 75, "arm": 75}
            },
            "3B": {
                "Schmidt":{"contact": 76, "power": 90, "discipline": 85, "speed": 55, "range": 80, "glove": 88, "arm": 88},
                "Boggs":  {"contact": 92, "power": 60, "discipline": 92, "speed": 45, "range": 70, "glove": 80, "arm": 75},
                "Brett":  {"contact": 88, "power": 78, "discipline": 78, "speed": 65, "range": 75, "glove": 78, "arm": 80}
            },
            "SS": {
                "Ozzie":  {"contact": 72, "power": 40, "discipline": 78, "speed": 86, "range": 94, "glove": 94, "arm": 86},
                "Ripken": {"contact": 80, "power": 80, "discipline": 75, "speed": 45, "range": 72, "glove": 86, "arm": 88},
                "Jeter":  {"contact": 86, "power": 68, "discipline": 78, "speed": 75, "range": 68, "glove": 78, "arm": 78}
            },
            "LF": {
                "Williams":{"contact": 94, "power": 88, "discipline": 94, "speed": 40, "range": 50, "glove": 60, "arm": 60},
                "Bonds":  {"contact": 84, "power": 92, "discipline": 95, "speed": 75, "range": 70, "glove": 78, "arm": 72},
                "Rickey": {"contact": 80, "power": 65, "discipline": 90, "speed": 95, "range": 80, "glove": 75, "arm": 65}
            },
            "CF": {
                "Mays":   {"contact": 82, "power": 86, "discipline": 78, "speed": 86, "range": 90, "glove": 90, "arm": 88},
                "Griffey":{"contact": 80, "power": 88, "discipline": 75, "speed": 82, "range": 88, "glove": 88, "arm": 82},
                "Lofton": {"contact": 84, "power": 55, "discipline": 80, "speed": 92, "range": 92, "glove": 85, "arm": 65}
            },
            "RF": {
                "Ruth":   {"contact": 82, "power": 95, "discipline": 88, "speed": 35, "range": 45, "glove": 55, "arm": 75},
                "Clemente":{"contact": 88, "power": 72, "discipline": 65, "speed": 70, "range": 85, "glove": 88, "arm": 95},
                "Gwynn":  {"contact": 95, "power": 50, "discipline": 88, "speed": 70, "range": 65, "glove": 78, "arm": 65}
            },
            "DH": {
                "Edgar":  {"contact": 88, "power": 82, "discipline": 88, "speed": 35, "range": 40, "glove": 50, "arm": 50},
                "Ortiz":  {"contact": 80, "power": 90, "discipline": 85, "speed": 30, "range": 35, "glove": 45, "arm": 45}
            }
        }

        self.general_archetypes = {
            "Dunn":   {"contact": 60, "power": 92, "discipline": 88, "speed": 35, "range": 40, "glove": 45, "arm": 50},
            "Ichiro": {"contact": 92, "power": 45, "discipline": 75, "speed": 90, "range": 88, "glove": 88, "arm": 90},
            "Zobrist":{"contact": 78, "power": 75, "discipline": 80, "speed": 75, "range": 75, "glove": 78, "arm": 75}
        }

        # ==========================================
        # PITCHER ARCHETYPES
        # ==========================================
        self.sp_archetypes = {
            "Ryan":      {"control": 60, "velocity": 92, "movement": 80, "stamina": 92},
            "Maddux":    {"control": 94, "velocity": 65, "movement": 86, "stamina": 88},
            "Pedro":     {"control": 82, "velocity": 88, "movement": 94, "stamina": 80},
            "R.Johnson": {"control": 72, "velocity": 92, "movement": 88, "stamina": 85},
            "Wakefield": {"control": 70, "velocity": 50, "movement": 94, "stamina": 95},
            "Koufax":    {"control": 78, "velocity": 86, "movement": 92, "stamina": 85},
            "Gibson":    {"control": 82, "velocity": 85, "movement": 82, "stamina": 95},
            "Buehrle":   {"control": 86, "velocity": 68, "movement": 78, "stamina": 92},
            "Lincecum":  {"control": 68, "velocity": 86, "movement": 90, "stamina": 78}
        }
        
        self.rp_archetypes = {
            "Miller":    {"control": 72, "velocity": 88, "movement": 90, "stamina": 45}, # Elite stuff, lower control
            "Hader":     {"control": 68, "velocity": 92, "movement": 86, "stamina": 40}, # Max velo from left side
            "Fingers":   {"control": 85, "velocity": 75, "movement": 82, "stamina": 55}  # Multi-inning control artist
        }

        self.cl_archetypes = {
            "Rivera":    {"control": 92, "velocity": 82, "movement": 95, "stamina": 25}, # Cutter magic
            "Chapman":   {"control": 62, "velocity": 96, "movement": 75, "stamina": 20}, # Pure gas
            "Gagne":     {"control": 78, "velocity": 88, "movement": 88, "stamina": 25}  # Balanced dominance
        }

    def get_next_id(self):
        self.sequence_tracker += 1
        return f"{self.current_season:04d}{self.sequence_tracker:08d}"

    def generate_name(self):
        return f"{random.choice(self.first_names)} {random.choice(self.last_names)}"

    def generate_inaugural_hitter(self, target_pos="CF", is_expansion=True, is_minor=False, league_tier=1):
        player_id = self.get_next_id()
        name = self.generate_name()
        
        age = int(random.gauss(22, 3)) if is_minor else int(random.gauss(26, 4))
        age = max(18, min(age, 38))
        
        # 75% Positional, 25% General Archetype Selection
        if random.random() < 0.75:
            # Fallback to DH if an invalid position is passed
            pos_dict = self.positional_archetypes.get(target_pos, self.positional_archetypes["DH"])
            arch_name, stat_means = random.choice(list(pos_dict.items()))
        else:
            arch_name, stat_means = random.choice(list(self.general_archetypes.items()))
        
        current_stats = {}
        for stat, mean in stat_means.items():
            if stat == "stamina":
                continue
                
            tier_mult = max(0.5, 1.0 - (0.07 * (league_tier - 1)))
            minor_mult = 0.90 if is_minor else 1.0
            
            effective_mean = mean * tier_mult * minor_mult
            
            val = int(random.gauss(effective_mean, 6))
            current_stats[stat] = max(50, min(99, val))

        hitter_stam = int(random.gauss(75, 7))
        hitter_stam = max(50, min(99, hitter_stam))

        attributes = {
            "bats": random.choice(["R", "R", "L", "S"]),
            "throws": random.choice(["R", "R", "R", "L"]),
            "batting": {
                "contact": current_stats["contact"],
                "power": current_stats["power"],
                "discipline": current_stats["discipline"],
                "stamina": hitter_stam
            },
            "baserunning": {"speed": current_stats["speed"]},
            "fielding": {
                "range": current_stats["range"], 
                "glove": current_stats["glove"], 
                "arm": current_stats["arm"]
            },
            "development": {
                "age": age,
                "peak_age": random.randint(27, 30),
                "last_peak_age": random.randint(32, 36),
                "archetype": arch_name
            },
            "strategy": {"approach_slider": 3, "steal_2nd_slider": 3, "steal_3rd_slider": 3},
            "pitching": {"control": 30, "velocity": 30, "movement": 30},
            "assigned_pos": target_pos # Tag them with their drafted position
        }
        # Create the object and attach the position explicitly
        player_obj = Player(player_id, name, attributes)
        player_obj.assigned_pos = target_pos
        return player_obj
    
    def generate_inaugural_pitcher(self, role="SP", is_expansion=True, is_minor=False, league_tier=1):
        player_id = self.get_next_id()
        name = self.generate_name()
        
        age = int(random.gauss(23, 3)) if is_minor else int(random.gauss(27, 4))
        age = max(18, min(age, 39)) 
        
        # Select archetype pool based on role
        if role == "SP":
            pool = self.sp_archetypes
        elif role in ["MR", "LR"]:
            pool = self.rp_archetypes
        else: # SU, CL
            pool = self.cl_archetypes

        arch_name, stat_means = random.choice(list(pool.items()))
        
        current_stats = {}
        for stat, mean in stat_means.items():
            if stat == "stamina":
                continue
            
            tier_mult = max(0.5, 1.0 - (0.07 * (league_tier - 1)))
            minor_mult = 0.90 if is_minor else 1.0
            effective_mean = mean * tier_mult * minor_mult
            
            current_stats[stat] = int(max(50, min(99, random.gauss(effective_mean, 6))))

        # Stamina is tied strictly to role and the archetype baseline
        stamina = stat_means["stamina"]
        if role in ["MR", "LR"]: stamina = random.randint(40, 60)
        elif role in ["SU", "CL"]: stamina = random.randint(15, 30)

        attributes = {
            "bats": random.choice(["R", "L"]), 
            "throws": random.choice(["R", "R", "R", "L"]),
            "batting": {"contact": 15, "power": 15, "discipline": 15, "stamina": 100},
            "baserunning": {"speed": random.randint(10, 30)},
            "fielding": {"range": 50, "glove": 50, "arm": 70},
            "pitching": {
                "control": current_stats["control"],
                "velocity": current_stats["velocity"],
                "movement": current_stats["movement"],
                "stamina": stamina
            },
            "development": {
                "age": age,
                "peak_age": random.randint(27, 30),
                "last_peak_age": random.randint(31, 35),
                "archetype": arch_name
            },
            "strategy": {"attack_slider": 3},
            "assigned_pos": "P",
            "role": role
        }
        
        # Create the object and attach the position explicitly
        player_obj = Player(player_id, name, attributes)
        player_obj.assigned_pos = "P"
        return player_obj

    def generate_team_roster(self, team_name, is_expansion=True, league_tier=1):
        """Generates a complete lineup using positional assignments, plus a 5-man bullpen."""
        
        # Explicitly build a structured defense rather than 9 random profiles
        positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]
        lineup = [self.generate_inaugural_hitter(pos, is_expansion, is_minor=False, league_tier=league_tier) for pos in positions]
        
        pitchers = [
            self.generate_inaugural_pitcher("SP", is_expansion, is_minor=False, league_tier=league_tier),
            self.generate_inaugural_pitcher("MR", is_expansion, is_minor=False, league_tier=league_tier),
            self.generate_inaugural_pitcher("LR", is_expansion, is_minor=False, league_tier=league_tier),
            self.generate_inaugural_pitcher("SU", is_expansion, is_minor=False, league_tier=league_tier),
            self.generate_inaugural_pitcher("CL", is_expansion, is_minor=False, league_tier=league_tier)
        ]
        
        return {
            "name": team_name,
            "lineup": lineup,
            "pitchers": pitchers
        }