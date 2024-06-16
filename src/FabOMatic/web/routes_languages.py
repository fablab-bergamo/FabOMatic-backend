from flask import session, redirect, url_for
from .webapplication import app


@app.route("/language/<lang>")
def set_language(lang=None):
    session["language"] = lang
    return redirect(url_for("about"))
