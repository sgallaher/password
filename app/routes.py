from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from .models import User
from . import db, bcrypt, mail  # include mail here
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
import os

auth_bp = Blueprint("auth", __name__)

LOCKOUT_TIMES = [timedelta(minutes=1), timedelta(hours=1), timedelta(hours=24)]

def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(os.environ.get("SECRET_KEY"))
    return serializer.dumps(email, salt="password-reset-salt")

def verify_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(os.environ.get("SECRET_KEY"))
    try:
        email = serializer.loads(token, salt="password-reset-salt", max_age=expiration)
    except:
        return None
    return email


@auth_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            flash("Please fill in all fields", "warning")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "danger")
            return redirect(url_for("auth.register"))

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Invalid email or password", "danger")
            return redirect(url_for("auth.login"))

        if user.disabled:
            flash("Account disabled. Contact support.", "danger")
            return redirect(url_for("auth.login"))

        if user.lockout_until and datetime.utcnow() < user.lockout_until:
            wait = int((user.lockout_until - datetime.utcnow()).total_seconds() // 60)
            flash(f"Account locked. Try again in {wait} minute(s).", "warning")
            return redirect(url_for("auth.login"))

        if user.check_password(password):
            user.failed_attempts = 0
            user.lockout_until = None
            db.session.commit()
            session["user_id"] = user.id
            flash("Logged in successfully!", "success")
            return redirect(url_for("auth.dashboard"))
        else:
            user.failed_attempts += 1
            if user.failed_attempts >= 3:
                if not user.lockout_until:
                    user.lockout_until = datetime.utcnow() + LOCKOUT_TIMES[0]
                elif (user.lockout_until - datetime.utcnow()).total_seconds() < 3600:
                    user.lockout_until = datetime.utcnow() + LOCKOUT_TIMES[1]
                elif (user.lockout_until - datetime.utcnow()).total_seconds() < 86400:
                    user.lockout_until = datetime.utcnow() + LOCKOUT_TIMES[2]
                else:
                    user.disabled = True
                user.failed_attempts = 0
            db.session.commit()
            flash("Invalid password", "danger")
            return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out", "info")
    return redirect(url_for("auth.index"))


@auth_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html")


@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Email not found", "danger")
            return redirect(url_for("auth.forgot_password"))

        token = generate_reset_token(user.email)
        reset_url = url_for("auth.reset_password", token=token, _external=True)

        msg = Message(
            subject="Password Reset Request",
            sender=os.environ.get("EMAIL_USER"),
            recipients=[user.email],
            body=f"Click the link to reset your password: {reset_url}\nThis link expires in 1 hour."
        )
        mail.send(msg)
        flash("Password reset email sent!", "info")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash("Invalid or expired token", "danger")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(email=email).first()
    if request.method == "POST":
        password = request.form.get("password")
        if not password:
            flash("Password cannot be empty", "warning")
            return redirect(url_for("auth.reset_password", token=token))

        user.set_password(password)
        db.session.commit()
        flash("Password reset successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")
