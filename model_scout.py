import random

class Scout:
    def __init__(self, scout_id, name, age, accuracy, contract_length, salary):
        self.scout_id = scout_id
        self.name = name
        self.age = age
        self.accuracy = accuracy # 1-100 scale. New teams start with 50-60.
        
        # Contract Info
        self.contract_length = contract_length
        self.years_remaining = contract_length
        self.salary = salary
        
        # Hidden attribute: determines if they are likely to improve or stagnate
        self.development_curve = random.choice(["Early Bloomer", "Steady", "Late Bloomer", "Stagnant"])
        self.is_retired = False

    def process_offseason_aging(self):
        """Ages the scout, adjusts their accuracy, and ticks down their contract."""
        self.age += 1
        self.years_remaining -= 1
        
        # Retirement Logic (Scouts work longer than players, usually retire 60-75)
        if self.age > 65 and random.random() < 0.15:
            self.is_retired = True
            return

        # Progression/Regression Logic
        if self.age < 40:
            # Young scouts mostly improve
            if self.development_curve != "Stagnant" and random.random() < 0.60:
                self.accuracy += random.randint(1, 3)
        elif 40 <= self.age <= 55:
            # Prime years - slow refinement
            if self.development_curve in ["Steady", "Late Bloomer"] and random.random() < 0.30:
                self.accuracy += random.randint(1, 2)
        else:
            # Older scouts (55+) might lose touch with the modern game (regression)
            if random.random() < 0.40:
                self.accuracy -= random.randint(1, 4)

        # Cap rating between 20 and 99
        self.accuracy = max(20, min(99, self.accuracy))

    def generate_report(self, player_obj):
        """
        Takes a player object and returns the blurred stats based on THIS scout's accuracy.
        (Hooks directly into the math we built in the previous step).
        """
        is_pitcher = player_obj.assigned_pos == "P"
        true_attributes = player_obj.attributes['pitching'] if is_pitcher else player_obj.attributes['batting']
        
        error_margin = max(1.5, 12.0 - (self.accuracy / 10.0))
        
        perceived_stats = {}
        for stat, true_val in true_attributes.items():
            if stat == "stamina": 
                continue
            
            perceived_val = random.gauss(true_val, error_margin)
            perceived_stats[stat] = int(max(20, min(99, perceived_val)))
            
        return {
            "Scout_Name": self.name,
            "Accuracy_Rating": self.accuracy,
            "Perceived_Stats": perceived_stats
        }