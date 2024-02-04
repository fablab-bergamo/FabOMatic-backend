""" This module contains the routes for the uses pages. """

# pylint: disable=C0116

from datetime import datetime

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from rfid_backend_FABLAB_BG.database.models import Machine, Use, User
from rfid_backend_FABLAB_BG.database.repositories import MachineRepository, UserRepository
from .webapplication import DBSession, app


@app.route("/machines/history/<int:machine_id>", methods=["GET"])
@login_required
def view_machine_use_history(machine_id):
    session = DBSession()
    uses = session.query(Use).filter_by(machine_id=machine_id).order_by(Use.start_timestamp.desc()).all()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    if machine is None:
        return "Machine not found", 404

    return render_template("view_machine_use_history.html", uses=uses, machine=machine)


@app.route("/delete_use/<int:use_id>", methods=["POST"])
@login_required
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
@login_required
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
    all_users = session.query(User).filter_by(deleted=False).all()
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


@app.route("/add_use", methods=["GET"])
@login_required
def add_use():
    with DBSession() as session:
        users = session.query(User).filter_by(deleted=False).order_by(User.name).all()
        machines = session.query(Machine).order_by(Machine.machine_name).all()
        return render_template("add_use.html", users=users, machines=machines)


@app.route("/add_use", methods=["POST"])
@login_required
def add_use_post():
    with DBSession() as session:
        use_data = request.form
        user_id = use_data["user_id"]
        machine_id = use_data["machine_id"]
        try:
            start_timestamp = datetime.strptime(use_data["start_timestamp"], "%Y-%m-%dT%H:%M")
            start_timestamp = start_timestamp.timestamp()
        except ValueError:
            flash("Invalid start timestamp.", "error")
            return redirect(url_for("add_use"))

        try:
            end_timestamp = datetime.strptime(use_data["end_timestamp"], "%Y-%m-%dT%H:%M")
            end_timestamp = end_timestamp.timestamp()
        except ValueError:
            end_timestamp = None

        if end_timestamp and end_timestamp < start_timestamp:
            flash("End timestamp cannot be before start timestamp.", "error")
            return redirect(url_for("add_use"))

        machine_repo = MachineRepository(session)
        machine = machine_repo.get_by_id(machine_id)
        if machine is None:
            flash("Machine not found.", "error")
            return redirect(url_for("add_use"))

        user_repo = UserRepository(session)
        user = user_repo.get_by_id(user_id)
        if user is None:
            flash("User not found.", "error")
            return redirect(url_for("add_use"))

        new_use = Use(
            user_id=user_id,
            machine_id=machine_id,
            start_timestamp=start_timestamp,
            last_seen=start_timestamp,
            end_timestamp=end_timestamp,
        )
        session.add(new_use)
        session.commit()
        flash("Registration added successfully.")
        return redirect(url_for("view_uses"))
