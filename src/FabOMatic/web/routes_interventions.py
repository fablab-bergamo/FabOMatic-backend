""" This module contains the routes for the interventions. """

# pylint: disable=C0116

from datetime import datetime
from time import time

from flask import render_template, request, redirect, url_for
from flask_login import login_required
from flask_babel import gettext
from FabOMatic.database.models import Intervention, Machine, Maintenance, User
from .webapplication import DBSession, app, excel


@app.route("/interventions")
@login_required
def view_interventions():
    session = DBSession()
    users = session.query(User).filter_by(deleted=False).order_by(User.user_id).all()
    machines = session.query(Machine).order_by(Machine.machine_id).all()

    search_user = request.args.get("search_user_id")
    search_machine = request.args.get("search_machine_id")

    query = session.query(Intervention)

    if search_user and search_user.isdigit():
        search_user = int(search_user)
        query = query.filter(Intervention.user_id == search_user)
    if search_machine and search_machine.isdigit():
        search_machine = int(search_machine)
        query = query.filter(Intervention.machine_id == search_machine)

    interventions = query.limit(500).all()
    return render_template(
        "view_interventions.html",
        users=users,
        machines=machines,
        interventions=interventions,
        search_user_id=search_user,
        search_machine_id=search_machine,
    )


@app.route("/interventions/add", methods=["GET", "POST"])
@login_required
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
@login_required
def edit_intervention(intervention_id):
    session = DBSession()
    intervention = session.query(Intervention).get(intervention_id)
    machines = session.query(Machine).order_by(Machine.machine_id).all()
    users = session.query(User).filter_by(deleted=False).order_by(User.user_id).all()
    maintenances = session.query(Maintenance).order_by(Maintenance.maintenance_id).all()

    if request.method == "POST":
        intervention.maintenance_id = request.form["maintenance_id"]
        intervention.machine_id = request.form["machine_id"]
        intervention.user_id = request.form["user_id"]
        try:
            timestamp = datetime.strptime(request.form["timestamp"], "%Y-%m-%dT%H:%M")
            timestamp = timestamp.timestamp()
        except ValueError:
            timestamp = None

        intervention.timestamp = timestamp
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
@login_required
def delete_intervention(intervention_id):
    session = DBSession()
    intervention = session.query(Intervention).get(intervention_id)

    if not intervention:
        return gettext("Intervention not found"), 404

    if request.method == "POST":
        session.delete(intervention)
        session.commit()

        return redirect(url_for("view_interventions"))

    return render_template("delete_intervention.html", intervention=intervention)


@app.route("/interventions/export", methods=["GET"])
def interventions_export():
    session = DBSession()
    return excel.make_response_from_tables(session, [Intervention, User, Machine], "xlsx", file_name="interventions")
