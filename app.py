from flask import Flask
from extensions import db
import os
from app_routes import main_bp
from dotenv import load_dotenv

# Load the hidden variables from the .env file
load_dotenv()

# 1. Initialize the app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\Users\jsleh\Documents\SimGame\diamondbucs_test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Pull the secret key securely from the environment
app.secret_key = os.environ.get("SECRET_KEY")

# 2. Connect the Database
db.init_app(app)

# 3. Register the Blueprint
app.register_blueprint(main_bp)

if __name__ == "__main__":
    app.run(debug=True)

class Game(db.Model):
    __tablename__ = 'games'
    __table_args__ = {'extend_existing': True}
    game_id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.Integer, nullable=False)
    competition = db.Column(db.String(50), nullable=False)
    home_team_id = db.Column(db.Integer, nullable=False)
    away_team_id = db.Column(db.Integer, nullable=False)
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='Pre-game')

class GameEvent(db.Model):
    __tablename__ = 'game_events'
    __table_args__ = {'extend_existing': True}
    event_id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.game_id'), nullable=False)
    event_index = db.Column(db.Integer, nullable=False)
    inning = db.Column(db.Integer, nullable=False)
    half_inning = db.Column(db.String(10), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    player_name = db.Column(db.String(100))
    event_text = db.Column(db.Text, nullable=False)
    pitch_log = db.Column(db.Text)
    outs_after = db.Column(db.Integer, default=0)
    home_score_after = db.Column(db.Integer, default=0)
    away_score_after = db.Column(db.Integer, default=0)
    runner_1b = db.Column(db.String(100))
    runner_2b = db.Column(db.String(100))
    runner_3b = db.Column(db.String(100))