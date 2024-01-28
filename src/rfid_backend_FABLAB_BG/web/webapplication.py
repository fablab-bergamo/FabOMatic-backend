""" This module contains the web application and common functions. """
# pylint: disable=C0116

from datetime import datetime
import os
from time import time
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rfid_backend_FABLAB_BG.database.models import Base
from rfid_backend_FABLAB_BG.database.DatabaseBackend import getSetting

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLASK_TEMPLATES_FOLDER = os.path.join(MODULE_DIR, "flask_app", "templates")
FLASK_STATIC_FOLDER = os.path.join(MODULE_DIR, "flask_app", "static")
UPLOAD_FOLDER = os.path.join(MODULE_DIR, "flask_app", "upload")
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

app = Flask(__name__, template_folder=FLASK_TEMPLATES_FOLDER, static_folder=FLASK_STATIC_FOLDER)
app.config["SECRET_KEY"] = getSetting("web", "secret_key")

# Get the database URL
db_url = getSetting("database", "url")

# Check if it's a SQLite URL
if db_url.startswith("sqlite:///"):
    # Remove the prefix to get the file path
    file_path = db_url[len("sqlite:///") :]

    # Get the absolute path
    absolute_path = os.path.abspath(file_path)

    # Add the prefix back to get the absolute URL
    absolute_url = "sqlite:///" + absolute_path
else:
    # If it's not a SQLite URL, just use it as is
    absolute_url = db_url

# Use the absolute URL to create the engine
engine = create_engine(absolute_url, echo=False)
app.config["SQLALCHEMY_DATABASE_URI"] = str(engine.url)

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

db = SQLAlchemy(app)
migrate = Migrate(app, db)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Custom filter for datetime formatting
@app.template_filter("datetimeformat")
def datetimeformat(value, format="%b %d, %Y %I:%M %p"):
    if value is None:
        return "-"
    if not isinstance(value, datetime):
        value = datetime.fromtimestamp(value)
    return value.strftime(format)


@app.template_filter("format_hours")
def format_hours(value):
    if value is None:
        return "-"
    hours = int(value)
    minutes = int((value % 1) * 60)
    if hours == 0:
        if minutes == 0:
            return "-"
        else:
            return f"{minutes} minutes"
    return f"{hours} hours {minutes} minutes"


# Define routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download_attachment/<filename>")
def download_attachment(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/about")
def about():
    return render_template("about.html")
