from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from rfid_backend_FABLAB_BG.database.models import User, Role
import re
from .webapplication import DBSession, app


@app.route("/users", methods=["GET"])
def view_users():
    session = DBSession()
    users = session.query(User).order_by(User.user_id).all()
    return render_template("view_users.html", users=users)


@app.route("/users/add", methods=["GET"])
def add_user():
    session = DBSession()
    roles = session.query(Role).order_by(Role.role_id).all()
    return render_template("add_user.html", roles=roles)


@app.route("/users/create", methods=["POST"])
def create_user():
    session = DBSession()
    user_data = request.form
    card_UUID = user_data.get("card_UUID", None)
    if card_UUID and not re.match(r"^[0-9A-Fa-f]{8}$", card_UUID):
        flash("Invalid card UUID. Please enter either 8 hexadecimal characters or leave it empty.", "error")
        return redirect(url_for("view_users"))

    new_user = User(
        name=user_data["name"],
        surname=user_data["surname"],
        role_id=user_data["role_id"],
        disabled=user_data.get("disabled", "off") == "on",
        card_UUID=card_UUID,
    )
    session.add(new_user)
    session.commit()
    return redirect(url_for("view_users"))


@app.route("/users/edit/<int:user_id>", methods=["GET"])
def edit_user(user_id):
    session = DBSession()
    user = session.query(User).filter_by(user_id=user_id).one()
    roles = session.query(Role).order_by(Role.role_id).all()
    if user:
        return render_template("edit_user.html", user=user, roles=roles)
    else:
        return "User not found", 404


@app.route("/users/update", methods=["POST"])
def update_user():
    session = DBSession()
    user_data = request.form
    user = session.query(User).filter_by(user_id=user_data["user_id"]).one()
    if user:
        # Validate the card_UUID
        card_UUID = user_data.get("card_UUID", None)
        if card_UUID and not re.match(r"^[0-9A-Fa-f]{8}$", card_UUID):
            flash("Invalid card UUID. Please enter either 8 hexadecimal characters or leave it empty.", "error")
            return redirect(url_for("edit_user", user_id=user.user_id))
        user.name = user_data["name"]
        user.surname = user_data["surname"]
        user.role_id = user_data["role_id"]
        user.card_UUID = user_data.get("card_UUID", None)
        user.disabled = user_data.get("disabled", "off") == "on"
        session.commit()
        return redirect(url_for("view_users"))
    else:
        return "User not found", 404


@app.route("/users/delete/<int:user_id>", methods=["GET", "POST"])
def delete_user(user_id):
    session = DBSession()
    user = session.query(User).filter_by(user_id=user_id).one()
    if not user:
        return "User not found", 404

    if request.method == "POST":
        session.delete(user)
        session.commit()
        return redirect(url_for("view_users"))

    return render_template("delete_user.html", user=user)
