import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://username:password@host:port/dbname"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("EMAIL_USER")  # your email
    MAIL_PASSWORD = os.environ.get("EMAIL_PASS")  # app password
