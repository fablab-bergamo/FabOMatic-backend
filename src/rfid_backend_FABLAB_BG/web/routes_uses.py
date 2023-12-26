""" This module contains the routes for the uses pages. """
# pylint: disable=C0116

from datetime import datetime

from flask import render_template, request, redirect, url_for, flash
from rfid_backend_FABLAB_BG.database.models import Machine, Use, User
from .webapplication import DBSession, app


@app.route("/machines/history/<int:machine_id>", methods=["GET"])
def view_machine_use_history(machine_id):
    session = DBSession()
    uses = session.query(Use).filter_by(machine_id=machine_id).order_by(Use.start_timestamp.desc()).all()
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

    uses = uses.order_by(Use.start_timestamp.desc()).all()

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
