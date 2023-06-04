from flask import Flask, render_template, request, redirect, url_for
from rfid_backend_FABLAB_BG.database.models import Intervention, Machine, Maintenance, User
from .webapplication import DBSession, app
import time


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
