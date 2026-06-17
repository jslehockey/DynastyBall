import random
from models import Player

class PlayerFactory:
    def __init__(self, current_season):
        self.current_season = current_season
        self.sequence_tracker = 0
        
        self.first_names = ["Dash", "Rip", "Crash", "Jolt", "Duke", "Spike", "Ace", "Rex", "Brock", "Jaxon", "Juan", "Mike", "Leo", "Trey", "Zane", "Cruz"]
        self.last_names = ["Thunder", "Lightning", "Steele", "Stone", "Cannon", "Blaze", "Fury", "Vance", "Grip", "Trout", "Smith", "Fox", "Wolf", "Hunter"]

        # Means for Gaussian generation (Scale 50-99)
        self.hitter_archetypes = {
            "Ruth":      {"contact": 59, "power": 83, "discipline": 77, "speed": 27, "range": 36, "glove": 45, "arm": 63},
            "Gwynn":     {"contact": 86, "power": 36, "discipline": 83, "speed": 63, "range": 54, "glove": 72, "arm": 54},
            "Henderson": {"contact": 74, "power": 47, "discipline": 83, "speed": 87, "range": 77, "glove": 68, "arm": 45},
            "Williams":  {"contact": 86, "power": 78, "discipline": 86, "speed": 36, "range": 45, "glove": 54, "arm": 54},
            "Mays":      {"contact": 79, "power": 79, "discipline": 72, "speed": 79, "range": 83, "glove": 83, "arm": 83},
            "Guerrero":  {"contact": 79, "power": 83, "discipline": 32, "speed": 54, "range": 54, "glove": 63, "arm": 86},
            "Ozzie":     {"contact": 68, "power": 29, "discipline": 77, "speed": 77, "range": 87, "glove": 87, "arm": 79},
            "Ripken":    {"contact": 72, "power": 63, "discipline": 72, "speed": 36, "range": 68, "glove": 79, "arm": 79},
            "Ichiro":    {"contact": 86, "power": 37, "discipline": 63, "speed": 86, "range": 83, "glove": 83, "arm": 86},
            "Dunn":      {"contact": 41, "power": 82, "discipline": 83, "speed": 18, "range": 18, "glove": 27, "arm": 36},
            "Bonds":     {"contact": 79, "power": 86, "discipline": 87, "speed": 54, "range": 54, "glove": 68, "arm": 63},
            "Pujols":    {"contact": 83, "power": 84, "discipline": 79, "speed": 18, "range": 45, "glove": 83, "arm": 63},
            "Zobrist":   {"contact": 68, "power": 68, "discipline": 68, "speed": 68, "range": 68, "glove": 68, "arm": 68}
        }

        # ==========================================
        # PITCHER ARCHETYPES (-10% Stats, -5 Stamina)
        # ==========================================
        self.pitcher_archetypes = {
            "Ryan":      {"control": 27, "velocity": 87, "movement": 68, "stamina": 90},
            "R.Johnson": {"control": 45, "velocity": 86, "movement": 77, "stamina": 75},
            "Wakefield": {"control": 45, "velocity": 29, "movement": 86, "stamina": 90},
            "Pedro":     {"control": 79, "velocity": 81, "movement": 86, "stamina": 70},
            "Maddux":    {"control": 87, "velocity": 38, "movement": 77, "stamina": 75},
            "Rivera":    {"control": 86, "velocity": 77, "movement": 86, "stamina": 20},
            "Chapman":   {"control": 27, "velocity": 89, "movement": 54, "stamina": 20},
            "Koufax":    {"control": 68, "velocity": 81, "movement": 86, "stamina": 75},
            "Gagne":     {"control": 70, "velocity": 86, "movement": 77, "stamina": 20},
            "Buehrle":   {"control": 79, "velocity": 45, "movement": 63, "stamina": 87},
            "Lincecum":  {"control": 63, "velocity": 79, "movement": 86, "stamina": 65},
            "Hoffman":   {"control": 83, "velocity": 54, "movement": 86, "stamina": 20},
            "Wildcard":  {"control": 68, "velocity": 68, "movement": 68, "stamina": 70}
        }

    def get_next_id(self):
        self.sequence_tracker += 1
        return f"{self.current_season:04d}{self.sequence_tracker:08d}"

    def generate_name(self):
        return f"{random.choice(self.first_names)} {random.choice(self.last_names)}"

    def generate_stat(self, mean, league_tier, is_minor):
        """Calculates gaussian stat with tier/minor penalties and 50-99 bounds."""
        # Tier 1 = 1.0, Tier 2 = 0.93, Tier 3 = 0.86
        tier_mult = max(0.5, 1.0 - (0.07 * (league_tier - 1)))
        final_mean = mean * tier_mult
        if is_minor:
            final_mean *= 0.83 # 17% reduction
        
        return int(max(50, min(99, random.gauss(final_mean, 6))))

    def create_player(self, is_minor, league_tier, is_pitcher=False, role="SP"):
        player_id = self.get_next_id()
        name = self.generate_name()
        
        # Age curve: Minors younger (22), Majors (27)
        age = int(random.gauss(22, 3)) if is_minor else int(random.gauss(27, 5))
        age = max(18, min(age, 38))
        
        if is_pitcher:
            arch_name, stats = random.choice(list(self.pitcher_archetypes.items()))
            pitching = {k: self.generate_stat(v, league_tier, is_minor) for k, v in stats.items() if k != 'stamina'}
            pitching['stamina'] = stats['stamina'] # Stamina stays as defined
            if role == "MR": pitching['stamina'] = random.randint(35, 55)
            elif role in ["SU", "CL"]: pitching['stamina'] = random.randint(15, 30)
            
            attrs = {
                "bats": random.choice(["R", "L"]), "throws": random.choice(["R", "L"]),
                "batting": {"contact": 15, "power": 15, "discipline": 15, "stamina": 100},
                "fielding": {"range": 50, "glove": 50, "arm": 70},
                "pitching": pitching,
                "development": {"age": age, "peak_age": random.randint(27, 30), "last_peak_age": random.randint(31, 35), "archetype": arch_name}
            }
        else:
            arch_name, stats = random.choice(list(self.hitter_archetypes.items()))
            batting = {k: self.generate_stat(v, league_tier, is_minor) for k, v in stats.items() if k not in ["speed", "range", "glove", "arm", "stamina"]}
            fielding = {k: self.generate_stat(v, league_tier, is_minor) for k, v in stats.items() if k in ["range", "glove", "arm"]}
            speed = self.generate_stat(stats["speed"], league_tier, is_minor)
            
            attrs = {
                "bats": random.choice(["R", "L", "S"]), "throws": random.choice(["R", "L"]),
                "batting": batting,
                "baserunning": {"speed": speed},
                "fielding": fielding,
                "development": {"age": age, "peak_age": random.randint(27, 30), "last_peak_age": random.randint(31, 35), "archetype": arch_name}
            }
        return Player(player_id, name, attrs)

    def generate_inaugural_hitter(self, is_expansion=True, is_minor=False, league_tier=1):
        player_id = self.get_next_id()
        name = self.generate_name()
        
        # Age and Archetype selection
        age = int(random.gauss(22, 3)) if is_minor else int(random.gauss(26, 4))
        age = max(18, min(age, 38))
        
        # Always pick from the main Major League archetypes
        arch_name, stat_means = random.choice(list(self.hitter_archetypes.items()))
        
        current_stats = {}
        for stat, mean in stat_means.items():
            if stat == "stamina":
                current_stats[stat] = random.randint(60, 90)
                continue
                
            # Apply 10% reduction if minor (as per your request)
            # Tier 1 = 1.0, Tier 2 = 0.93...
            tier_mult = max(0.5, 1.0 - (0.07 * (league_tier - 1)))
            minor_mult = 0.90 if is_minor else 1.0
            
            # Combine multipliers
            effective_mean = mean * tier_mult * minor_mult
            
            # Gaussian distribution centered on the effective mean
            val = int(random.gauss(effective_mean, 6))
            current_stats[stat] = max(50, min(99, val))

        # --- STAMINA: Gaussian Distro (Mean 75, Std Dev 7) ---
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
            "pitching": {"control": 30, "velocity": 30, "movement": 30}
        }
        from models import Player
        return Player(player_id, name, attributes)

    def generate_inaugural_pitcher(self, role="SP", is_expansion=True, is_minor=False, league_tier=1):
        player_id = self.get_next_id()
        name = self.generate_name()
        
        # Age logic: Pitchers skew slightly older
        age = int(random.gauss(23, 3)) if is_minor else int(random.gauss(27, 4))
        age = max(18, min(age, 39)) 
        
        # Pick from main Major League archetypes
        arch_name, stat_means = random.choice(list(self.pitcher_archetypes.items()))
        
        # --- GAUSSIAN GENERATION ---
        current_stats = {}
        for stat, mean in stat_means.items():
            if stat == "stamina":
                # Preserve stamina logic as requested
                continue
            
            # Tier 1 = 1.0, Tier 2 = 0.93, Tier 3 = 0.86
            tier_mult = max(0.5, 1.0 - (0.07 * (league_tier - 1)))
            minor_mult = 0.90 if is_minor else 1.0
            
            # Apply multipliers
            effective_mean = mean * tier_mult * minor_mult
            
            # Generate Gaussian stat capped at 50-99
            current_stats[stat] = int(max(50, min(99, random.gauss(effective_mean, 6))))

        # Set Stamina overrides after Gaussian loop
        stamina = stat_means["stamina"]
        if role == "MR": stamina = random.randint(35, 55)
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
            "strategy": {"attack_slider": 3}
        }
        
        from models import Player
        return Player(player_id, name, attributes)

    def generate_team_roster(self, team_name, is_expansion=True, league_tier=1):
        """Generates a complete 9-man lineup and 5-man bullpen using the specific league tier."""
        lineup = [self.generate_inaugural_hitter(is_expansion, is_minor=False, league_tier=league_tier) for _ in range(9)]
        
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

    def generate_minor_league_roster(self, team_name, is_expansion=True, league_tier=1):
        """Generates a Minor League roster matching the Tier, inherently penalized an extra 20%."""
        lineup = [self.generate_inaugural_hitter(is_expansion, is_minor=True, league_tier=league_tier) for _ in range(9)]
        
        pitchers = [
            self.generate_inaugural_pitcher("SP", is_expansion, is_minor=True, league_tier=league_tier),
            self.generate_inaugural_pitcher("MR", is_expansion, is_minor=True, league_tier=league_tier),
            self.generate_inaugural_pitcher("LR", is_expansion, is_minor=True, league_tier=league_tier),
            self.generate_inaugural_pitcher("SU", is_expansion, is_minor=True, league_tier=league_tier),
            self.generate_inaugural_pitcher("CL", is_expansion, is_minor=True, league_tier=league_tier)
        ]
        
        return {
            "name": team_name,
            "lineup": lineup,
            "pitchers": pitchers
        }

    def generate_draft_prospect(self, position_type="hitter"):
        """
        Generates a prospect for the Rookie Draft.
        """
        player_id = self.get_next_id()
        name = self.generate_name()
        
        is_college = random.uniform(0, 100) < 55.0
        
        if is_college:
            origin = "College"
            age = random.choice([20, 21, 22])
            development_boost = 0.12 
        else:
            origin = "High School"
            age = random.choice([18, 19])
            development_boost = 0.0 
            
        peak_age = random.randint(26, 29)
        decline_rate = round(random.uniform(0.7, 1.3), 2)
        
        tier_roll = random.uniform(0, 100)
        
        if tier_roll < 5.0:
            base_mult = random.uniform(0.75, 0.85) 
        elif tier_roll < 20.0:
            base_mult = random.uniform(0.60, 0.74) 
        elif tier_roll < 60.0:
            base_mult = random.uniform(0.45, 0.59) 
        else:
            base_mult = random.uniform(0.30, 0.44) 
            
        tier_mult = min(0.95, base_mult + development_boost)

        current_stats = {}
        
        if position_type == "hitter":
            arch_name, stat_ranges = random.choice(list(self.hitter_archetypes.items()))
            
            for stat, (low, high) in stat_ranges.items():
                base_val = random.randint(low, high)
                current_stats[stat] = max(1, int(base_val * tier_mult))
                
            attributes = {
                "bats": random.choice(["R", "R", "L", "S"]), 
                "throws": random.choice(["R", "R", "R", "L"]),
                "batting": {
                    "contact": current_stats["contact"],
                    "power": current_stats["power"],
                    "discipline": current_stats["discipline"],
                    "stamina": current_stats["stamina"]
                },
                "baserunning": {"speed": current_stats["speed"]},
                "fielding": {
                    "range": current_stats["range"], 
                    "glove": current_stats["glove"], 
                    "arm": current_stats["arm"]
                },
                "development": {
                    "age": age,
                    "peak_age": peak_age,
                    "decline_rate": decline_rate,
                    "archetype": arch_name,
                    "origin": origin 
                },
                "traits": [],
                "strategy": {"approach_slider": 3, "steal_2nd_slider": 3, "steal_3rd_slider": 3, "steal_2nd_threshold": 0, "steal_3rd_threshold": 0}
            }
            
        else: 
            arch_name, stat_ranges = random.choice(list(self.pitcher_archetypes.items()))
            role = random.choices(["SP", "MR", "SU", "CL"], weights=[50, 30, 10, 10])[0]
            
            for stat, (low, high) in stat_ranges.items():
                base_val = random.randint(low, high)
                current_stats[stat] = max(1, int(base_val * tier_mult))
                
            if role == "SP": stamina = random.randint(80, 100)
            elif role == "MR": stamina = random.randint(35, 55)
            else: stamina = random.randint(15, 30)
                
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
                    "peak_age": peak_age,
                    "decline_rate": decline_rate,
                    "archetype": arch_name,
                    "origin": origin 
                },
                "traits": [],
                "strategy": {"attack_slider": 3}
            }

        from models import Player
        return Player(player_id, name, attributes)