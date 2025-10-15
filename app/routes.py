from flask import Blueprint, redirect, url_for, session, render_template, flash, request, jsonify, current_app
from flask_dance.contrib.google import google
from sqlalchemy import func
from . import db
from .models import User, LoginSession
from datetime import datetime

bp = Blueprint("auth", __name__)

# ----- INDEX -----
@bp.route("/")
def index():
    user_id = session.get("user_id")
    return render_template("index.html", logged_in=bool(user_id))

# ----- LOGIN -----
@bp.route("/login/google")
def google_login():
    """Redirect the user to Google OAuth login page"""
    return redirect(url_for("google.login"))

# ----- DASHBOARD -----
from flask_dance.contrib.google import google

@bp.route("/dashboard")
def dashboard():
    # --- Step 1: Check Google OAuth authorization ---
    if not google.authorized:
        return redirect(url_for("google.login"))

    # --- Step 2: Get user info from Google ---
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return redirect(url_for("auth.index"))

    info = resp.json()
    email = info.get("email")
    name = info.get("name")

    # --- Step 3: Retrieve or create user in DB ---
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, name=name)
        db.session.add(user)
        db.session.commit()
        flash("Account created via Google!", "success")

    # --- Step 4: Set session info ---
    session["user_id"] = user.id
    session["user_name"] = user.name
    session["user_email"] = user.email
    session.permanent = True
    login_time_str = session.get("login_time")
    
    # --- Step 5: Handle login session tracking ---
    if not login_time_str:
        new_session = LoginSession(user_id=user.id)
        db.session.add(new_session)
        db.session.commit()
        session["login_session_id"] = new_session.id
        session["login_time"] = new_session.login_time.isoformat()
        login_time = new_session.login_time
    else:
        login_time = datetime.fromisoformat(login_time_str)

    # --- Step 6: Check session timeout ---
    if (datetime.utcnow() - login_time).total_seconds() > 120 * 60:
        flash("Session expired after 2 hours. Please log in again.", "warning")
        return redirect(url_for("auth.logout"))

    # --- Step 7: Calculate total active time ---
    total_active_seconds = db.session.query(
        func.coalesce(func.sum(LoginSession.active_time_seconds), 0)
    ).filter_by(user_id=user.id).scalar()

    # --- Step 8: Render dashboard ---
    return render_template(
        "dashboard.html",
        total_active_minutes=total_active_seconds // 60,
        total_active_seconds=total_active_seconds % 60,
        user_name=user.name
    )

# ----- GOOGLE AUTH CALLBACK -----
@bp.route("/login/google/authorized")
def google_authorized():
    # Debug: print current session keys
    current_app.logger.info("Session keys: %s", list(session.keys()))
    
    if not google.authorized:
        # Debug: check token
        token = google.token
        current_app.logger.warning("Google not authorized. Token: %s", token)
        flash("Google login required.", "warning")
        return redirect(url_for("auth.google_login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        current_app.logger.error("Failed to fetch user info: %s", resp.text)
        flash("Failed to fetch user info from Google.", "danger")
        return redirect(url_for("auth.index"))

    info = resp.json()
    email = info.get("email")
    name = info.get("name")

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, name=name)
        db.session.add(user)
        db.session.commit()
        flash("Account created via Google!", "success")

    # Set session
    session["user_id"] = user.id
    session.permanent = True
    new_session = LoginSession(user_id=user.id)
    db.session.add(new_session)
    db.session.commit()

    session["login_session_id"] = new_session.id
    session["login_time"] = new_session.login_time.isoformat()
    session["user_name"] = user.name
    session["user_email"] = user.email
    flash(f"Logged in as {user.name}!", "success")

    current_app.logger.info("User %s logged in successfully.", user.email)
    return redirect(url_for("auth.dashboard"))

# ----- LOGOUT -----
@bp.route("/logout")
def logout():
    login_session_id = session.get("login_session_id")
    if login_session_id:
        login_session = LoginSession.query.get(login_session_id)
        if login_session and not login_session.logout_time:
            login_session.logout_time = datetime.utcnow()
            login_session.duration_minutes = int(
                (login_session.logout_time - login_session.login_time).total_seconds() / 60
            )
            db.session.commit()

    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.index"))

# ----- UPDATE ACTIVE TIME -----
@bp.route("/update_active_time", methods=["POST"])
def update_active_time():
    if "login_session_id" not in session:
        return jsonify({"error": "not logged in"}), 403

    try:
        data = request.get_json(force=True)
        delta_seconds = int(data.get("active_seconds", 0))
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400

    if delta_seconds <= 0:
        return jsonify({"status": "nothing to update"})

    login_session = LoginSession.query.get(session["login_session_id"])
    if not login_session:
        return jsonify({"error": "login session not found"}), 404

    if login_session.active_time_seconds is None:
        login_session.active_time_seconds = 0

    login_session.active_time_seconds += delta_seconds
    db.session.commit()

    return jsonify({"status": "ok", "total_active_seconds": login_session.active_time_seconds})

# ----- LEADERBOARD -----
@bp.route("/leaderboard")
def leaderboard():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.index"))

    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except ValueError:
        page = 1
        per_page = 10

    query = (
        db.session.query(
            User.id,
            User.name,
            User.email,
            func.coalesce(func.sum(LoginSession.active_time_seconds), 0).label("total_active_seconds")
        )
        .join(LoginSession, LoginSession.user_id == User.id)
        .group_by(User.id)
        .order_by(func.sum(LoginSession.active_time_seconds).desc())
    )

    total_users = query.count()
    leaderboard_data = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total_users + per_page - 1) // per_page

    return render_template(
        "leaderboard.html",
        leaderboard=leaderboard_data,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
