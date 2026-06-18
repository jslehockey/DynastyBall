import random
from models import Player

class PlayerFactory:
    def __init__(self, current_season):
        self.current_season = current_season
        self.sequence_tracker = 0
        
        self.first_names = [
            "Michael", "Christopher", "Matthew", "Joshua", "David", "Andrew", "Daniel", "James", "Justin", "Joseph", 
            "Ryan", "John", "Robert", "Nicholas", "Anthony", "William", "Jonathan", "Kyle", "Brandon", "Jacob", 
            "Tyler", "Zachary", "Kevin", "Eric", "Steven", "Thomas", "Richard", "Brian", "Mark", "Jim",
            "Babe", "Ty", "Mickey", "Willie", "Hank", "Jackie", "Lou", "Stan", "Nolan", "Cy"
        ]

        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", 
            "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", 
            "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Walker",
            "Ruth", "Mantle", "Mays", "Aaron", "Gehrig", "Ryan", "Ripken", "Gwynn", "Griffey", "Bonds"
        ]

        # --- TRAIT POOLS ---
        self.pitching_traits = ["Marathon Man", "Escape Artist", "Groundball Guru", "Putaway Pitcher", "Rubber Arm", "Ice in the Veins", "Pitch to Contact", "Lights Out"]
        self.hitting_traits = ["Clutch", "Table Setter", "First Pitch Killer", "Gold Glover", "Speed Demon", "Unfazed", "Platoon Punisher", "Launch Angle God"]

        # HITTER ARCHETYPES (13 Sub-Stats)
        self.positional_archetypes = {
            "C": {
                "Bench":  {"timing": 67, "barreling": 76, "strength": 84, "bat_speed": 76, "elevation": 86, "eye": 67, "restraint": 70, "sprint_speed": 38, "instincts": 38, "def.reaction": 57, "def.glove": 80, "def.ArmStr": 87, "def.ArmAcc": 84},
                "Mauer":  {"timing": 86, "barreling": 82, "strength": 67, "bat_speed": 67, "elevation": 61, "eye": 81, "restraint": 75, "sprint_speed": 52, "instincts": 52, "def.reaction": 52, "def.glove": 76, "def.ArmStr": 72, "def.ArmAcc": 76},
                "Molina": {"timing": 67, "barreling": 70, "strength": 62, "bat_speed": 57, "elevation": 52, "eye": 71, "restraint": 62, "sprint_speed": 33, "instincts": 33, "def.reaction": 81, "def.glove": 87, "def.ArmStr": 86, "def.ArmAcc": 89}
            },
            "1B": {
                "Gehrig": {"timing": 84, "barreling": 84, "strength": 86, "bat_speed": 82, "elevation": 84, "eye": 78, "restraint": 78, "sprint_speed": 48, "instincts": 48, "def.reaction": 57, "def.glove": 71, "def.ArmStr": 62, "def.ArmAcc": 62},
                "Pujols": {"timing": 78, "barreling": 82, "strength": 89, "bat_speed": 84, "elevation": 84, "eye": 82, "restraint": 78, "sprint_speed": 29, "instincts": 29, "def.reaction": 67, "def.glove": 80, "def.ArmStr": 67, "def.ArmAcc": 67},
                "Keith":  {"timing": 78, "barreling": 78, "strength": 62, "bat_speed": 67, "elevation": 57, "eye": 78, "restraint": 74, "sprint_speed": 43, "instincts": 43, "def.reaction": 81, "def.glove": 87, "def.ArmStr": 71, "def.ArmAcc": 71}
            },
            "2B": {
                "Morgan": {"timing": 76, "barreling": 76, "strength": 72, "bat_speed": 80, "elevation": 70, "eye": 87, "restraint": 84, "sprint_speed": 81, "instincts": 81, "def.reaction": 62, "def.glove": 78, "def.ArmStr": 67, "def.ArmAcc": 67},
                "Alomar": {"timing": 81, "barreling": 81, "strength": 65, "bat_speed": 71, "elevation": 58, "eye": 76, "restraint": 72, "sprint_speed": 78, "instincts": 78, "def.reaction": 84, "def.glove": 84, "def.ArmStr": 74, "def.ArmAcc": 74},
                "Kent":   {"timing": 74, "barreling": 74, "strength": 84, "bat_speed": 78, "elevation": 81, "eye": 68, "restraint": 68, "sprint_speed": 43, "instincts": 43, "def.reaction": 81, "def.glove": 71, "def.ArmStr": 71, "def.ArmAcc": 71}
            },
            "3B": {
                "Schmidt":{"timing": 68, "barreling": 76, "strength": 89, "bat_speed": 82, "elevation": 86, "eye": 84, "restraint": 78, "sprint_speed": 52, "instincts": 52, "def.reaction": 90, "def.glove": 84, "def.ArmStr": 87, "def.ArmAcc": 80},
                "Boggs":  {"timing": 89, "barreling": 86, "strength": 57, "bat_speed": 62, "elevation": 52, "eye": 89, "restraint": 86, "sprint_speed": 43, "instincts": 43, "def.reaction": 90, "def.glove": 76, "def.ArmStr": 71, "def.ArmAcc": 71},
                "Brett":  {"timing": 84, "barreling": 84, "strength": 76, "bat_speed": 78, "elevation": 68, "eye": 76, "restraint": 72, "sprint_speed": 62, "instincts": 62, "def.reaction": 81, "def.glove": 74, "def.ArmStr": 76, "def.ArmAcc": 76}
            },
            "SS": {
                "Ozzie":  {"timing": 70, "barreling": 67, "strength": 38, "bat_speed": 48, "elevation": 29, "eye": 76, "restraint": 72, "sprint_speed": 82, "instincts": 82, "def.reaction": 94, "def.glove": 89, "def.ArmStr": 82, "def.ArmAcc": 82},
                "Ripken": {"timing": 76, "barreling": 76, "strength": 78, "bat_speed": 74, "elevation": 76, "eye": 74, "restraint": 68, "sprint_speed": 43, "instincts": 43, "def.reaction": 90, "def.glove": 82, "def.ArmStr": 86, "def.ArmAcc": 82},
                "Jeter":  {"timing": 82, "barreling": 82, "strength": 67, "bat_speed": 71, "elevation": 56, "eye": 76, "restraint": 72, "sprint_speed": 71, "instincts": 71, "def.reaction": 58, "def.glove": 74, "def.ArmStr": 74, "def.ArmAcc": 74}
            },
            "LF": {
                "Williams":{"timing": 89, "barreling": 89, "strength": 84, "bat_speed": 87, "elevation": 80, "eye": 91, "restraint": 87, "sprint_speed": 38, "instincts": 38, "def.reaction": 57, "def.glove": 57, "def.ArmStr": 57, "def.ArmAcc": 57},
                "Bonds":  {"timing": 80, "barreling": 80, "strength": 89, "bat_speed": 89, "elevation": 84, "eye": 93, "restraint": 87, "sprint_speed": 71, "instincts": 71, "def.reaction": 62, "def.glove": 74, "def.ArmStr": 68, "def.ArmAcc": 68},
                "Rickey": {"timing": 76, "barreling": 76, "strength": 62, "bat_speed": 71, "elevation": 52, "eye": 87, "restraint": 84, "sprint_speed": 90, "instincts": 90, "def.reaction": 62, "def.glove": 71, "def.ArmStr": 62, "def.ArmAcc": 62}
            },
            "CF": {
                "Mays":   {"timing": 78, "barreling": 78, "strength": 84, "bat_speed": 84, "elevation": 78, "eye": 76, "restraint": 72, "sprint_speed": 82, "instincts": 82, "def.reaction": 89, "def.glove": 86, "def.ArmStr": 84, "def.ArmAcc": 84},
                "Griffey":{"timing": 76, "barreling": 76, "strength": 84, "bat_speed": 87, "elevation": 80, "eye": 72, "restraint": 70, "sprint_speed": 78, "instincts": 78, "def.reaction": 89, "def.glove": 84, "def.ArmStr": 78, "def.ArmAcc": 78},
                "Lofton": {"timing": 80, "barreling": 80, "strength": 52, "bat_speed": 62, "elevation": 43, "eye": 78, "restraint": 74, "sprint_speed": 87, "instincts": 87, "def.reaction": 87, "def.glove": 81, "def.ArmStr": 62, "def.ArmAcc": 62}
            },
            "RF": {
                "Ruth":   {"timing": 76, "barreling": 80, "strength": 94, "bat_speed": 87, "elevation": 89, "eye": 86, "restraint": 82, "sprint_speed": 33, "instincts": 33, "def.reaction": 52, "def.glove": 52, "def.ArmStr": 76, "def.ArmAcc": 67},
                "Clemente":{"timing": 84, "barreling": 84, "strength": 68, "bat_speed": 74, "elevation": 63, "eye": 65, "restraint": 59, "sprint_speed": 67, "instincts": 67, "def.reaction": 90, "def.glove": 84, "def.ArmStr": 93, "def.ArmAcc": 87},
                "Gwynn":  {"timing": 91, "barreling": 89, "strength": 48, "bat_speed": 57, "elevation": 38, "eye": 86, "restraint": 82, "sprint_speed": 67, "instincts": 67, "def.reaction": 57, "def.glove": 74, "def.ArmStr": 62, "def.ArmAcc": 62}
            },
            "DH": {
                "Edgar":  {"timing": 84, "barreling": 84, "strength": 78, "bat_speed": 82, "elevation": 74, "eye": 86, "restraint": 82, "sprint_speed": 33, "instincts": 33, "def.reaction": 43, "def.glove": 48, "def.ArmStr": 48, "def.ArmAcc": 48},
                "Ortiz":  {"timing": 76, "barreling": 76, "strength": 87, "bat_speed": 86, "elevation": 84, "eye": 82, "restraint": 80, "sprint_speed": 29, "instincts": 29, "def.reaction": 38, "def.glove": 43, "def.ArmStr": 43, "def.ArmAcc": 43}
            }
        }

        self.general_archetypes = {
            "Dunn":   {"timing": 48, "barreling": 67, "strength": 93, "bat_speed": 76, "elevation": 93, "eye": 87, "restraint": 80, "sprint_speed": 33, "instincts": 33, "def.reaction": 43, "def.glove": 43, "def.ArmStr": 48, "def.ArmAcc": 48},
            "Ichiro": {"timing": 89, "barreling": 86, "strength": 43, "bat_speed": 52, "elevation": 33, "eye": 76, "restraint": 67, "sprint_speed": 86, "instincts": 86, "def.reaction": 82, "def.glove": 84, "def.ArmStr": 87, "def.ArmAcc": 84},
            "Zobrist":{"timing": 74, "barreling": 74, "strength": 71, "bat_speed": 74, "elevation": 68, "eye": 78, "restraint": 74, "sprint_speed": 71, "instincts": 71, "def.reaction": 71, "def.glove": 74, "def.ArmStr": 71, "def.ArmAcc": 71}
        }

        # PITCHER ARCHETYPES (Reduced by ~5%, EXCEPT STAMINA)
        self.sp_archetypes = {
            "Ryan":      {"arm_speed": 93, "deception": 82, "accuracy": 48, "command": 67, "spin_rate": 81, "bite": 71, "stamina": 92},
            "Maddux":    {"arm_speed": 52, "deception": 71, "accuracy": 91, "command": 87, "spin_rate": 76, "bite": 87, "stamina": 88},
            "Pedro":     {"arm_speed": 86, "deception": 82, "accuracy": 76, "command": 80, "spin_rate": 91, "bite": 87, "stamina": 80},
            "R.Johnson": {"arm_speed": 91, "deception": 84, "accuracy": 65, "command": 72, "spin_rate": 80, "bite": 87, "stamina": 85},
            "Wakefield": {"arm_speed": 38, "deception": 57, "accuracy": 67, "command": 67, "spin_rate": 38, "bite": 94, "stamina": 95},
            "Koufax":    {"arm_speed": 84, "deception": 80, "accuracy": 72, "command": 76, "spin_rate": 91, "bite": 84, "stamina": 85},
            "Gibson":    {"arm_speed": 82, "deception": 80, "accuracy": 78, "command": 78, "spin_rate": 78, "bite": 78, "stamina": 95},
            "Buehrle":   {"arm_speed": 59, "deception": 70, "accuracy": 84, "command": 80, "spin_rate": 68, "bite": 80, "stamina": 92},
            "Lincecum":  {"arm_speed": 84, "deception": 80, "accuracy": 61, "command": 68, "spin_rate": 87, "bite": 84, "stamina": 78}
        }
        
        self.rp_archetypes = {
            "Miller":    {"arm_speed": 87, "deception": 80, "accuracy": 65, "command": 72, "spin_rate": 82, "bite": 89, "stamina": 45},
            "Hader":     {"arm_speed": 91, "deception": 84, "accuracy": 61, "command": 68, "spin_rate": 87, "bite": 76, "stamina": 40},
            "Fingers":   {"arm_speed": 71, "deception": 71, "accuracy": 81, "command": 81, "spin_rate": 78, "bite": 78, "stamina": 55}
        }

        self.cl_archetypes = {
            "Rivera":    {"arm_speed": 80, "deception": 76, "accuracy": 87, "command": 87, "spin_rate": 81, "bite": 94, "stamina": 25},
            "Chapman":   {"arm_speed": 94, "deception": 88, "accuracy": 52, "command": 66, "spin_rate": 76, "bite": 67, "stamina": 20},
            "Gagne":     {"arm_speed": 86, "deception": 82, "accuracy": 74, "command": 74, "spin_rate": 84, "bite": 84, "stamina": 25}
        }

    # --- NEW HELPER: Shared Trait Generator ---
    def _generate_traits(self, is_pitcher=False):
        player_traits = []
        available = self.pitching_traits.copy() if is_pitcher else self.hitting_traits.copy()

        # 60% chance for 1st trait
        if random.uniform(0, 100) <= 60.0:
            t1 = random.choice(available)
            player_traits.append(t1)
            available.remove(t1)

            # 25% chance for 2nd trait
            if random.uniform(0, 100) <= 25.0:
                t2 = random.choice(available)
                player_traits.append(t2)
                available.remove(t2)

                # 10% chance for 3rd trait
                if random.uniform(0, 100) <= 10.0:
                    t3 = random.choice(available)
                    player_traits.append(t3)

        return player_traits

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
        
        if random.random() < 0.75:
            pos_dict = self.positional_archetypes.get(target_pos, self.positional_archetypes["DH"])
            arch_name, stat_means = random.choice(list(pos_dict.items()))
        else:
            arch_name, stat_means = random.choice(list(self.general_archetypes.items()))
        
        current_stats = {}
        for stat, mean in stat_means.items():
            tier_mult = max(0.5, 1.0 - (0.07 * (league_tier - 1)))
            minor_mult = 0.90 if is_minor else 1.0
            effective_mean = mean * tier_mult * minor_mult
            
            val = int(random.gauss(effective_mean, 6))
            current_stats[stat] = max(50, min(99, val))

        # Generate correlated Defensive Range based on Sprint Speed
        sprint = current_stats.get("sprint_speed", 50)
        
        # Positional tweaks: CF/SS are natural fielders, 1B/DH/C are not
        if target_pos in ["CF", "SS", "2B"]: range_modifier = random.randint(0, 4)
        elif target_pos in ["1B", "C", "DH"]: range_modifier = random.randint(-5, -1)
        else: range_modifier = random.randint(-2, 2)
        
        current_stats["def.range"] = max(40, min(99, int(random.gauss(sprint + range_modifier, 4))))

        hitter_stam = int(random.gauss(75, 7))
        hitter_stam = max(50, min(99, hitter_stam))

        # --- GENERATE TRAITS ---
        generated_traits = self._generate_traits(is_pitcher=False)

        # Map the raw generated stats into their appropriate buckets
        attributes = {
            "bats": random.choice(["R", "R", "L", "S"]),
            "throws": random.choice(["R", "R", "R", "L"]),
            "batting": {
                "timing": current_stats["timing"],
                "barreling": current_stats["barreling"],
                "strength": current_stats["strength"],
                "bat_speed": current_stats["bat_speed"],
                "elevation": current_stats["elevation"],
                "eye": current_stats["eye"],
                "restraint": current_stats["restraint"],
                "stamina": hitter_stam
            },
            "baserunning": {
                "sprint_speed": current_stats["sprint_speed"],
                "instincts": current_stats["instincts"]
            },
            "defense": {
                "def.range": current_stats["def.range"],
                "def.reaction": current_stats["def.reaction"],
                "def.glove": current_stats["def.glove"],
                "def.ArmStr": current_stats["def.ArmStr"],
                "def.ArmAcc": current_stats["def.ArmAcc"]
            },
            "development": {
                "age": age,
                "peak_age": random.randint(27, 30),
                "last_peak_age": random.randint(32, 36),
                "archetype": arch_name
            },
            "strategy": {"approach_slider": 3, "steal_2nd_slider": 3, "steal_3rd_slider": 3},
            "pitching": {"arm_speed": 30, "deception": 30, "accuracy": 30, "command": 30, "spin_rate": 30, "bite": 30, "stamina": 20},
            "Primary Pos": target_pos, 
            "Game Pos": target_pos,
            "traits": generated_traits # Assigned here!
        }
        
        player_obj = Player(player_id, name, attributes)
        player_obj.traits = generated_traits # Direct access assignment
        player_obj.assigned_pos = target_pos
        return player_obj
    
    def generate_inaugural_pitcher(self, role="SP", is_expansion=True, is_minor=False, league_tier=1):
        player_id = self.get_next_id()
        name = self.generate_name()
        
        age = int(random.gauss(23, 3)) if is_minor else int(random.gauss(27, 4))
        age = max(18, min(age, 39)) 
        
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

        stamina = stat_means["stamina"]
        if role in ["MR", "LR"]: stamina = random.randint(40, 60)
        elif role in ["SU", "CL"]: stamina = random.randint(15, 30)

        # --- GENERATE TRAITS ---
        generated_traits = self._generate_traits(is_pitcher=True)

        # Map the raw generated stats into the pitching bucket
        attributes = {
            "bats": random.choice(["R", "L"]), 
            "throws": random.choice(["R", "R", "R", "L"]),
            # Dummy hitting/fielding stats for pitchers
            "batting": {"timing": 15, "barreling": 15, "strength": 15, "bat_speed": 15, "elevation": 15, "eye": 15, "restraint": 15, "stamina": 100},
            "baserunning": {"sprint_speed": random.randint(10, 30), "instincts": 15},
            "defense": {"def.range": 50, "def.reaction": 50, "def.glove": 50, "def.ArmStr": 60, "def.ArmAcc": 50},
            "pitching": {
                "arm_speed": current_stats["arm_speed"],
                "deception": current_stats["deception"],
                "accuracy": current_stats["accuracy"],
                "command": current_stats["command"],
                "spin_rate": current_stats["spin_rate"],
                "bite": current_stats["bite"],
                "stamina": stamina
            },
            "development": {
                "age": age,
                "peak_age": random.randint(27, 30),
                "last_peak_age": random.randint(31, 35),
                "archetype": arch_name
            },
            "strategy": {"attack_slider": 3},
            "Primary Pos": "P",
            "Game Pos": "P",
            "role": role,
            "traits": generated_traits # Assigned here!
        }
        
        player_obj = Player(player_id, name, attributes)
        player_obj.traits = generated_traits # Direct access assignment
        player_obj.assigned_pos = "P"
        return player_obj

    def generate_team_roster(self, team_name, is_expansion=True, league_tier=1):
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