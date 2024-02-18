""" This module contains the web application and common functions. """

# pylint: disable=C0116

from datetime import datetime
import os
from time import time

from flask import Flask, render_template, send_from_directory
from flask_login import login_required
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rfid_backend_FABLAB_BG.database.models import Base, Machine
from rfid_backend_FABLAB_BG.database.DatabaseBackend import getSetting, getDatabaseUrl
from rfid_backend_FABLAB_BG.database.repositories import MachineRepository

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLASK_TEMPLATES_FOLDER = os.path.join(MODULE_DIR, "flask_app", "templates")
FLASK_STATIC_FOLDER = os.path.join(MODULE_DIR, "flask_app", "static")
UPLOAD_FOLDER = os.path.join(MODULE_DIR, "flask_app", "upload")
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

app = Flask(__name__, template_folder=FLASK_TEMPLATES_FOLDER, static_folder=FLASK_STATIC_FOLDER)
app.config["SECRET_KEY"] = getSetting("web", "secret_key")

engine = create_engine(getDatabaseUrl(), echo=False)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


from datetime import datetime
from jinja2 import Environment


def timestamp_to_datetime(value):
    return datetime.fromtimestamp(value)


# Add the filter to Jinja2's environment
app.jinja_env.filters["timestamp_to_datetime"] = timestamp_to_datetime


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


@app.template_filter("time_since")
def time_since(dt):
    now = datetime.now()

    if not isinstance(dt, datetime):
        dt = datetime.fromtimestamp(dt)

    diff = now - dt
    seconds = abs(diff.total_seconds())

    if seconds < 60:
        return f"{seconds} seconds ago"
    elif seconds < 3600:
        return f"{seconds // 60} minutes ago"
    elif seconds < 86400:
        return f"{seconds // 3600} hours ago"
    else:
        return f"{seconds // 86400} days ago"


# Define routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download_attachment/<filename>")
@login_required
def download_attachment(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/about")
def about():
    with DBSession() as session:
        machine_repo = MachineRepository(session)
        machines = machine_repo.get_all()
        for mac in machines:
            setattr(mac, "maintenance_needed", machine_repo.getMachineMaintenanceNeeded(mac.machine_id)[0])
            if mac.last_seen is None:
                setattr(mac, "online", False)
            else:
                setattr(mac, "online", time() - mac.last_seen < 180)
        return render_template("about.html", machines=machines)
