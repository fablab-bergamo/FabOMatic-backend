import logging
from flask_login import LoginManager, login_user, logout_user, login_required
from flask import render_template, request, redirect, url_for, flash
from .webapplication import DBSession, app
from FabOMatic.database.models import User
from FabOMatic.conf import FabConfig
from flask_mail import Mail, Message
from flask_babel import gettext

login_manager = LoginManager()
login_manager.init_app(app)


app.config["MAIL_SERVER"] = FabConfig.getSetting("email", "server")
app.config["MAIL_PORT"] = FabConfig.getSetting("email", "port")
app.config["MAIL_USE_TLS"] = FabConfig.getSetting("email", "use_tls")
app.config["MAIL_USERNAME"] = FabConfig.getSetting("email", "username")
app.config["MAIL_PASSWORD"] = FabConfig.getSetting("email", "password")
app.config["MAIL_DEFAULT_SENDER"] = FabConfig.getSetting("email", "sender")

mail = Mail(app)

SALT = b"fablab-bg"


@login_manager.user_loader
def load_user(user_id):
    with DBSession() as session:
        return session.query(User).get(int(user_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with DBSession() as session:
            user = session.query(User).filter_by(email=request.form["email"]).first()
            if user and user.check_password(request.form["password"]):
                # Now check the user role
                if user.role.backend_admin or user.role.authorize_all:
                    login_user(user)
                    logging.info("User %s logged in", user.email)
                    return redirect(url_for("about"))
                else:
                    logging.warning("User %s does not have a role with backend administration permission.", user.email)
                    flash(gettext("Your user does not have a role with backend administration permission."), "danger")
                    return redirect(url_for("login"))
            else:
                logging.warning("Failed login attempt for user %s", request.form["email"])
                flash(gettext("Wrong username or password."), "danger")
                return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash(gettext("You have been logged out."), "success")
    return redirect(url_for("login"))


def send_reset_email(user: User) -> bool:
    try:
        token = user.get_reset_token(app.config["SECRET_KEY"], SALT)
        msg = Message("Password Reset Request", recipients=[user.email])
        msg.body = f"""To reset your password, visit the following link:
                {url_for('reset_token', token=token, _external=True)}

                If you did not make this request then simply ignore this email and no changes will be made.
                """
        mail.send(msg)
        logging.info("Password reset email sent to %s", user.email)
        return True
    except Exception as e:
        logging.error("Failed to send password reset email to %s: %s", user.email, str(e))
        return False


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        with DBSession() as session:
            user = session.query(User).filter_by(email=request.form["email"]).first()
            if user:
                if send_reset_email(user):
                    flash(gettext("Email sent with instructions to reset your password."), "info")
                else:
                    flash(gettext("Failed to send email. Please contact an administrator."), "danger")
                return redirect(url_for("login"))
            else:
                flash(gettext("No user found with this email."), "danger")
                return redirect(url_for("login"))
    return render_template("forgot_password.html")


@app.route("/reset_token/<token>", methods=["GET", "POST"])
def reset_token(token):
    user_id = User.verify_reset_token(token, app.config["SECRET_KEY"], SALT)
    if not user_id:
        flash(gettext("That is an invalid or expired token"), "warning")
        return redirect(url_for("forgot_password"))
    if request.method == "POST":
        with DBSession() as session:
            user = session.query(User).get(user_id)
            user.set_password(request.form["password"])
            session.commit()
            flash(gettext("Your password has been updated! You are now able to log in"), "success")
            return redirect(url_for("login"))
    return render_template("reset_token.html", title="Reset Password")
