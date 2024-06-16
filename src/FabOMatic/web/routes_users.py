""" This module contains the routes for the users management. """

# pylint: disable=C0116

import re

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from flask_babel import gettext
from FabOMatic.database.models import User, Role, UnknownCard
from FabOMatic.web.authentication import send_reset_email
from .webapplication import DBSession, app, excel


@app.route("/users", methods=["GET"])
@login_required
def view_users():
    session = DBSession()
    users = session.query(User).filter_by(deleted=False).order_by(User.user_id).all()
    cards = session.query(UnknownCard).order_by(UnknownCard.timestamp.desc()).limit(20)
    return render_template("view_users.html", users=users, cards=cards)


@app.route("/users/add", methods=["GET"])
@login_required
def add_user():
    session = DBSession()
    roles = session.query(Role).order_by(Role.role_id).all()
    uuid = request.args.get("card_uuid", None)
    return render_template("add_user.html", roles=roles, card_UUID=uuid)


@app.route("/users/reset/<int:user_id>", methods=["GET", "POST"])
@login_required
def reset_user(user_id):
    session = DBSession()
    user = session.query(User).filter_by(user_id=user_id).one()
    if not user:
        return gettext("User not found"), 404

    if request.method == "POST":
        send_reset_email(user)
        flash(gettext("An email has been sent with instructions to reset password."), "info")
        return redirect(url_for("view_users"))

    return render_template("reset_user.html", user=user)


@app.route("/users/create", methods=["POST"])
@login_required
def create_user():
    session = DBSession()
    user_data = request.form
    card_UUID = user_data.get("card_UUID", None)

    if card_UUID == "" or card_UUID == "None":  # If the card_UUID is empty, set it to None
        card_UUID = None

    if card_UUID and not re.match(r"^[0-9A-Fa-f]{8}$", card_UUID):
        flash(gettext("Invalid card UUID. Please enter either 8 hexadecimal characters or leave it empty."), "error")
        return redirect(url_for("view_users"))

    check_user = session.query(User).filter(User.card_UUID.isnot(None)).filter_by(card_UUID=card_UUID).one_or_none()
    if check_user:
        flash(
            f"This card ID ({card_UUID}) is already assigned to another user ({check_user.name} {check_user.surname})",
            "error",
        )
        return redirect(url_for("view_users"))
    new_user = User(
        name=user_data["name"],
        surname=user_data["surname"],
        role_id=user_data["role_id"],
        disabled=user_data.get("disabled", "off") == "on",
        card_UUID=card_UUID,
        email=user_data["email"],
    )
    session.add(new_user)

    # Delete the card from the unknown cards table if it exists
    for card in session.query(UnknownCard).filter_by(card_UUID=card_UUID).all():
        session.delete(card)

    session.commit()

    if new_user.role.backend_admin and len(new_user.email) == 0:
        flash(
            gettext(
                "You have created a backend admin user without an email address. User will not be able to log on."
            ),
            "warning",
        )
    return redirect(url_for("view_users"))


@app.route("/users/edit/<int:user_id>", methods=["GET"])
@login_required
def edit_user(user_id):
    session = DBSession()
    user = session.query(User).filter_by(user_id=user_id).one()
    roles = session.query(Role).order_by(Role.role_id).all()
    if user:
        return render_template("edit_user.html", user=user, roles=roles)
    else:
        return gettext("User not found"), 404


@app.route("/users/update", methods=["POST"])
@login_required
def update_user():
    session = DBSession()
    user_data = request.form
    user = session.query(User).filter_by(user_id=user_data["user_id"]).one()
    if user:
        # Validate the card_UUID
        card_UUID = user_data.get("card_UUID", None)

        if card_UUID and not re.match(r"^[0-9A-Fa-f]{8}$", card_UUID):
            flash(
                gettext("Invalid card UUID. Please enter either 8 hexadecimal characters or leave it empty."), "error"
            )
            return redirect(url_for("edit_user", user_id=user.user_id))
        if card_UUID == "" or card_UUID == "None":
            card_UUID = None

        check_user = (
            session.query(User).filter(User.card_UUID.isnot(None)).filter_by(card_UUID=card_UUID).one_or_none()
        )
        if check_user and check_user.user_id != user.user_id:
            flash(
                gettext("This card ID is already assigned to another user")
                + f" ({check_user.name} {check_user.surname})",
                "error",
            )
            return redirect(url_for("edit_user", user_id=user.user_id))
        user.name = user_data["name"]
        user.surname = user_data["surname"]
        user.role_id = user_data["role_id"]
        user.card_UUID = card_UUID
        user.disabled = user_data.get("disabled", "off") == "on"
        user.email = user_data["email"]
        session.commit()
        return redirect(url_for("view_users"))
    else:
        return gettext("User not found"), 404


@app.route("/users/delete/<int:user_id>", methods=["GET", "POST"])
@login_required
def delete_user(user_id):
    session = DBSession()
    user = session.query(User).filter_by(user_id=user_id).one()
    if not user:
        return gettext("User not found"), 404

    if request.method == "POST":
        user.deleted = True
        user.card_UUID = None
        session.commit()
        return redirect(url_for("view_users"))

    return render_template("delete_user.html", user=user)


@app.route("/users/export", methods=["GET"])
@login_required
def users_export():
    session = DBSession()
    return excel.make_response_from_tables(session, [User, Role], "xlsx", file_name="users")
