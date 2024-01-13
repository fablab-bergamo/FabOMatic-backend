from flask_login import LoginManager, login_user, logout_user, login_required
from flask import render_template, request, redirect, url_for, flash
from .webapplication import DBSession, app
from rfid_backend_FABLAB_BG.database.models import User
from rfid_backend_FABLAB_BG.database.DatabaseBackend import getSetting
from flask_mail import Mail, Message

login_manager = LoginManager()
login_manager.init_app(app)


app.config["MAIL_SERVER"] = getSetting("email", "server")
app.config["MAIL_PORT"] = getSetting("email", "port")
app.config["MAIL_USE_TLS"] = getSetting("email", "use_tls")
app.config["MAIL_USERNAME"] = getSetting("email", "username")
app.config["MAIL_PASSWORD"] = getSetting("email", "password")

mail = Mail(app)

SALT = b"fablab-bg"


@login_manager.user_loader
def load_user(user_id):
    session = DBSession()
    return session.query(User).get(int(user_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session = DBSession()
        user = session.query(User).filter_by(email=request.form["email"]).first()
        if user and user.check_password(request.form["password"]):
            # Now check the user role
            if user.role.backend_admin or user.role.authorize_all:
                login_user(user)
                return redirect(url_for("about"))
            else:
                flash("Your user does not have a role with backend administration permission.", "danger")
                return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        session = DBSession()
        user = session.query(User).filter_by(email=request.form["email"]).first()
        if user:
            token = user.get_reset_token(app.config["SECRET_KEY"], SALT)
            msg = Message("Password Reset Request", sender="noreply@demo.com", recipients=[user.email])
            msg.body = f"""To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
"""
            mail.send(msg)
            flash("Email sent with instructions to reset your password.", "info")
            return redirect(url_for("login"))
        else:
            flash("No user found with this email.", "danger")
            return redirect(url_for("login"))
    return render_template("forgot_password.html")


@app.route("/reset_token/<token>", methods=["GET", "POST"])
def reset_token(token):
    user_id = User.verify_reset_token(token, app.config["SECRET_KEY"], SALT)
    if not user_id:
        flash("That is an invalid or expired token", "warning")
        return redirect(url_for("forgot_password"))
    if request.method == "POST":
        session = DBSession()
        user = session.query(User).get(user_id)
        user.set_password(request.form["password"])
        session.commit()
        flash("Your password has been updated! You are now able to log in", "success")
        return redirect(url_for("login"))
    return render_template("reset_token.html", title="Reset Password")
