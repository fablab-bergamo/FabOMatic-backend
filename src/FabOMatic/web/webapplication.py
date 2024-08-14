""" This module contains the web application and common functions. """

# pylint: disable=C0116

from datetime import datetime
import os
from time import time

from flask import Flask, render_template, request, send_from_directory, g, session
from flask_login import login_required
from flask_babel import gettext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from FabOMatic.database.models import Base
from FabOMatic.database.DatabaseBackend import getSetting, getDatabaseUrl
from FabOMatic.database.repositories import MachineRepository
from flask_babel import Babel
import flask_excel as excel

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

# Init various extensions

excel.init_excel(app)


def get_locale():
    # if the user has set up the language manually it will be stored in the session,
    # so we use the locale from the user settings
    try:
        language = session["language"]
    except KeyError:
        language = None
    if language is not None:
        return language

    translations = [str(translation) for translation in babel.list_translations()]
    return request.accept_languages.best_match(translations)


def get_timezone():
    user = getattr(g, "user", None)
    if user is not None:
        return user.timezone


babel = Babel(
    app,
    locale_selector=get_locale,
    timezone_selector=get_timezone,
    default_timezone="Europe/Rome",
    default_locale="it",
    default_translation_directories=os.path.join(MODULE_DIR, "translations"),
)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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

    if hours > 1:
        hour_text = gettext("hours")
    else:
        hour_text = gettext("hour")

    if minutes > 1:
        minutes_text = gettext("minutes")
    else:
        minutes_text = gettext("minute")

    if hours == 0:
        if minutes == 0:
            return "-"
        return f"{minutes} {minutes_text}"

    return f"{hours} {hour_text} {minutes} {minutes_text}"


@app.template_filter("time_since")
def time_since(dt):
    now = datetime.now()

    if not isinstance(dt, datetime):
        try:
            value = int(dt)
            dt = datetime.fromtimestamp(value)
        except ValueError:
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")

    diff = now - dt
    seconds = int(abs(diff.total_seconds()))

    if seconds < 60:
        if seconds > 1:
            return f"{seconds} " + gettext("seconds ago")
        else:
            return f"{seconds} " + gettext("second ago")
    elif seconds < 3600:
        if seconds // 60 > 1:
            return f"{seconds // 60} " + gettext("minutes ago")
        else:
            return f"{seconds // 60} " + gettext("minute ago")
    elif seconds < 86400:
        if seconds // 3600 > 1:
            return f"{seconds // 3600} " + gettext("hours ago")
        else:
            return f"{seconds // 3600} " + gettext("hour ago")
    else:
        if seconds // 86400 > 1:
            return f"{seconds // 86400} " + gettext("days ago")

    return f"{seconds // 86400} " + gettext("day ago")


# Define routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    with DBSession() as session:
        machine_repo = MachineRepository(session)
        machines = machine_repo.get_all()
        for mac in machines:
            setattr(mac, "maintenance_needed", machine_repo.getMachineMaintenanceNeeded(mac.machine_id)[0])
        return render_template("about.html", machines=machines)
