from datetime import datetime
import logging
import math
import re
import os
from time import time
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rfid_backend_FABLAB_BG.database.models import (
    Base,
    Role,
    MachineType,
    Machine,
    User,
    Authorization,
    Maintenance,
    Intervention,
)
from rfid_backend_FABLAB_BG.database.repositories import *
from rfid_backend_FABLAB_BG.database.DatabaseBackend import getSetting

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLASK_TEMPLATES_FOLDER = os.path.join(MODULE_DIR, "flask_app", "templates")
FLASK_STATIC_FOLDER = os.path.join(MODULE_DIR, "flask_app", "static")
UPLOAD_FOLDER = os.path.join(MODULE_DIR, "flask_app", "upload")
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

app = Flask(__name__, template_folder=FLASK_TEMPLATES_FOLDER, static_folder=FLASK_STATIC_FOLDER)
app.config["SECRET_KEY"] = getSetting("web", "secret_key")

engine = create_engine(getSetting("database", "url"), echo=False)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Custom filter for datetime formatting
@app.template_filter("datetimeformat")
def datetimeformat(value, format="%b %d, %Y %I:%M %p"):
    if value is None:
        return "-"
    if type(value) is not datetime:
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


@app.route("/maintenances")
def maintenances():
    session = DBSession()
    maintenances = session.query(Maintenance).all()
    return render_template("view_maintenances.html", maintenances=maintenances)


@app.route("/maintenances/add", methods=["GET", "POST"])
def add_maintenance():
    session = DBSession()
    logging.debug("Processing add_maintenance %s", request)
    if request.method == "POST":
        hours_between = request.form["hours_between"]
        description = request.form["description"]
        machine_id = request.form["machine_id"]
        attachment = None

        if "attachment" in request.files:
            file = request.files["attachment"]
            if file.filename != "" and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                attachment = filename
            else:
                logging.warning(f"Invalid file uploaded {file.filename}")

        maintenance = Maintenance(
            hours_between=hours_between, description=description, machine_id=machine_id, attachment=attachment
        )
        session.add(maintenance)
        session.commit()
        return redirect(url_for("maintenances"))
    else:
        machines = session.query(Machine).all()
        return render_template("add_maintenance.html", machines=machines)


@app.route("/maintenances/edit/<int:maintenance_id>", methods=["GET", "POST"])
def edit_maintenance(maintenance_id):
    session = DBSession()
    maintenance = session.query(Maintenance).filter_by(maintenance_id=maintenance_id).one()
    if request.method == "POST":
        maintenance.hours_between = request.form["hours_between"]
        maintenance.description = request.form["description"]
        maintenance.machine_id = request.form["machine_id"]
        maintenance.attachment = None
        if "attachment" in request.files:
            file = request.files["attachment"]
            if file.filename != "" and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                maintenance.attachment = filename
            else:
                logging.warning(f"Invalid file uploaded {file.filename}")
        session.add(maintenance)
        session.commit()
        return redirect(url_for("maintenances"))
    else:
        machines = session.query(Machine).all()
        return render_template(
            "edit_maintenance.html",
            machines=machines,
            maintenance_id=maintenance.maintenance_id,
            maintenance=maintenance,
        )


@app.route("/maintenances/delete/<int:maintenance_id>", methods=["GET", "POST"])
def delete_maintenance(maintenance_id):
    session = DBSession()
    maintenance = session.query(Maintenance).filter_by(maintenance_id=maintenance_id).one()
    if not maintenance:
        return "Maintenance not found", 404

    if request.method == "POST":
        session.delete(maintenance)
        session.commit()
        flash("Maintenance deleted successfully.")
        return redirect(url_for("maintenances"))

    return render_template("delete_maintenance.html", maintenance=maintenance)


@app.route("/machinetypes")
def machinetypes():
    session = DBSession()
    machine_types = session.query(MachineType).all()
    return render_template("view_machinetypes.html", machine_types=machine_types)


@app.route("/machinetypes/add", methods=["GET", "POST"])
def add_machinetype():
    if request.method == "POST":
        session = DBSession()
        type_name = request.form["type_name"]
        machine_type = MachineType(type_name=type_name)
        session.add(machine_type)
        session.commit()
        return redirect(url_for("machinetypes"))
    else:
        return render_template("add_machinetype.html")


@app.route("/machinetypes/edit/<int:type_id>", methods=["GET", "POST"])
def edit_machinetype(type_id):
    session = DBSession()
    machine_type = session.query(MachineType).filter_by(type_id=type_id).one()
    if request.method == "POST":
        machine_type.type_name = request.form["type_name"]
        session.add(machine_type)
        session.commit()
        return redirect(url_for("machinetypes"))
    else:
        return render_template("edit_machinetype.html", type_id=machine_type.type_id, machine_type=machine_type)


@app.route("/machinetypes/delete/<int:type_id>", methods=["GET", "POST"])
def delete_machinetype(type_id):
    session = DBSession()
    machine_type = session.query(MachineType).filter_by(type_id=type_id).one()
    if not machine_type:
        return "Machine Type not found", 404
    if request.method == "POST":
        session.delete(machine_type)
        session.commit()
        flash("Machine type deleted successfully.")
        return redirect(url_for("machinetypes"))
    return render_template("delete_machinetype.html", machine_type=machine_type)


@app.route("/roles")
def roles():
    session = DBSession()
    roles = session.query(Role).all()
    return render_template("view_roles.html", roles=roles)


@app.route("/roles/add", methods=["GET", "POST"])
def add_role():
    if request.method == "POST":
        session = DBSession()
        role_name = request.form["role_name"]
        authorize_all = request.form.get("authorize_all", "off") == "on"
        role = Role(role_name=role_name, authorize_all=authorize_all, reserved=False)
        session.add(role)
        session.commit()
        return redirect(url_for("roles"))
    else:
        return render_template("add_role.html")


@app.route("/roles/edit/<int:role_id>", methods=["GET", "POST"])
def edit_role(role_id):
    session = DBSession()
    role = session.query(Role).filter_by(role_id=role_id).one()

    # Block editing of reserved roles
    if not role:
        return "Role not found", 404

    if role.reserved:
        return "Cannot edit reserved role", 403

    if request.method == "POST":
        role.role_name = request.form["role_name"]
        role.authorize_all = request.form.get("authorize_all", "off") == "on"
        session.add(role)
        session.commit()
        return redirect(url_for("roles"))

    return render_template("edit_role.html", role_id=role.role_id, role=role)


@app.route("/roles/delete/<int:role_id>", methods=["GET", "POST"])
def delete_role(role_id):
    session = DBSession()
    role_repo = RoleRepository(session)
    role = role_repo.get_by_id(role_id)
    if not role:
        return "Role not found", 404
    if role.reserved:
        return "Cannot delete reserved role", 403

    if request.method == "POST":
        role_repo.delete(role)
        flash("Role deleted successfully.")
        return redirect(url_for("roles"))

    return render_template("delete_role.html", role=role)


@app.route("/machine_types")
def machine_types():
    session = DBSession()
    machine_types = session.query(MachineType).all()
    return render_template("machine_types.html", machine_types=machine_types)


@app.route("/machine_types/add", methods=["GET", "POST"])
def add_machine_type():
    if request.method == "POST":
        session = DBSession()
        type_name = request.form["type_name"]
        machine_type = MachineType(type_name=type_name)
        session.add(machine_type)
        session.commit()
        return redirect(url_for("machine_types"))
    else:
        return render_template("add_machine_type.html")


@app.route("/machine_types/edit/<int:type_id>", methods=["GET", "POST"])
def edit_machine_type(type_id):
    session = DBSession()
    machine_type = session.query(MachineType).filter_by(type_id=type_id).one()
    if request.method == "POST":
        machine_type.type_name = request.form["type_name"]
        session.add(machine_type)
        session.commit()
        return redirect(url_for("machine_types"))


@app.route("/users", methods=["GET"])
def view_users():
    session = DBSession()
    users = session.query(User).order_by(User.user_id).all()
    return render_template("view_users.html", users=users)


@app.route("/users/add", methods=["GET"])
def add_user():
    session = DBSession()
    roles = session.query(Role).order_by(Role.role_id).all()
    return render_template("add_user.html", roles=roles)


@app.route("/users/create", methods=["POST"])
def create_user():
    session = DBSession()
    user_data = request.form
    card_UUID = user_data.get("card_UUID", None)
    if card_UUID and not re.match(r"^[0-9A-Fa-f]{8}$", card_UUID):
        flash("Invalid card UUID. Please enter either 8 hexadecimal characters or leave it empty.", "error")
        return redirect(url_for("view_users"))

    new_user = User(
        name=user_data["name"],
        surname=user_data["surname"],
        role_id=user_data["role_id"],
        card_UUID=card_UUID,
    )
    session.add(new_user)
    session.commit()
    return redirect(url_for("view_users"))


@app.route("/users/edit/<int:user_id>", methods=["GET"])
def edit_user(user_id):
    session = DBSession()
    user = session.query(User).filter_by(user_id=user_id).one()
    roles = session.query(Role).order_by(Role.role_id).all()
    if user:
        return render_template("edit_user.html", user=user, roles=roles)
    else:
        return "User not found", 404


@app.route("/users/update", methods=["POST"])
def update_user():
    session = DBSession()
    user_data = request.form
    user = session.query(User).filter_by(user_id=user_data["user_id"]).one()
    if user:
        # Validate the card_UUID
        card_UUID = user_data.get("card_UUID", None)
        if card_UUID and not re.match(r"^[0-9A-Fa-f]{8}$", card_UUID):
            flash("Invalid card UUID. Please enter either 8 hexadecimal characters or leave it empty.", "error")
            return redirect(url_for("edit_user", user_id=user.user_id))
        user.name = user_data["name"]
        user.surname = user_data["surname"]
        user.role_id = user_data["role_id"]
        user.card_UUID = user_data.get("card_UUID", None)
        session.commit()
        return redirect(url_for("view_users"))
    else:
        return "User not found", 404


@app.route("/users/delete/<int:user_id>", methods=["GET", "POST"])
def delete_user(user_id):
    session = DBSession()
    user = session.query(User).filter_by(user_id=user_id).one()
    if not user:
        return "User not found", 404

    if request.method == "POST":
        session.delete(user)
        session.commit()
        return redirect(url_for("view_users"))

    return render_template("delete_user.html", user=user)


@app.route("/machines", methods=["GET"])
def view_machines():
    session = DBSession()
    machines = session.query(Machine).order_by(Machine.machine_id).all()
    return render_template("view_machines.html", machines=machines)


@app.route("/machines/add", methods=["GET"])
def add_machine():
    session = DBSession()
    machine_types = session.query(MachineType).order_by(MachineType.type_id).all()
    return render_template("add_machine.html", machine_types=machine_types)


@app.route("/machines/create", methods=["POST"])
def create_machine():
    session = DBSession()
    machine_data = request.form
    new_machine = Machine(
        machine_name=machine_data["machine_name"],
        machine_type_id=machine_data["machine_type_id"],
        machine_hours=float(machine_data["machine_hours"]),
        blocked=machine_data.get("blocked", "off") == "on",
    )
    session.add(new_machine)
    session.commit()
    return redirect(url_for("view_machines"))


@app.route("/machines/edit/<int:machine_id>", methods=["GET"])
def edit_machine(machine_id):
    session = DBSession()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    machine_types = session.query(MachineType).order_by(MachineType.type_id).all()
    if machine:
        return render_template("edit_machine.html", machine=machine, machine_types=machine_types)
    else:
        return "Machine not found", 404


@app.route("/machines/update", methods=["POST"])
def update_machine():
    session = DBSession()
    machine_data = request.form
    machine = session.query(Machine).filter_by(machine_id=machine_data["machine_id"]).one()
    if machine:
        machine.machine_name = machine_data["machine_name"]
        machine.machine_type_id = machine_data["machine_type_id"]
        machine.machine_hours = float(machine_data["machine_hours"])
        machine.blocked = machine_data.get("blocked", "off") == "on"
        session.commit()
        return redirect(url_for("view_machines"))
    else:
        return "Machine not found", 404


@app.route("/machines/delete/<int:machine_id>", methods=["GET", "POST"])
def delete_machine(machine_id):
    machine = Machine.query.get(machine_id)
    if not machine:
        return "Machine not found", 404

    if request.method == "POST":
        db.session.delete(machine)
        db.session.commit()
        return redirect(url_for("view_machines"))

    return render_template("delete_machine.html", machine=machine)
