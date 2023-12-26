""" This module contains the routes for the authorizations. """
# pylint: disable=C0116

from flask import render_template, request, redirect, url_for
from rfid_backend_FABLAB_BG.database.models import Authorization, Machine, User
from .webapplication import DBSession, app


@app.route("/authorizations", methods=["GET"])
def view_authorizations():
    session = DBSession()
    authorizations = session.query(Authorization).all()
    return render_template("view_authorizations.html", authorizations=authorizations)


@app.route("/authorizations/add", methods=["GET"])
def add_authorization():
    session = DBSession()
    users = session.query(User).all()
    machines = session.query(Machine).all()
    return render_template("add_authorization.html", users=users, machines=machines)


@app.route("/authorizations/create", methods=["POST"])
def create_authorization():
    session = DBSession()
    authorization_data = request.form
    new_authorization = Authorization(
        user_id=authorization_data["user_id"],
        machine_id=authorization_data["machine_id"],
    )
    session.add(new_authorization)
    session.commit()
    return redirect(url_for("view_authorizations"))


@app.route("/authorizations/edit/<int:authorization_id>", methods=["GET"])
def edit_authorization(authorization_id):
    session = DBSession()
    authorization = session.query(Authorization).filter_by(authorization_id=authorization_id).one()
    users = session.query(User).all()
    machines = session.query(Machine).all()
    if authorization:
        return render_template("edit_authorization.html", authorization=authorization, users=users, machines=machines)
    else:
        return "Authorization not found", 404


@app.route("/authorizations/update", methods=["POST"])
def update_authorization():
    session = DBSession()
    authorization_data = request.form
    authorization = (
        session.query(Authorization).filter_by(authorization_id=authorization_data["authorization_id"]).one()
    )
    if authorization:
        authorization.user_id = authorization_data["user_id"]
        authorization.machine_id = authorization_data["machine_id"]
        session.commit()
        return redirect(url_for("view_authorizations"))
    else:
        return "Authorization not found", 404


@app.route("/authorizations/delete/<int:authorization_id>", methods=["GET", "POST"])
def delete_authorization(authorization_id):
    session = DBSession()
    authorization = session.query(Authorization).filter_by(authorization_id=authorization_id).one()
    if not authorization:
        return "Authorization not found", 404

    if request.method == "POST":
        session.delete(authorization)
        session.commit()
        return redirect(url_for("view_authorizations"))

    return render_template("delete_authorization.html", authorization=authorization)
