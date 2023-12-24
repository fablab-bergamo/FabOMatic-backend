from flask import Flask, render_template, request, redirect, url_for, flash
from rfid_backend_FABLAB_BG.database.models import MachineType
from .webapplication import DBSession, app


@app.route("/machinetypes")
def machinetypes():
    session = DBSession()
    machine_types = session.query(MachineType).all()
    return render_template("view_machinetypes.html", machine_types=machine_types)


@app.route("/machinetypes/add", methods=["GET", "POST"])
def add_machinetype():
    if request.method == "POST":
        session = DBSession()
        type_name = request.form["type_name"]
        timeout_min = request.form["type_timeout_min"]
        machine_type = MachineType(type_name=type_name, type_timeout_min=timeout_min)
        session.add(machine_type)
        session.commit()
        return redirect(url_for("machinetypes"))
    else:
        return render_template("add_machinetype.html")


@app.route("/machinetypes/edit/<int:type_id>", methods=["GET", "POST"])
def edit_machinetype(type_id):
    session = DBSession()
    machine_type = session.query(MachineType).filter_by(type_id=type_id).one()
    if request.method == "POST":
        machine_type.type_name = request.form["type_name"]
        machine_type.type_timeout_min = request.form["type_timeout_min"]
        session.add(machine_type)
        session.commit()
        return redirect(url_for("machinetypes"))
    else:
        return render_template("edit_machinetype.html", type_id=machine_type.type_id, machine_type=machine_type)


@app.route("/machinetypes/delete/<int:type_id>", methods=["GET", "POST"])
def delete_machinetype(type_id):
    session = DBSession()
    machine_type = session.query(MachineType).filter_by(type_id=type_id).one()
    if not machine_type:
        return "Machine Type not found", 404
    if request.method == "POST":
        session.delete(machine_type)
        session.commit()
        flash("Machine type deleted successfully.")
        return redirect(url_for("machinetypes"))
    return render_template("delete_machinetype.html", machine_type=machine_type)
