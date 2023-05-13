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

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLASK_TEMPLATES_FOLDER = os.path.join(MODULE_DIR, "flask_app", "templates")
FLASK_STATIC_FOLDER = os.path.join(MODULE_DIR, "flask_app", "static")

app = Flask(__name__, template_folder=FLASK_TEMPLATES_FOLDER, static_folder=FLASK_STATIC_FOLDER)

engine = create_engine("sqlite:///database.db")
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
    return render_template("roles.html", roles=roles)


@app.route("/roles/add", methods=["GET", "POST"])
def add_role():
    if request.method == "POST":
        session = DBSession()
        role_name = request.form["role_name"]
        authorize_all = request.form["authorize_all"] == "on"
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
        role.authorize_all = request.form["authorize_all"] == "on"
        session.add(role)
        session.commit()
        return redirect(url_for("roles"))
    else:
        return render_template("edit_role.html", role=role)


@app.route("/roles/delete/<int:role_id>", methods=["GET", "POST"])
def delete_role(role_id):
    session = DBSession()
    role = session.query(Role).filter_by(role_id=role_id).one()
    if request.method == "POST":
        session.delete(role)
        session.commit()
        return redirect(url_for("roles"))
    else:
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


@app.route("/machines", methods=["GET"])
def get_machines():
    session = DBSession()
    machines = session.query(Machine).all()
    return jsonify(
        [
            {
                "id": machine.id,
                "name": machine.name,
                "description": machine.description,
                "blocked": machine.blocked,
                "machine_type_id": machine.machine_type_id,
                "machine_hours": machine.machine_hours,
            }
            for machine in machines
        ]
    )
