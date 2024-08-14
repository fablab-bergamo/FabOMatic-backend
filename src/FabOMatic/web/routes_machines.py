""" Routes for machines management. """

# pylint: disable=C0116

from flask import flash, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from flask_babel import gettext
from FabOMatic.__main__ import Backend
from FabOMatic.database.models import Machine, MachineType, User
from FabOMatic.database.repositories import MachineRepository
from .webapplication import DBSession, app


@app.route("/machines", methods=["GET"])
@login_required
def view_machines():
    session = DBSession()
    machine_repo = MachineRepository(session)
    machines = session.query(Machine).order_by(Machine.machine_id).all()
    maint_stats = {}
    for machine in machines:
        for maint in machine.maintenances:
            elapsed_s = machine_repo.getRelativeUseTimeByMaintenance(machine.machine_id, maint)
            elapsed_h = round(elapsed_s / 3600.0, 1)
            expired = elapsed_h > maint.hours_between
            maint_stats[maint.maintenance_id] = {"expired": expired, "elapsed": elapsed_h}

    return render_template("view_machines.html", machines=machines, maint_stats=maint_stats)


@app.route("/machines/add", methods=["GET"])
@login_required
def add_machine():
    session = DBSession()
    machine_types = session.query(MachineType).order_by(MachineType.type_id).all()
    return render_template("add_machine.html", machine_types=machine_types)


@app.route("/machines/create", methods=["POST"])
@login_required
def create_machine():
    session = DBSession()
    machine_data = request.form

    # Input validation
    try:
        if float(machine_data["machine_hours"]) < 0:
            flash(gettext("Hours must be a positive number."))
            return redirect(url_for("add_machine"))
    except ValueError:
        flash(gettext("Hours must be a number."))
        return redirect(url_for("add_machine"))

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
@login_required
def edit_machine(machine_id):
    session = DBSession()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    machine_types = session.query(MachineType).order_by(MachineType.type_id).all()
    if machine:
        return render_template("edit_machine.html", machine=machine, machine_types=machine_types)
    else:
        return gettext("Machine not found"), 404


@app.route("/machines/start/<int:machine_id>", methods=["GET"])
@login_required
def start_machine(machine_id):
    session = DBSession()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    user: User = current_user
    if user.card_UUID is None:
        flash(gettext("Your user needs a valid CARD ID to use this function"))
        return redirect(url_for("view_machines"))

    if machine:
        if not machine.isOnline():
            flash(gettext("Machine is not online:") + machine.machine_name)
            return redirect(url_for("view_machines"))

        backend: Backend = app.backend
        mapper = backend.getMapper()

        if mapper.remoteStart(machine.machine_id, user.card_UUID):
            flash(gettext("Remote start success"))
        else:
            flash(gettext("Remote start failure"))

        return redirect(url_for("view_machines"))

    return gettext("Machine not found"), 404


@app.route("/machines/stop/<int:machine_id>", methods=["GET"])
@login_required
def stop_machine(machine_id):
    session = DBSession()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    user: User = current_user
    if user.card_UUID is None:
        flash(gettext("Your user needs a valid CARD ID to use this function"))
        return redirect(url_for("view_machines"))

    if machine:
        if not machine.isOnline():
            flash(gettext("Machine is not online:") + machine.machine_name)
            return redirect(url_for("view_machines"))

        backend: Backend = app.backend
        mapper = backend.getMapper()

        if mapper.remoteStop(machine.machine_id, user.card_UUID):
            flash(gettext("Remote stop success"))
        else:
            flash(gettext("Remote stop failure"))

        return redirect(url_for("view_machines"))

    return gettext("Machine not found"), 404


@app.route("/machines/update", methods=["POST"])
@login_required
def update_machine():
    session = DBSession()
    machine_data = request.form
    machine = session.query(Machine).filter_by(machine_id=machine_data["machine_id"]).one()
    if machine:
        machine.machine_name = machine_data["machine_name"]
        machine.machine_type_id = machine_data["machine_type_id"]

        # Input validation
        try:
            if float(machine_data["machine_hours"]) < 0:
                flash(gettext("Hours must be a positive number."))
                return redirect(url_for("edit_machine", machine_id=machine.machine_id))
        except ValueError:
            flash(gettext("Hours must be a number."))
            return redirect(url_for("edit_machine", machine_id=machine.machine_id))

        machine.machine_hours = float(machine_data["machine_hours"])
        machine.blocked = machine_data.get("blocked", "off") == "on"
        session.commit()
        return redirect(url_for("view_machines"))

    return gettext("Machine not found"), 404


@app.route("/machines/delete/<int:machine_id>", methods=["GET", "POST"])
@login_required
def delete_machine(machine_id):
    session = DBSession()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    if not machine:
        return gettext("Machine not found"), 404

    if request.method == "POST":
        session.delete(machine)
        session.commit()
        return redirect(url_for("view_machines"))

    return render_template("delete_machine.html", machine=machine)
