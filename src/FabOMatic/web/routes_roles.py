""" Routes for managing roles. """

# pylint: disable=C0116

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from flask_babel import gettext
from FabOMatic.database.models import Role
from FabOMatic.database.repositories import RoleRepository
from .webapplication import DBSession, app


@app.route("/roles")
@login_required
def roles():
    session = DBSession()
    roles_list = session.query(Role).all()
    return render_template("view_roles.html", roles=roles_list)


@app.route("/roles/add", methods=["GET", "POST"])
@login_required
def add_role():
    if request.method == "POST":
        session = DBSession()
        role_name = request.form["role_name"]
        authorize_all = request.form.get("authorize_all", "off") == "on"
        maintenance = request.form.get("maintenance", "off") == "on"
        backend_admin = request.form.get("backend_admin", "off") == "on"
        role = Role(
            role_name=role_name,
            authorize_all=authorize_all,
            maintenance=maintenance,
            reserved=False,
            backend_admin=backend_admin,
        )
        session.add(role)
        session.commit()
        return redirect(url_for("roles"))
    else:
        return render_template("add_role.html")


@app.route("/roles/edit/<int:role_id>", methods=["GET", "POST"])
@login_required
def edit_role(role_id):
    session = DBSession()
    role = session.query(Role).filter_by(role_id=role_id).one()

    # Block editing of reserved roles
    if not role:
        flash(gettext("Role not found."), "error")
        return redirect(url_for("roles"))

    if role.reserved:
        flash(gettext("Cannot edit reserved role."), "error")
        return redirect(url_for("roles"))

    if request.method == "POST":
        role.role_name = request.form["role_name"]
        role.authorize_all = request.form.get("authorize_all", "off") == "on"
        role.maintenance = request.form.get("maintenance", "off") == "on"
        role.backend_admin = request.form.get("backend_admin", "off") == "on"
        session.add(role)
        session.commit()
        return redirect(url_for("roles"))

    return render_template("edit_role.html", role_id=role.role_id, role=role)


@app.route("/roles/delete/<int:role_id>", methods=["GET", "POST"])
def delete_role(role_id):
    session = DBSession()
    role_repo = RoleRepository(session)
    role = role_repo.get_by_id(role_id)
    if not role:
        flash(gettext("Role not found."), "error")
        return redirect(url_for("roles"))

    if role.reserved:
        flash(gettext("Cannot edit reserved role."), "error")
        return redirect(url_for("roles"))

    if request.method == "POST":
        role_repo.delete(role)
        flash(gettext("Role deleted successfully."))
        return redirect(url_for("roles"))

    return render_template("delete_role.html", role=role)
