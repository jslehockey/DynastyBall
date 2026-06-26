# ==========================================
# gameSim_weather.py
# ==========================================
# Handles daily weather generation and retrieval for the league.
# ==========================================
import random

class LeagueWeatherSystem:
    def __init__(self):
        self.daily_forecasts = {}

    def generate_daily_weather(self, day_number, teams):
        """Generates a unique forecast for every home stadium for the given day."""
        self.daily_forecasts[day_number] = {}
        for team in teams:
            temp = random.randint(45, 95)
            wind_speed = random.randint(0, 20)
            wind_direction = random.choice(["Blowing In", "Blowing Out", "Crosswind Left", "Crosswind Right", "Calm"])
            precipitation = random.choices(["None", "Rain"], weights=[85, 15])[0] 
            
            self.daily_forecasts[day_number][team] = {
                "temp": temp,
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "precipitation": precipitation
            }

    def get_game_weather(self, day_number, home_team):
        """Fetches the specific weather for the home stadium."""
        return self.daily_forecasts.get(day_number, {}).get(home_team, {
            "temp": 70, "wind_speed": 0, "wind_direction": "Calm", "precipitation": "None"
        })