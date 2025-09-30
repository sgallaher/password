from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from models import db, User
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
mail = Mail(app)

LOCKOUT_TIMES = [timedelta(minutes=1), timedelta(hours=1), timedelta(hours=24)]

@app.before_first_request
def create_tables():
    db.create_all()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("register"))
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created, please log in")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Invalid email or password")
            return redirect(url_for("login"))

        if user.is_disabled:
            flash("Account disabled. Contact support.")
            return redirect(url_for("login"))

        if user.lockout_until and datetime.utcnow() < user.lockout_until:
            flash(f"Account locked until {user.lockout_until}")
            return redirect(url_for("login"))

        if user.check_password(password):
            user.failed_attempts = 0
            user.lockout_until = None
            db.session.commit()
            session["user_id"] = user.id
            flash("Login successful")
            return redirect(url_for("index"))
        else:
            user.failed_attempts += 1
            if user.failed_attempts >= 3:
                if user.lockout_level < 3:
                    user.lockout_until = datetime.utcnow() + LOCKOUT_TIMES[user.lockout_level]
                    user.lockout_level += 1
                else:
                    user.is_disabled = True
                user.failed_attempts = 0
            db.session.commit()
            flash("Invalid password")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out")
    return redirect(url_for("index"))

@app.route("/reset_request", methods=["GET", "POST"])
def reset_request():
    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            msg = Message("Password Reset Request",
                          sender="noreply@example.com",
                          recipients=[user.email])
            link = url_for("reset_token", token=token, _external=True)
            msg.body = f"Click to reset: {link}"
            mail.send(msg)
            flash("Password reset link sent to your email")
        else:
            flash("Email not found")
        return redirect(url_for("login"))
    return render_template("reset_request.html")

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_token(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        flash("Invalid or expired token")
        return redirect(url_for("reset_request"))

    if request.method == "POST":
        password = request.form["password"]
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash("Password reset successful. Please login.")
        return redirect(url_for("login"))

    return render_template("reset_token.html")
