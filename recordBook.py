class RecordBook:
    def __init__(self, stat_log_records):
        self.records = stat_log_records

    def get_career_leaderboard(self, stat_category, limit=5):
        career_totals = {}
        player_names = {}
        for r in self.records:
            pid = str(r["PlayerID"])
            player_names[pid] = r["Name"]
            if stat_category in r and r[stat_category] != "":
                career_totals[pid] = career_totals.get(pid, 0) + float(r[stat_category])
        sorted_leaders = sorted(career_totals.items(), key=lambda x: x[1], reverse=True)
        return [(player_names[pid], pid, total) for pid, total in sorted_leaders[:limit]]

    def get_franchise_records(self, team_id, stat_category, record_type="season", limit=5):
        team_seasons = [r for r in self.records if str(r.get("TeamID")) == team_id and stat_category in r and r[stat_category] != ""]
        if record_type == "season":
            sorted_seasons = sorted(team_seasons, key=lambda x: float(x[stat_category]), reverse=True)
            return [(r["Name"], r["SeasonID"], r["Tier"], float(r[stat_category])) for r in sorted_seasons[:limit]]
        elif record_type == "career":
            franchise_career = {}
            player_names = {}
            for r in team_seasons:
                pid = str(r["PlayerID"])
                player_names[pid] = r["Name"]
                franchise_career[pid] = franchise_career.get(pid, 0) + float(r[stat_category])
            sorted_franchise = sorted(franchise_career.items(), key=lambda x: x[1], reverse=True)
            return [(player_names[pid], pid, total) for pid, total in sorted_franchise[:limit]]

    def get_league_season_leaders(self, season_id, tier, stat_category, limit=5):
        """Isolates a specific season and tier to find league leaders."""
        season_tier_records = [
            r for r in self.records 
            if str(r.get("SeasonID")) == str(season_id) and str(r.get("Tier")) == str(tier) and stat_category in r and r[stat_category] != ""
        ]
        sorted_leaders = sorted(season_tier_records, key=lambda x: float(x[stat_category]), reverse=True)
        return [(r["Name"], r["TeamID"], float(r[stat_category])) for r in sorted_leaders[:limit]]