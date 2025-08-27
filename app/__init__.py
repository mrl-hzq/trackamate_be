from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from config import Config

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    # CORS(app, resources={r"/*": {"origins": "http://localhost:5000"}}, supports_credentials=True)
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    @app.route('/status', methods=['GET'])
    def new_api():
        return f'OK'

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

    return app
