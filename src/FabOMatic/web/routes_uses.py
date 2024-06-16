""" This module contains the routes for the uses pages. """

# pylint: disable=C0116

from datetime import datetime

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from flask_babel import gettext
from FabOMatic.database.models import Machine, Use, User
from FabOMatic.database.repositories import MachineRepository, UserRepository
from .webapplication import DBSession, app, excel


@app.route("/machines/history/<int:machine_id>", methods=["GET"])
@login_required
def view_machine_use_history(machine_id):
    session = DBSession()
    uses = session.query(Use).filter_by(machine_id=machine_id).order_by(Use.start_timestamp.desc()).limit(500).all()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    if machine is None:
        return gettext("Machine not found"), 404

    return render_template("view_machine_use_history.html", uses=uses, machine=machine)


@app.route("/delete_use/<int:use_id>", methods=["POST", "GET"])
@login_required
def delete_use(use_id):
    session = DBSession()
    use = session.query(Use).filter_by(use_id=use_id).one()
    # ASk for confirmation before deleting
    if request.method == "GET":
        return render_template("delete_use.html", use=use)

    if use:
        # Correct machine cumulated hours if requested.
        correct = request.form.get("correctTotal", type=str, default="")
        if correct == "on":
            duration = use.end_timestamp - use.start_timestamp
            machine = session.query(Machine).filter_by(machine_id=use.machine_id).one()
            if machine and duration > 0:
                machine.machine_hours -= duration / 3600.0

        session.delete(use)
        session.commit()
        flash(gettext("Use deleted successfully."))
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

    if user_id and user_id.isdigit():
        user_id = int(user_id)
        uses = uses.filter(Use.user_id == user_id)

    if machine_id and machine_id.isdigit():
        machine_id = int(machine_id)
        uses = uses.filter(Use.machine_id == machine_id)

    if start_time:
        uses = uses.filter(Use.start_timestamp >= start_time)

    uses = uses.order_by(Use.start_timestamp.desc()).limit(500).all()

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
            flash(gettext("Invalid start timestamp."), "error")
            return redirect(url_for("add_use"))

        try:
            end_timestamp = datetime.strptime(use_data["end_timestamp"], "%Y-%m-%dT%H:%M")
            end_timestamp = end_timestamp.timestamp()
        except ValueError:
            end_timestamp = None

        if end_timestamp and end_timestamp < start_timestamp:
            flash(gettext("End timestamp cannot be before start timestamp."), "error")
            return redirect(url_for("add_use"))

        machine_repo = MachineRepository(session)
        machine = machine_repo.get_by_id(machine_id)
        if machine is None:
            flash(gettext("Machine not found."), "error")
            return redirect(url_for("add_use"))

        user_repo = UserRepository(session)
        user = user_repo.get_by_id(user_id)
        if user is None:
            flash(gettext("User not found."), "error")
            return redirect(url_for("add_use"))

        new_use = Use(
            user_id=user_id,
            machine_id=machine_id,
            start_timestamp=start_timestamp,
            last_seen=start_timestamp,
            end_timestamp=end_timestamp,
        )

        # Update machine usage
        machine.machine_hours += (end_timestamp - start_timestamp) / 3600.0

        session.add(new_use)
        session.commit()
        flash(gettext("Registration added successfully."))
        return redirect(url_for("view_uses"))


@app.route("/uses/export", methods=["GET"])
@login_required
def uses_export():
    session = DBSession()
    return excel.make_response_from_tables(session, [Use, Machine, User], "xlsx", file_name="uses")


@app.route("/machines/history/<int:machine_id>/export", methods=["GET"])
@login_required
def machine_use_export(machine_id):
    session = DBSession()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    if machine is None:
        return gettext("Machine not found"), 404
    uses = session.query(Use).filter_by(machine_id=machine_id).order_by(Use.start_timestamp.desc()).all()
    columns = ["use_id", "user_id", "machine_id", "start_timestamp", "end_timestamp"]
    return excel.make_response_from_query_sets(uses, columns, "xlsx", file_name="machine_use")
