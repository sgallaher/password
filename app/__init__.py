from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_dance.contrib.google import make_google_blueprint
import os
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta

db = SQLAlchemy()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "devsecret")

    # Trust proxy headers (Codespaces / Render)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


    # Session config
    app.permanent_session_lifetime = timedelta(minutes=120)
# Session cookies
    if os.environ.get("FLASK_ENV") == "production":
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    else:
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['SESSION_COOKIE_SAMESITE'] = None



    # Database
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True
}
    db.init_app(app)
    bcrypt.init_app(app)

    # Session timeout
    app.permanent_session_lifetime = timedelta(minutes=120)

    # --- GOOGLE OAUTH ---
    # Use environment variable to choose redirect URL dynamically

    google_bp = make_google_blueprint(
        client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
        scope=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid"
        ],
        redirect_to="auth.dashboard"  # <-- Flask endpoint
    )
    google_bp.backend = None  # store token in session (default)
    app.register_blueprint(google_bp, url_prefix="/login")

    # Register routes
    from . import routes
    app.register_blueprint(routes.bp)

    # Create tables
    with app.app_context():
        db.create_all()

    
     # -----------------------------
    # App-level error handlers
    # -----------------------------
    from flask import session, redirect, url_for, flash

    @app.errorhandler(404)
    def page_not_found(e):
        session.clear()
        flash("Page not found. Redirected to homepage.", "warning")
        return redirect(url_for("auth.index"))

    @app.errorhandler(401)
    @app.errorhandler(403)
    def unauthorized_error(e):
        session.clear()
        flash("Session expired or unauthorized. Please log in.", "warning")
        return redirect(url_for("auth.index"))

    return app
