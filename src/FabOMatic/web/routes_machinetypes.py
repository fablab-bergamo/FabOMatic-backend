""" Routes for Machine Types management """

# pylint: disable=C0116

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from flask_babel import gettext
from FabOMatic.database.models import MachineType
from .webapplication import DBSession, app


@app.route("/machinetypes")
@login_required
def machinetypes():
    session = DBSession()
    machine_types = session.query(MachineType).all()
    return render_template("view_machinetypes.html", machine_types=machine_types)


@app.route("/machinetypes/add", methods=["GET", "POST"])
@login_required
def add_machinetype():
    if request.method == "POST":
        session = DBSession()
        type_name = request.form["type_name"]
        timeout_min = request.form["type_timeout_min"]
        grace_period_min = request.form["grace_period_min"]
        access_management = request.form["access_control"]

        if not timeout_min.isnumeric() or not grace_period_min.isnumeric() or not access_management.isnumeric():
            flash(gettext("Invalid values for timeout or grace period or access control."))
            return redirect(url_for("add_machinetype"))
        else:
            timeout_min = int(timeout_min)
            grace_period_min = int(grace_period_min)
            access_management = int(access_management)

        if timeout_min < 0 or timeout_min > 65535:
            flash(gettext("Invalid values for timeout"))
            return redirect(url_for("add_machinetype"))

        if grace_period_min < 0 or grace_period_min > 65535:
            flash(gettext("Invalid values for grace period."))
            return redirect(url_for("add_machinetype"))

        machine_type = MachineType(
            type_name=type_name,
            type_timeout_min=timeout_min,
            grace_period_min=grace_period_min,
            access_management=access_management,
        )
        session.add(machine_type)
        session.commit()
        return redirect(url_for("machinetypes"))
    else:
        return render_template("add_machinetype.html", MachineType=MachineType)


@app.route("/machinetypes/edit/<int:type_id>", methods=["GET", "POST"])
@login_required
def edit_machinetype(type_id):
    session = DBSession()
    machine_type = session.query(MachineType).filter_by(type_id=type_id).one()
    if request.method == "POST":
        grace_period_min = request.form["grace_period_min"]
        timeout_min = request.form["type_timeout_min"]
        access_management = request.form["access_control"]

        if not timeout_min.isnumeric() or not grace_period_min.isnumeric() or not access_management.isnumeric():
            flash(gettext("Invalid values for timeout or grace period or access control."))
            return redirect(url_for("edit_machinetype", type_id=type_id))
        else:
            timeout_min = int(timeout_min)
            grace_period_min = int(grace_period_min)
            access_management = int(access_management)

        machine_type.type_timeout_min = timeout_min
        machine_type.grace_period_min = grace_period_min
        machine_type.access_management = access_management
        machine_type.type_name = request.form["type_name"]

        if machine_type.type_timeout_min < 0 or machine_type.type_timeout_min > 65535:
            flash(gettext("Invalid values for timeout"))
            return redirect(url_for("edit_machinetype", type_id=type_id))

        if machine_type.type_timeout_min < 0 or machine_type.grace_period_min > 65535:
            flash(gettext("Invalid values for grace period."))
            return redirect(url_for("edit_machinetype", type_id=type_id))

        session.add(machine_type)
        session.commit()
        return redirect(url_for("machinetypes"))
    else:
        return render_template("edit_machinetype.html", type_id=machine_type.type_id, machine_type=machine_type)


@app.route("/machinetypes/delete/<int:type_id>", methods=["GET", "POST"])
@login_required
def delete_machinetype(type_id):
    session = DBSession()
    machine_type = session.query(MachineType).filter_by(type_id=type_id).one()
    if not machine_type:
        return gettext("Machine Type not found"), 404
    if request.method == "POST":
        session.delete(machine_type)
        session.commit()
        flash(gettext("Machine type deleted successfully."))
        return redirect(url_for("machinetypes"))
    return render_template("delete_machinetype.html", machine_type=machine_type)
