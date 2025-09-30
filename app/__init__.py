from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
import os

db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)

    # Config from environment (Render injects them)
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "devkey")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Email config
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get("EMAIL_USER")
    app.config['MAIL_PASSWORD'] = os.environ.get("EMAIL_PASS")

    db.init_app(app)
    mail.init_app(app)

    from .routes import auth_bp
    app.register_blueprint(auth_bp)

    return app
