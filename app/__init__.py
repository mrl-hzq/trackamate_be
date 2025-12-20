from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from config import Config
import os

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS Configuration - Allow all origins for development
    CORS(app,
         resources={r"/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Type"],
             "supports_credentials": False  # Changed to False when using "*" origin
         }})

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    @app.route('/status', methods=['GET'])
    def new_api():
        return f'OK'

    # Static file serving for uploaded images
    @app.route('/uploads/<folder>/<filename>')
    def uploaded_file(folder, filename):
        """Serve uploaded files (burn, invest, commit images)"""
        upload_dir = app.config['UPLOAD_FOLDER']
        return send_from_directory(os.path.join(upload_dir, folder), filename)

    from app.views.auth import user_bp
    app.register_blueprint(user_bp, url_prefix="/user")

    from app.views.food import food_bp
    app.register_blueprint(food_bp, url_prefix="/food")

    from app.views.income import income_bp
    app.register_blueprint(income_bp, url_prefix="/income")

    from app.views.burn import burn_bp
    app.register_blueprint(burn_bp, url_prefix="/burn")

    from app.views.invest import invest_bp
    app.register_blueprint(invest_bp, url_prefix="/invest")

    from app.views.commit import commit_bp
    app.register_blueprint(commit_bp, url_prefix="/commit")

    from app.views.note import note_bp
    app.register_blueprint(note_bp, url_prefix="/note")

    from app.views.weight import weight_bp
    app.register_blueprint(weight_bp, url_prefix="/weight")

    from app.views.nutrition import nutrition_bp
    app.register_blueprint(nutrition_bp, url_prefix="/nutrition")

    from app.views.analytics import analytics_bp
    app.register_blueprint(analytics_bp, url_prefix="/analytics")

    return app
