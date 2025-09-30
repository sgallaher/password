from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from .models import User
from . import db, bcrypt

# Define the blueprint
auth_bp = Blueprint("auth", __name__)

# Lockout timings
LOCKOUT_TIMES = [timedelta(minutes=1), timedelta(hours=1), timedelta(hours=24)]

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
                # Determine lockout level
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
