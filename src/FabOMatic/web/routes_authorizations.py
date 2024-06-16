""" This module contains the routes for the authorizations. """

# pylint: disable=C0116

from flask import flash, render_template, request, redirect, url_for
from flask_login import login_required
from flask_babel import gettext
from FabOMatic.database.models import Authorization, Machine, User
from .webapplication import DBSession, app, excel


@app.route("/authorizations", methods=["GET"])
@login_required
def view_authorizations():
    user_filter = request.args.get("user")
    machine_filter = request.args.get("machine")

    with DBSession() as session:
        query = (
            session.query(Authorization).join(Authorization.user).filter_by(deleted=False).join(Authorization.machine)
        )

        if user_filter and user_filter.isdigit():
            query = query.filter(User.user_id == int(user_filter))
        if machine_filter and machine_filter.isdigit():
            query = query.filter(Machine.machine_id == int(machine_filter))

        authorizations = query.all()
        users = session.query(User).filter_by(deleted=False).all()
        machines = session.query(Machine).all()
        return render_template(
            "view_authorizations.html", authorizations=authorizations, users=users, machines=machines
        )


@app.route("/authorizations/add", methods=["GET"])
@login_required
def add_authorization():
    with DBSession() as session:
        users = session.query(User).filter_by(deleted=False).all()
        machines = session.query(Machine).all()
        return render_template("add_authorization.html", users=users, machines=machines)


@app.route("/authorizations/create", methods=["POST"])
@login_required
def create_authorization():
    with DBSession() as session:
        authorization_data = request.form
        new_authorization = Authorization(
            user_id=authorization_data["user_id"],
            machine_id=authorization_data["machine_id"],
        )
        session.add(new_authorization)
        try:
            session.commit()
        except Exception as e:
            flash(str(e), "danger")
        return redirect(url_for("view_authorizations"))


@app.route("/authorizations/edit/<int:authorization_id>", methods=["GET"])
@login_required
def edit_authorization(authorization_id):
    with DBSession() as session:
        authorization = session.query(Authorization).filter_by(authorization_id=authorization_id).one()
        users = session.query(User).filter_by(deleted=False).all()
        machines = session.query(Machine).all()
        if authorization:
            return render_template(
                "edit_authorization.html", authorization=authorization, users=users, machines=machines
            )
        else:
            return gettext("Authorization not found"), 404


@app.route("/authorizations/update", methods=["POST"])
@login_required
def update_authorization():
    with DBSession() as session:
        authorization_data = request.form
        authorization = (
            session.query(Authorization).filter_by(authorization_id=authorization_data["authorization_id"]).one()
        )
        if authorization:
            authorization.user_id = authorization_data["user_id"]
            authorization.machine_id = authorization_data["machine_id"]
            try:
                session.commit()
            except Exception as e:
                flash(str(e), "danger")
            return redirect(url_for("view_authorizations"))
        else:
            return gettext("Authorization not found"), 404


@app.route("/authorizations/delete/<int:authorization_id>", methods=["GET", "POST"])
@login_required
def delete_authorization(authorization_id):
    with DBSession() as session:
        authorization = session.query(Authorization).filter_by(authorization_id=authorization_id).one()
        if not authorization:
            return "Authorization not found", 404

        if request.method == "POST":
            session.delete(authorization)
            session.commit()
            return redirect(url_for("view_authorizations"))

        return render_template("delete_authorization.html", authorization=authorization)


@app.route("/authorizations/bulkadd", methods=["GET", "POST"])
@login_required
def bulkadd_authorizations():
    with DBSession() as session:
        machines = session.query(Machine).all()
        users = session.query(User).filter_by(deleted=False).order_by(User.user_id).all()

        if request.method == "POST":
            authorization_data = request.form
            machine = session.query(Machine).filter_by(machine_id=authorization_data["machine_id"]).one()
            for user_id in authorization_data.getlist("user_ids"):
                existing = (
                    session.query(Authorization).filter_by(user_id=user_id, machine_id=machine.machine_id).first()
                )
                if existing:
                    continue
                authorization = Authorization(user_id=user_id, machine_id=machine.machine_id)
                session.add(authorization)
            session.commit()
            flash(gettext("Authorizations added successfully"), "success")
            return redirect(url_for("view_authorizations"))

        return render_template("bulkadd_authorizations.html", machines=machines, users=users)


@app.route("/authorizations/export", methods=["GET"])
@login_required
def authorizations_export():
    session = DBSession()
    return excel.make_response_from_tables(session, [Authorization, User, Machine], "xlsx", file_name="authorizations")
