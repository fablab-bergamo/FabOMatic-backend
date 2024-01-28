""" This module contains the routes for the interventions. """
# pylint: disable=C0116

from datetime import datetime
from time import time

from flask import render_template, request, redirect, url_for
from flask_login import login_required
from rfid_backend_FABLAB_BG.database.models import Intervention, Machine, Maintenance, User
from .webapplication import DBSession, app


@app.route("/interventions")
@login_required
def view_interventions():
    session = DBSession()
    interventions = session.query(Intervention).all()
    return render_template("view_interventions.html", interventions=interventions)


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
        return "Intervention not found", 404

    if request.method == "POST":
        session.delete(intervention)
        session.commit()

        return redirect(url_for("view_interventions"))

    return render_template("delete_intervention.html", intervention=intervention)
