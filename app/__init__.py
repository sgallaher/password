from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_bcrypt import Bcrypt
import os

db = SQLAlchemy()
mail = Mail()
bcrypt = Bcrypt()


def create_app():
    app = Flask(__name__)
    







def create_app():
    app = Flask(__name__)

    # Config
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "devkey")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get("EMAIL_USER")
    app.config['MAIL_PASSWORD'] = os.environ.get("EMAIL_PASS")

    db.init_app(app)

    # Only create tables if they don't exist
    with app.app_context():
        # This checks existing tables before creating new ones
        existing_tables = db.inspect(db.engine).get_table_names()
        if 'users' not in existing_tables:
            db.create_all()
            print("Tables created!")
    mail.init_app(app)
    bcrypt.init_app(app)

    # Register blueprint
    from .routes import auth_bp
    app.register_blueprint(auth_bp)

    return app
