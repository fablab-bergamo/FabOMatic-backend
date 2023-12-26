""" This module contains the routes for the maintenance management. """
# pylint: disable=C0116

import logging
import os

from flask import render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

from rfid_backend_FABLAB_BG.database.models import Machine, Maintenance
from .webapplication import DBSession, allowed_file, app, UPLOAD_FOLDER


@app.route("/maintenances")
def maintenances():
    session = DBSession()
    maintenance_list = session.query(Maintenance).all()
    return render_template("view_maintenances.html", maintenances=maintenance_list)


@app.route("/maintenances/add", methods=["GET", "POST"])
def add_maintenance():
    session = DBSession()
    logging.debug("Processing add_maintenance %s", request)
    if request.method == "POST":
        hours_between = request.form["hours_between"]
        description = request.form["description"]
        machine_id = request.form["machine_id"]
        attachment = None

        if "attachment" in request.files:
            file = request.files["attachment"]
            if file.filename != "" and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                attachment = filename
            else:
                logging.warning(f"Invalid file uploaded {file.filename}")

        maintenance = Maintenance(
            hours_between=hours_between, description=description, machine_id=machine_id, attachment=attachment
        )
        session.add(maintenance)
        session.commit()
        return redirect(url_for("maintenances"))

    machines = session.query(Machine).all()
    return render_template("add_maintenance.html", machines=machines)


@app.route("/maintenances/edit/<int:maintenance_id>", methods=["GET", "POST"])
def edit_maintenance(maintenance_id):
    session = DBSession()
    maintenance = session.query(Maintenance).filter_by(maintenance_id=maintenance_id).one()
    if request.method == "POST":
        maintenance.hours_between = request.form["hours_between"]
        maintenance.description = request.form["description"]
        maintenance.machine_id = request.form["machine_id"]
        maintenance.attachment = None
        if "attachment" in request.files:
            file = request.files["attachment"]
            if file.filename != "" and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                maintenance.attachment = filename
            else:
                logging.warning(f"Invalid file uploaded {file.filename}")
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
        return "Maintenance not found", 404

    if request.method == "POST":
        session.delete(maintenance)
        session.commit()
        flash("Maintenance deleted successfully.")
        return redirect(url_for("maintenances"))

    return render_template("delete_maintenance.html", maintenance=maintenance)
