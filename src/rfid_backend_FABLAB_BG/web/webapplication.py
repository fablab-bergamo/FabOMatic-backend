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
app.config["SQLALCHEMY_DATABASE_URI"] = getSetting("database", "url")

engine = create_engine(getSetting("database", "url"), echo=False)
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


@app.route("/interventions")
def view_interventions():
    session = DBSession()
    interventions = session.query(Intervention).all()
    return render_template("view_interventions.html", interventions=interventions)


@app.route("/interventions/add", methods=["GET", "POST"])
def add_intervention():
    session = DBSession()
    machines = session.query(Machine).order_by(Machine.machine_id).all()
    users = session.query(User).order_by(User.user_id).all()
    maintenances = session.query(Maintenance).order_by(Maintenance.maintenance_id).all()

    if request.method == "POST":
        maintenance_id = request.form["maintenance_id"]
        machine_id = request.form["machine_id"]
        user_id = request.form["user_id"]
        timestamp = time()

        intervention = Intervention(
            maintenance_id=maintenance_id, machine_id=machine_id, user_id=user_id, timestamp=timestamp
        )

        session.add(intervention)
        session.commit()

        return redirect(url_for("view_interventions"))
    else:
        return render_template("add_intervention.html", machines=machines, users=users, maintenances=maintenances)


@app.route("/interventions/edit/<int:intervention_id>", methods=["GET", "POST"])
def edit_intervention(intervention_id):
    session = DBSession()
    intervention = session.query(Intervention).get(intervention_id)
    machines = session.query(Machine).order_by(Machine.machine_id).all()
    users = session.query(User).order_by(User.user_id).all()
    maintenances = session.query(Maintenance).order_by(Maintenance.maintenance_id).all()

    if request.method == "POST":
        intervention.maintenance_id = request.form["maintenance_id"]
        intervention.machine_id = request.form["machine_id"]
        intervention.user_id = request.form["user_id"]
        intervention.timestamp = time()

        session.add(intervention)
        session.commit()

        return redirect(url_for("view_interventions"))
    else:
        return render_template(
            "edit_intervention.html",
            intervention=intervention,
            machines=machines,
            users=users,
            maintenances=maintenances,
        )


@app.route("/interventions/delete/<int:intervention_id>", methods=["GET", "POST"])
def delete_intervention(intervention_id):
    session = DBSession()
    intervention = session.query(Intervention).get(intervention_id)

    if not intervention:
        return "Intervention not found", 404

    if request.method == "POST":
        session.delete(intervention)
        session.commit()

        return redirect(url_for("view_interventions"))

    return render_template("delete_intervention.html", intervention=intervention)


@app.route("/machines/history/<int:machine_id>", methods=["GET"])
def view_machine_use_history(machine_id):
    session = DBSession()
    uses = session.query(Use).filter_by(machine_id=machine_id).order_by(Use.start_timestamp).all()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    if machine is None:
        return "Machine not found", 404

    return render_template("view_machine_use_history.html", uses=uses, machine=machine)


@app.route("/delete_use/<int:use_id>", methods=["POST"])
def delete_use(use_id):
    session = DBSession()
    use = session.query(Use).filter_by(use_id=use_id).one()
    if use:
        session.delete(use)
        session.commit()
        flash("Use deleted successfully.")
    else:
        return "Use not found.", 404
    return redirect(url_for("view_uses"))


@app.route("/view_uses", methods=["GET"])
def view_uses():
    session = DBSession()
    user_id = request.args.get("user_id")
    machine_id = request.args.get("machine_id")
    start_time = request.args.get("start_time")

    # Convert start_time to a datetime object
    if start_time:
        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")

    # Query the database to get the data
    uses = session.query(Use)

    if user_id:
        uses = uses.filter(Use.user_id == user_id)

    if machine_id:
        uses = uses.filter(Use.machine_id == machine_id)

    if start_time:
        uses = uses.filter(Use.start_timestamp >= start_time)

    uses = uses.all()

    # Query the database to get all users and machines for the filter dropdowns
    all_users = session.query(User).all()
    all_machines = session.query(Machine).all()

    return render_template(
        "view_uses.html",
        uses=uses,
        all_users=all_users,
        all_machines=all_machines,
        selected_user_id=user_id,
        selected_machine_id=machine_id,
        selected_start_time=start_time,
    )


@app.route("/logout")
def logout():
    # here you would add your logout logic, like clearing session, etc.
    # then redirect to the login page (or wherever you want)
    return redirect(url_for("login"))


@app.route("/authorizations", methods=["GET"])
def view_authorizations():
    session = DBSession()
    authorizations = session.query(Authorization).all()
    return render_template("view_authorizations.html", authorizations=authorizations)


@app.route("/authorizations/add", methods=["GET"])
def add_authorization():
    session = DBSession()
    users = session.query(User).all()
    machines = session.query(Machine).all()
    return render_template("add_authorization.html", users=users, machines=machines)


@app.route("/authorizations/create", methods=["POST"])
def create_authorization():
    session = DBSession()
    authorization_data = request.form
    new_authorization = Authorization(
        user_id=authorization_data["user_id"],
        machine_id=authorization_data["machine_id"],
    )
    session.add(new_authorization)
    session.commit()
    return redirect(url_for("view_authorizations"))


@app.route("/authorizations/edit/<int:authorization_id>", methods=["GET"])
def edit_authorization(authorization_id):
    session = DBSession()
    authorization = session.query(Authorization).all()
    users = session.query(User).all()
    machines = session.query(Machine).all()
    if authorization:
        return render_template("edit_authorization.html", authorization=authorization, users=users, machines=machines)
    else:
        return "Authorization not found", 404


@app.route("/authorizations/update", methods=["POST"])
def update_authorization():
    session = DBSession()
    authorization_data = request.form
    authorization = (
        session.query(Authorization).filter_by(authorization_id=authorization_data["authorization_id"]).one()
    )
    if authorization:
        authorization.user_id = authorization_data["user_id"]
        authorization.machine_id = authorization_data["machine_id"]
        session.commit()
        return redirect(url_for("view_authorizations"))
    else:
        return "Authorization not found", 404


@app.route("/authorizations/delete/<int:authorization_id>", methods=["GET", "POST"])
def delete_authorization(authorization_id):
    session = DBSession()
    authorization = session.query(Authorization).filter_by(authorization_id=authorization_id).one()
    if not authorization:
        return "Authorization not found", 404

    if request.method == "POST":
        session.delete(authorization)
        session.commit()
        return redirect(url_for("view_authorizations"))

    return render_template("delete_authorization.html", authorization=authorization)

@app.route("/about")
def about():
    return render_template("about.html")
