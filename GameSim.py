# ==========================================
# GameSim.py (Master Controller)
# ==========================================
import random
import time

# FIXED IMPORTS: 
from extensions import db
from app import app, Game, GameEvent 
from sqlalchemy import text

from model_league import LeagueEnvironment
from flow_fullGame import FullGame
from gameSim_weather import LeagueWeatherSystem

# --- DELEGATED MODULES ---
import gameSim_builder as builder
import gameSim_reporter as reporter
import gameSim_economy as economy
import gameSim_season as season

class SimulationEngine:
    def __init__(self):
        # 2. State (Populated dynamically via builder)
        self.teams = [] 
        self.team_ids = {}
        self.rosters = {}
        self.parks = {} 
        self.standings = {}
        
        # 3. Game/Season Memory
        self.game_log = []
        self.boxscores = []
        self.player_stats = {}
        self.current_day = 0
        self.weather_system = LeagueWeatherSystem()
        self.record_book = None # Loaded in builder

    def _get_win_pct(self, team_name):
        w = self.standings[team_name]["W"]
        l = self.standings[team_name]["L"]
        return w / (w + l) if (w + l) > 0 else 0.500

    def _count_superstars(self, team_obj):
        count = 0
        for p in team_obj.lineup + team_obj.game_pitchers:
            if p and len(p.traits) >= 2: count += 1 
        return count

    def get_schedule_for_day(self, day_index):
        num_teams = len(self.teams)
        if num_teams < 2: 
            return []
            
        teams = self.teams.copy()
        round_num = day_index % (num_teams - 1)
        
        if round_num > 0:
            teams = teams[:1] + teams[-round_num:] + teams[1:-round_num]
            
        matchups = []
        half = num_teams // 2
        
        for i in range(half):
            team_a = teams[i]
            team_b = teams[-1 - i]
            
            if i % 2 == round_num % 2:
                matchups.append((team_a, team_b))
            else:
                matchups.append((team_b, team_a))
                
        return matchups

    def simulate_game(self, away_team, home_team, match_type="Regular"):
        away_games = self.standings[away_team]["W"] + self.standings[away_team]["L"]
        home_games = self.standings[home_team]["W"] + self.standings[home_team]["L"]
        
        away_sp_role = f"SP{(away_games % 5) + 1}"
        home_sp_role = f"SP{(home_games % 5) + 1}"

        away_obj = builder.build_team_object(self, away_team, away_sp_role)
        home_obj = builder.build_team_object(self, home_team, home_sp_role)

        h_park = self.parks.get(home_team, {})
        a_park = self.parks.get(away_team, {})

        active_stars = self._count_superstars(home_obj) + self._count_superstars(away_obj)

        attendance_data = economy.calculate_match_attendance(
            capacity=h_park.get("capacity", 30000),
            actual_price=h_park.get("ticket_price", 30.00),
            home_tier=h_park.get("tier", 1),
            away_tier=a_park.get("tier", 1),
            match_type=match_type,
            home_prestige=h_park.get("prestige", 50),
            home_win_pct=self._get_win_pct(home_team),
            away_prestige=a_park.get("prestige", 50),
            away_win_pct=self._get_win_pct(away_team),
            active_superstars=active_stars
        )
        
        modifiers = economy.get_homefield_modifiers(attendance_data["attendance"])

        away_hr_record = self.record_book.get_franchise_records(away_team, "HR", record_type="season", limit=1) if self.record_book else []
        home_hr_record = self.record_book.get_franchise_records(home_team, "HR", record_type="season", limit=1) if self.record_book else []
        
        target_hr_away = away_hr_record[0][3] if away_hr_record else 0
        target_hr_home = home_hr_record[0][3] if home_hr_record else 0

        env = LeagueEnvironment()
        local_weather = self.weather_system.get_game_weather(self.current_day, home_team)
        
        # Execute Core Game Engine
        game = FullGame(
            away_obj, home_obj, env, weather=local_weather, career_stats=self.player_stats, 
            hr_record_target_away=target_hr_away, hr_record_target_home=target_hr_home,
            attendance_data=attendance_data, modifiers=modifiers 
        )
        game.play_game()

        # =====================================
        # SAVE GAME SCRIPT TO SQLITE DATABASE
        # =====================================
        away_id = self.team_ids.get(away_team, 2)
        home_id = self.team_ids.get(home_team, 1)

        new_game = Game(
            season=self.current_day, 
            competition=match_type,
            home_team_id=int(home_id),
            away_team_id=int(away_id),
            home_score=game.home.stats["batting"]["R"],
            away_score=game.away.stats["batting"]["R"],
            status='Final'
        )
        db.session.add(new_game)
        db.session.commit()

        events_to_insert = []
        for index, ev in enumerate(game.game_events, start=1):
            events_to_insert.append(GameEvent(
                game_id=new_game.game_id,
                event_index=index,
                inning=ev["inning"],
                half_inning=ev["half"],
                event_type=ev["type"],
                player_name=ev["player"],
                event_text=ev["desc"],
                outs_after=ev["outs"],
                home_score_after=ev["home_score"],
                away_score_after=ev["away_score"],
                runner_1b=ev["r1"],
                runner_2b=ev["r2"],
                runner_3b=ev["r3"],
                pitch_log=ev.get("pitch_log", "")
            ))
            
        db.session.bulk_save_objects(events_to_insert)
        db.session.commit()
        print(f"  [DATABASE] Saved Game #{new_game.game_id} to SQLite!")

        # Adjust Standings
        away_runs = game.away.stats["batting"]["R"]
        home_runs = game.home.stats["batting"]["R"]
        
        if home_runs > away_runs:
            home_wl, away_wl = "W", "L"
            self.standings[home_team]["W"] += 1
            self.standings[away_team]["L"] += 1
        else:
            home_wl, away_wl = "L", "W"
            self.standings[home_team]["L"] += 1
            self.standings[away_team]["W"] += 1
            
        self.standings[home_team]["RS"] += home_runs
        self.standings[home_team]["RA"] += away_runs
        self.standings[away_team]["RS"] += away_runs
        self.standings[away_team]["RA"] += home_runs
        
        self.game_log.append([away_team, away_runs, away_wl, home_team, home_runs, home_wl])
        
        # Extract Post Game Stats
        self._extract_post_game_data(away_team, away_obj)
        self._extract_post_game_data(home_team, home_obj)

    def _extract_post_game_data(self, team_name, team_obj):
        all_players = team_obj.lineup + team_obj.game_pitchers + team_obj.bullpen
        for obj_player in all_players:
            if not obj_player: continue
            pid = str(obj_player.player_id)
            if pid in self.player_stats:
                s = self.player_stats[pid]
                b_stats = obj_player.stats["batting"]
                p_stats = obj_player.stats["pitching"]
                f_stats = obj_player.stats.get("defense", {"PO": 0, "A": 0, "E": 0, "TC": 0})
                
                if b_stats["PA"] > 0 or p_stats["Pitches"] > 0 or f_stats["TC"] > 0: 
                    s["G"] += 1
                
                for key in ["PA", "AB", "R", "H", "1B", "2B", "3B", "HR", "RBI", "BB", "HBP", "SB", "CS", "SF", "GIDP"]:
                    s[key] += b_stats.get(key, 0)
                s["K_bat"] += b_stats.get("K", 0) 
                
                s["Outs_pit"] = s.get("Outs_pit", 0) + p_stats["Outs"]
                for key in ["W", "L", "SV", "HLD", "BS", "ER", "CG", "SHO", "Pitches"]:
                    s[key] += p_stats.get(key, 0)
                s["H_allowed"] += p_stats.get("H", 0)
                s["R_allowed"] += p_stats.get("R", 0)
                s["HR_allowed"] += p_stats.get("HR", 0)
                s["BB_allowed"] += p_stats.get("BB", 0)
                s["HBP_allowed"] += p_stats.get("HBP", 0)
                s["K_pit"] += p_stats.get("K", 0)

                for key in ["PO", "A", "E", "TC"]:
                    s[key] += f_stats.get(key, 0)

    def _run_daily_slate(self, is_bye):
        if is_bye:
            print(f"\n[LEAGUE BYE DAY] All teams are resting and recovering stamina.")
        else:
            self.weather_system.generate_daily_weather(self.current_day, self.teams)
            matchups = self.get_schedule_for_day(self.current_day)
            for away, home in matchups:
                self.simulate_game(away, home, match_type="Regular")
            self.current_day += 1

    def simulate_next_block(self):
        # Defaulting to Block 1 for SQLite testing without the Google Sheets season logic
        block = 1 
        total_games_played = sum([self.standings[t]["W"] + self.standings[t]["L"] for t in self.teams])
        self.current_day = int(total_games_played / max(1, (len(self.teams) / 2)))

        print(f"\n" + "="*50)
        print(f"INITIATING SIM-STATE BLOCK {block}")
        print("="*50)
        
        for _ in range(4): self._run_daily_slate(is_bye=False)

def run_live_test_environment():
    print("BASEBALL FRANCHISE CLI")
    
    with app.app_context():
        # --- NEW: Drop the old broken tables so they can be rebuilt ---
        db.session.execute(text("DROP TABLE IF EXISTS game_events"))
        db.session.execute(text("DROP TABLE IF EXISTS games"))
        db.session.commit()
        
        # Now create them fresh with the perfect schema!
        db.create_all()  
        
        engine = SimulationEngine()
        builder.load_state_from_db(engine)
        
        print(f"\nReady to manually trigger Sim-State Block 1")
        input("\nPress ENTER to run the current block (or CTRL+C to quit)...")
        
        engine.simulate_next_block()
        print("\nBlock complete. Games have been saved to the database.")

if __name__ == "__main__":
    run_live_test_environment()