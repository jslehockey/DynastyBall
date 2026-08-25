from app import app
from extensions import db
# Importing the models ensures SQLAlchemy knows what tables to build
import model_league
import model_team
import model_stadium
import model_bid
import model_player

with app.app_context():
    db.create_all()
    print("Success! Pristine database tables generated in diamondbucs_test.db.")