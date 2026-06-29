import random

class ScoutingDepartment:
    def __init__(self):
        # Defines the access levels for the different subscription tiers
        self.tiers = {
            "Free": {"max_scouts": 1, "data_level": "OVR_Only"},
            "Basic_Scout": {"max_scouts": 2, "data_level": "Top_Bottom_Traits"},
            "Premium_Scout": {"max_scouts": 3, "data_level": "Full_Granular"}
        }

    def calculate_public_ovr(self, true_stats_dict):
        """Calculates the true average of all core stats for the public OVR."""
        if not true_stats_dict: return 0
        total = sum(true_stats_dict.values())
        count = len(true_stats_dict)
        return int(total / count)

    def generate_player_report(self, player_obj, scout_obj, sub_tier="Free"):
        """
        Generates the frontend UI payload for the manager by routing 
        the player through the assigned scout's specific filter.
        """
        is_pitcher = player_obj.assigned_pos == "P"
        true_attributes = player_obj.attributes['pitching'] if is_pitcher else player_obj.attributes['batting']
        
        # 1. THE PUBLIC DATA (Everyone sees this)
        report = {
            "Name": player_obj.name,
            "Age": player_obj.attributes['development']['age'],
            "Position": player_obj.assigned_pos,
            "Stamina": true_attributes.get('stamina', 100),
            # OVR is mathematically precise, no fog of war
            "OVR": self._calculate_public_ovr({k: v for k, v in true_attributes.items() if k != "stamina"})
        }

        # 2. FREE TIER ENDS HERE
        if sub_tier == "Free":
            report["Scouting_Data"] = "LOCKED. Upgrade to view granular mechanics."
            return report

        # 3. GENERATE THE SCOUT'S PERCEIVED DATA
        # We call the individual Scout object to apply its specific accuracy math
        scout_report = scout_obj.generate_report(player_obj)
        perceived_stats = scout_report["Perceived_Stats"]

        # 4. BASIC TIER: Only gets the Top 2 and Bottom 1 stats
        if sub_tier == "Basic_Scout":
            sorted_stats = sorted(perceived_stats.items(), key=lambda x: x[1], reverse=True)
            report["Scout_Notes"] = {
                "Strengths": [f"{sorted_stats[0][0]} ({sorted_stats[0][1]})", f"{sorted_stats[1][0]} ({sorted_stats[1][1]})"],
                "Weakness": f"{sorted_stats[-1][0]} ({sorted_stats[-1][1]})"
            }
            report["Granular_Data"] = "LOCKED. Upgrade to Premium for full breakdown."
            return report

        # 5. PREMIUM TIER: Gets the full table (blurred by the scout's rating)
        if sub_tier == "Premium_Scout":
            report["Granular_Data"] = perceived_stats
            report["Scout_Name"] = scout_report["Scout_Name"]
            report["Confidence_Level"] = f"{scout_report['Accuracy_Rating']}/100"
            return report