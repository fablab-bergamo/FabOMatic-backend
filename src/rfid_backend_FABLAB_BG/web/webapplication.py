import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
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

app = Flask(__name__, template_folder=FLASK_TEMPLATES_FOLDER, static_folder=FLASK_STATIC_FOLDER)

engine = create_engine(getSetting("database", "url"), echo=False)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


# Define routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


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
        role = Role(role_name=role_name, authorize_all=authorize_all)
        session.add(role)
        session.commit()
        return redirect(url_for("roles"))
    else:
        return render_template("add_role.html")


@app.route("/roles/edit/<int:role_id>", methods=["GET", "POST"])
def edit_role(role_id):
    session = DBSession()
    role = session.query(Role).filter_by(role_id=role_id).one()
    if request.method == "POST":
        role.role_name = request.form["role_name"]
        role.authorize_all = request.form.get("authorize_all", "off") == "on"
        session.add(role)
        session.commit()
        return redirect(url_for("roles"))
    else:
        return render_template("edit_role.html", role_id=role.role_id, role=role)


@app.route("/roles/delete/<int:role_id>", methods=["GET", "POST"])
def delete_role(role_id):
    session = DBSession()
    role_repo = RoleRepository(session)
    role = role_repo.get_by_id(role_id)
    if not role:
        return "Role not found", 404

    if request.method == "POST":
        role_repo.delete(role)
        return redirect(url_for("view_roles"))

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
    users = User.query.all()
    return render_template("view_users.html", users=users)


@app.route("/users/add", methods=["GET"])
def add_user():
    roles = Role.query.all()
    return render_template("add_user.html", roles=roles)


@app.route("/users/create", methods=["POST"])
def create_user():
    user_data = request.form
    new_user = User(
        name=user_data["name"],
        surname=user_data["surname"],
        role_id=user_data["role_id"],
        card_UUID=user_data.get("card_UUID", None),
    )
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for("view_users"))


@app.route("/users/edit/<int:user_id>", methods=["GET"])
def edit_user(user_id):
    user = User.query.get(user_id)
    roles = Role.query.all()
    if user:
        return render_template("edit_user.html", user=user, roles=roles)
    else:
        return "User not found", 404


@app.route("/users/update", methods=["POST"])
def update_user():
    user_data = request.form
    user = User.query.get(user_data["user_id"])
    if user:
        user.name = user_data["name"]
        user.surname = user_data["surname"]
        user.role_id = user_data["role_id"]
        user.card_UUID = user_data.get("card_UUID", None)
        db.session.commit()
        return redirect(url_for("view_users"))
    else:
        return "User not found", 404


@app.route("/users/delete/<int:user_id>", methods=["GET", "POST"])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return "User not found", 404

    if request.method == "POST":
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for("view_users"))

    return render_template("delete_user.html", user=user)


@app.route("/machines", methods=["GET"])
def view_machines():
    machines = Machine.query.all()
    return render_template("view_machines.html", machines=machines)


@app.route("/machines/add", methods=["GET"])
def add_machine():
    machine_types = MachineType.query.all()
    return render_template("add_machine.html", machine_types=machine_types)


@app.route("/machines/create", methods=["POST"])
def create_machine():
    machine_data = request.form
    new_machine = Machine(
        machine_name=machine_data["machine_name"],
        machine_type_id=machine_data["machine_type_id"],
        machine_hours=float(machine_data["machine_hours"]),
        blocked=machine_data.get("blocked", False),
    )
    db.session.add(new_machine)
    db.session.commit()
    return redirect(url_for("view_machines"))


@app.route("/machines/edit/<int:machine_id>", methods=["GET"])
def edit_machine(machine_id):
    machine = Machine.query.get(machine_id)
    machine_types = MachineType.query.all()
    if machine:
        return render_template("edit_machine.html", machine=machine, machine_types=machine_types)
    else:
        return "Machine not found", 404


@app.route("/machines/update", methods=["POST"])
def update_machine():
    machine_data = request.form
    machine = Machine.query.get(machine_data["machine_id"])
    if machine:
        machine.machine_name = machine_data["machine_name"]
        machine.machine_type_id = machine_data["machine_type_id"]
        machine.machine_hours = float(machine_data["machine_hours"])
        machine.blocked = machine_data.get("blocked", False)
        db.session.commit()
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
