from . import db, bcrypt



from datetime import datetime, timedelta



class LoginSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)
    active_time_seconds = db.Column(db.Integer, default=0)  # 👈 new

    user = db.relationship("User", backref="login_sessions")

    def end_session(self):
        """Call this when the user logs out or times out."""
        self.logout_time = datetime.utcnow()
        self.duration_minutes = int((self.logout_time - self.login_time).total_seconds() / 60)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    password_hash = db.Column(db.String(128))


    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
