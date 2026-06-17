import pandas as pd
import json # NEW: To handle the arrays
from datetime import datetime

class DataExporter:
    
    @staticmethod
    def export_game_log(game_id, date, away_team, home_team, linescore, scoring_plays, milestones):
        
        # We create ONE master row for the Game Summary table
        game_summary = {
            "GameID": game_id,
            "Date": date,
            "AwayTeam": away_team.name,
            "HomeTeam": home_team.name,
            "AwayRuns": away_team.stats["Runs"],
            "HomeRuns": home_team.stats["Runs"],
            
            # The Magic: Dumping complex arrays into strict JSON columns
            "Linescore": json.dumps(linescore),
            "ScoringPlays": json.dumps(scoring_plays),
            "Milestones": json.dumps(milestones) 
        }
        
        # Export the Game Summary (1 row per game)
        df_game = pd.DataFrame([game_summary])
        df_game.to_csv("diamondbucs_games.csv", mode='a', header=not pd.io.common.file_exists("diamondbucs_games.csv"), index=False)
        
        print(f"\n[DATA] Game Summary exported. Milestones detected: {len(milestones)}")
        for m in milestones:
            print(f"  -> {m}")
            