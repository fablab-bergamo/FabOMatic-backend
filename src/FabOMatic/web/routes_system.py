""" Routes for managing roles. """

# pylint: disable=C0116

from flask import flash, redirect, render_template, Response, request, send_file, url_for
from flask_login import login_required
from flask_babel import gettext
from importlib.metadata import version

from FabOMatic.database.DatabaseBackend import getDatabaseUrl
from FabOMatic.database.repositories import BoardsRepository
from .webapplication import DBSession, app
import os
import platform
import shutil
import psutil
import subprocess
import requests


@app.route("/system")
@login_required
def system():
    db_file = getDatabaseUrl().replace("sqlite:///", "")
    db_size = os.path.getsize(db_file)
    # Returns information about the host machine (Raspberry Pi)
    machine_info = f"{platform.uname() }, CPU:{os.cpu_count()}"
    total, used, disk_free = shutil.disk_usage(__file__)
    stats = psutil.virtual_memory()
    ram_free = getattr(stats, "available")

    # application details
    app_version = version("FabOMatic")

    # check if there is an updated pypi package
    package = "FabOMatic"  # replace with the package you want to check
    response = requests.get(f"https://pypi.org/pypi/{package}/json")
    latest_version = response.json()["info"]["version"]

    # Get the boards from the database repository
    session = DBSession()
    board_repo = BoardsRepository(session)
    boards = board_repo.get_all()

    return render_template(
        "view_system.html",
        db_size=int(db_size / 1024),
        machine_info=machine_info,
        disk_free=int(disk_free / 1024 / 1024),
        ram_free=int(ram_free / 1024 / 1024),
        app_version=app_version,
        latest_version=latest_version,
        db_file=db_file,
        boards=boards,
    )


@app.route("/download_db")
@login_required
def download_db():
    # Returns of copy of the SQLite database to the user
    db_file = getDatabaseUrl().replace("sqlite:///", "")
    return send_file(db_file, as_attachment=True)


@app.route("/download_logs")
@login_required
def download_logs():
    log_dir = os.path.expanduser("~/log")
    log_file = os.path.join(log_dir, "log.txt")
    return send_file(log_file, as_attachment=True)


@app.route("/upload_db", methods=["POST"])
@login_required
def upload_db():
    if "db_file" not in request.files:
        return redirect(request.url)

    new_db_file = request.files["db_file"]
    if not new_db_file.filename.lower().endswith(".sqldb"):
        flash(gettext("File must have sqldb extension"), "error")
        redirect(url_for("system"))

    # Backup existing file
    actual_db_file = getDatabaseUrl().replace("sqlite:///", "")
    backup_copy = actual_db_file + ".bak"
    shutil.copyfile(actual_db_file, backup_copy)

    # Save the uploaded file over the existing
    new_db_file.save(actual_db_file)
    # Redirect to the home page after uploading
    flash(gettext("Database was replaced. Previous copy can be found at ") + backup_copy)
    return redirect(url_for("system"))


@app.route("/update_app")
@login_required
def update_app():
    upgrade_output = subprocess.run(
        ["pip", "install", "-i", "https://pypi.org/simple/", "FabOMatic", "--upgrade"],
        check=True,
        text=True,
        capture_output=True,
    )

    # Restart the application using Systemd
    if platform.system() != "Windows":
        restart_output = subprocess.run(
            ["systemctl", "--user", "restart", "fablab"], check=True, text=True, capture_output=True
        )
        restart_output = f"Restart output:\n{restart_output.stdout}"
    else:
        restart_output = "Restart skipped because application is running on Windows or not running under systemd."

    output = f"Upgrade results : PIP output:\n{upgrade_output}\n\nSystemd output:\n{restart_output}"

    return Response(output, mimetype="text/plain")


@app.route("/reboot")
@login_required
def reboot():
    if platform.system() != "Windows":
        reboot_output = subprocess.run(["sudo", "reboot"], check=True, text=True, capture_output=True)
        reboot_output = f"Reboot output:\n{reboot_output.stdout}"
    else:
        reboot_output = "Reboot skipped because application is running on Windows"

    return Response(reboot_output, mimetype="text/plain")


@app.route("/restart_app")
@login_required
def restart_app():
    # Restart the application using Systemd
    if platform.system() != "Windows":
        restart_output = subprocess.run(
            ["systemctl", "--user", "restart", "fablab"], check=True, text=True, capture_output=True
        )
        restart_output = f"Restart output:\n{restart_output.stdout}"
    else:
        restart_output = "Restart skipped because application is running on Windows or not running under systemd."

    return Response(restart_output, mimetype="text/plain")
