""" This module contains the routes for the maintenance management. """

# pylint: disable=C0116

import logging
import os

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from flask_babel import gettext
from werkzeug.utils import secure_filename

from FabOMatic.database.models import Machine, Maintenance
from .webapplication import DBSession, allowed_file, app, UPLOAD_FOLDER


@app.route("/maintenances")
@login_required
def maintenances():
    machine_filter = request.args.get("machine")
    description_filter = request.args.get("description")

    session = DBSession()
    query = session.query(Maintenance).join(Maintenance.machine)

    if machine_filter and machine_filter.isdigit():
        query = query.filter(Machine.machine_id == int(machine_filter))
    if description_filter:
        query = query.filter(Maintenance.description.contains(description_filter))

    maintenances = query.all()
    machines = session.query(Machine).all()

    return render_template("view_maintenances.html", maintenances=maintenances, machines=machines)


@app.route("/maintenances/add", methods=["GET", "POST"])
@login_required
def add_maintenance():
    session = DBSession()
    logging.debug("Processing add_maintenance %s", request)
    if request.method == "POST":
        hours_between = request.form["hours_between"]
        try:
            if float(hours_between) <= 0:
                flash(gettext("Hours between must be a positive number."))
                return redirect(url_for("add_maintenance"))
            hours_between = float(hours_between)
        except ValueError:
            flash(gettext("Hours between must be a number."))
            return redirect(url_for("add_maintenance"))

        description = request.form["description"]
        machine_id = request.form["machine_id"]
        lcd_message = request.form["lcd_message"]
        url = request.form["instructions_url"]

        maintenance = Maintenance(
            hours_between=hours_between,
            description=description,
            machine_id=machine_id,
            lcd_message=lcd_message,
            instructions_url=url,
        )
        session.add(maintenance)
        session.commit()
        return redirect(url_for("maintenances"))

    machines = session.query(Machine).all()
    return render_template("add_maintenance.html", machines=machines)


@app.route("/maintenances/edit/<int:maintenance_id>", methods=["GET", "POST"])
@login_required
def edit_maintenance(maintenance_id):
    session = DBSession()
    maintenance = session.query(Maintenance).filter_by(maintenance_id=maintenance_id).one()
    if request.method == "POST":
        hours_between = request.form["hours_between"]
        maintenance.description = request.form["description"]
        maintenance.machine_id = request.form["machine_id"]
        maintenance.lcd_message = request.form["lcd_message"]
        maintenance.instructions_url = request.form["instructions_url"]
        try:
            if float(hours_between) <= 0:
                flash(gettext("Hours between must be a positive number."))
                return redirect(url_for("edit_maintenance", maintenance_id=maintenance_id))
            hours_between = float(hours_between)
        except ValueError:
            flash(gettext("Hours between must be a number."))
            return redirect(url_for("edit_maintenance", maintenance_id=maintenance_id))

        maintenance.hours_between = hours_between

        session.add(maintenance)
        session.commit()
        return redirect(url_for("maintenances"))
    else:
        machines = session.query(Machine).all()
        return render_template(
            "edit_maintenance.html",
            machines=machines,
            maintenance_id=maintenance.maintenance_id,
            maintenance=maintenance,
        )


@app.route("/maintenances/delete/<int:maintenance_id>", methods=["GET", "POST"])
def delete_maintenance(maintenance_id):
    session = DBSession()
    maintenance = session.query(Maintenance).filter_by(maintenance_id=maintenance_id).one()
    if not maintenance:
        return gettext("Maintenance not found"), 404

    if request.method == "POST":
        session.delete(maintenance)
        session.commit()
        flash(gettext("Maintenance deleted successfully."))
        return redirect(url_for("maintenances"))

    return render_template("delete_maintenance.html", maintenance=maintenance)
