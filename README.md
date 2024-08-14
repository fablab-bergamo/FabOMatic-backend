# Fab-O-Matic back-end

[![Build, test and package](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/build.yml/badge.svg)](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/build.yml)

## What is this project?

* This is a web application to handle a FabLab machines access by Fab-O-Matic boards connected to the machines (see ESP32 project : [Fab-O-Matic](https://github.com/fablab-bergamo/Fab-O-matic) )

* Homescreen example, with real-time machine status:

![image](https://github.com/fablab-bergamo/rfid-backend/assets/6236243/75075b86-ec9b-4e6c-82d8-35de94663c09)

* [UI description](doc/UI.pdf)

* This Python 3.10 application runs a MQTT client and a Flask HTTPS application.

* Articles describing the project are available on FabLab Bergamo website : <https://www.fablabbergamo.it/2024/07/14/fabomatic7/>

## Features

* Web admin portal with user authentication over https

* Holds the member cards RFID database with their status (active, inactive). Easy registration of new members (swipe card on existing Fab-O-Matic and convert to new user).

* Machine maintenance plans based on actual hours with display on Fab-O-Matic LCD

* Permissions by user and machine (can be disabled)

* Machine history (usage and maintenance)

* Real-time dashboard of machines status

## Backend runtime requirements

* An external MQTT Broker. Mosquitto has been used for testing.

* SQLAlchemy supports several database engines, but this has been tested with SQLite only.

## Pre-requisites for Raspberry Pi Zero

* Install prerequisites (python 3.10+, rustc for cryptography, mosquitto, pip). It takes 3-4 hours on Raspberry Pi Zero to complete installation.

```shell
wget -qO - https://raw.githubusercontent.com/tvdsluijs/sh-python-installer/main/python.sh | sudo bash -s 3.10.9
sudo apt remove python3-apt
sudo apt install python3-apt
sudo curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
sudo apt install mosquitto
```

## Pre-requisites for Linux machines

* On other Linux systems, the following requisites shall be enough:

```shell
sudo apt install python3-apt
sudo apt install rustc
sudo apt install mosquitto
sudo apt install dbus-user-session
```

## Pre-requisites for firmware updates

* Espressif's ESPOTA tool is used to apply Over-the-air firmware updates to Fab-O-Matic boards.

```shell
wget https://raw.githubusercontent.com/espressif/arduino-esp32/master/tools/espota.py
```

## Installation instructions

* Install from test pypi repository

```shell
pip install FabOMatic
```

* Change defaults in conf/settings.toml (see below)

* Test it with

```shell
python -m FabOMatic 5
```

* After installation login with default admin email in settings file and "admin" password.

> Default URL is https://HOSTNAME:23336/

* Setup backup strategy for database (database.sqldb), which is automatically created on first run.

* Setup systemd to automatically launch Python module on boot with user profile:

See sample configuration example in doc/systemd

## How to upgrade release

* Use pip --upgrade :

```shell
pip install FabOMatic --upgrade
```

* Review settings.toml file after installation.

* Database upgrades are applied by Alembic at start of the backend and shall not need user interaction.

## Configuration file defaults

* See file conf\settings.toml to setup MQTT server, database connections, SMTP for "forgot password" email. Example below

```text
[database]
url = "sqlite:///machines.sqldb"
name = "fablab"

[MQTT]
broker = "127.0.0.1"
port = 1883
client_id = "backend"
topic = "machine/"        # root topic. Subtopics will be /machine/<ID> will be subscribed
reply_subtopic = "/reply"  # appended to the machine topics for replies by backend. E.g. machine/1/reply
stats_topic = "stats/"

[web]
secret_key = "some_long_hex_string_1234gs"  # Used for encryption
default_admin_email = "admin@fablag.org"    # Used for initial login

[email]
server = "smtp.google.com"
port = 587
use_tls = true
username = ""
password = ""

```

## Developper notes

* Developped with VSCode, extensions: Python, SQLTools, SQLTools SQLite, Black formatter

* Create a python venv with Python >=3.10 and make sure your terminal has activated the venv

* Test settings are into tests\test_settings.toml file, to run tests from root folder (or Terminal)

```shell
pytest -v
```

* How to run the server from Terminal (from root folder)

```shell
pip install -e . 
python ./run.py
```

* Package requirements / How to package (see [Python docs(https://packaging.python.org/en/latest/tutorials/packaging-projects/)])

```shell
pip install --upgrade build
pip install --upgrade twine
```

To update distribution

```shell
python -m build
python -m twine upload dist/*
```

* To handle schema changes with existing installations, changes the database/models.py, check that the changes are properly captured by alembic, then generate a migration script, and apply it. Then commit all files and publish a new revision.

```shell
alembic check
alembic revision --autogenerate -m "Description of change"
alembic upgrade head
```

* To handle data migration you have to manually edit the generated migration file in alembic folder.

* After testing the new database schema, archive a copy of simple-db.sqldb (generated by pytest) into tests/databases folder with the revision name. This will ensure migrations will be tested on this new release in the future.

* Translations with Babel

Initial extract (run from src/FabOMatic folder)

```shell
pybabel extract -F babel.cfg -o messages.pot ./
```

Update merging the changes the translations files

```shell
pybabel update -i messages.pot -d translations
```

Adding a new locale

```shell
pybabel init -i messages.pot -d translations -l <locale>
```

Compile the changes

```shell
pybabel compile -d translations
```

## GDPR compliance ⚖️

Members' RFID card will be tied to a physical person and therefore, you *must* collect written consent of this person as part of membership agreement.

### Suggested GDPR agreement

* The reason for data collection is *to control FabLab equipment usage for better maintenance of equipment and physical safety of the FabLab users*.
* The data conservation period for RFID master data is for the duration of the membership to the FabLab with a minimum of *one year*.
* The data conservation period of historical records, including user name, time of use, machine used, maintenance operation performed is *one year*.
* After 1 year, the historical nominative data is automatically replaced with an anonymous user data.
* The system may collect RFID tags ID from nearby cards, not tied to the FabLab RFID master data. Such information will be deleted after *one month*.
* The responsible persons for data treatment are the Fab-O-Matic administrative users.
* The collected information is not shared outside Fab-O-Matic system or disclosed outside Fab-O-Matic admins.

### What you need to do

* You *need* to secure access to the Fab-O-Matic backend webserver and physical hosts (use a proper password policy).
* You *need* to schedule a daily cron job in order to ensure data is deleted from database and logfiles

```shell
python -m FabOMatic --purge
journalctl --vacuum-time=1y
```

* To garantee data access requests, you can use the Excel export feature filtering data by the user.
* To garantee right to deletion, you can use the Delete buttons on Use, Interventions and User pages.

## Main revision log

| Version | When | Release notes |
|--|--|--|
| 0.0.18 | January 2024 | first revision with Alembic for database version tracking to handle graceful updates |
| 0.1.15 | February 2024 | improved UI on mobile, fixed duplicated uses, added grace period definition on machine types, added system page |
| 0.2.0 | February 2024 | UI translations with flask-babel (IT, EN), added boards details in system page |
| 0.3.0 | May 2024 | User authorizations can be disabled by Machine type, Maintenance URL field added, System page improvements (DB reload, log files)  |
| 0.4.0 | June 2024 | Buffered messages sent by Fab-O-Matic boards are flagged with a clock icon. |
| 0.5.0 | June 2024 | First release on PyPi. Renamed to FabOMatic. Added GDPR compliance (purge function) |
| 0.6.0 | August 2024 | Added remote commands from backend for cloud-enabled printers like BambuLab |
