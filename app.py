from flask import Flask
from extensions import db
from app_routes import main_bp

# 1. Initialize the app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\Users\jsleh\Documents\SimGame\diamondbucs_test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 2. Connect the Database
db.init_app(app)

# 3. Register the Blueprint
app.register_blueprint(main_bp)

if __name__ == "__main__":
    app.run(debug=True)