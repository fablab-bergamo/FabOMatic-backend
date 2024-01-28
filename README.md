# rfid-backend

Build & Test status [![Python package](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/python-package.yml/badge.svg)](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/python-package.yml)

## What is this project?

* This is a web interface to handle a FabLab machines access through RFID access cards.

* [UI description](doc/UI.pdf)

* This python application runs a MQTT client and a Flask HTTPS application.

## Backend runtime requirements

* An external MQTT Broker. Mosquitto has been used for testing.
* A database engine. SQLAlchemy supports several, but this has been tested with SQLite only (so far)

## Installation instructions on Raspberry Pi Zero

* Install prerequisites (python 3.10+, rustc for cryptography, mosquitto, pip). It takes 3-4 hours on Raspberry Pi Zero to complete installation.

```shell
wget -qO - https://raw.githubusercontent.com/tvdsluijs/sh-python-installer/main/python.sh | sudo bash -s 3.10.9
sudo apt remove python3-apt
sudo apt install python3-apt
sudo curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
sudo apt install mosquitto
```
* Install from test pypi repository

```shell
pip install -i https://test.pypi.org/pypi/ --extra-index-url https://pypi.org/simple rfid_backend_FABLAB_BG
```

* Change defaults in conf/settings.toml (see below)

* Run it with

```shell
python -m rfid_backend_FABLAB_BG
```

* After installation login with default admin email in settings file and "admin" password.

> Default URL is https://HOSTNAME:23336/

* Setup backup strategy for database (database.sqldb), which is automatically created on first run.

* Setup systemd to automatically run on boot with user profile:


## How to upgrade release

* Use pip --upgrade :

```shell
pip install -i https://test.pypi.org/pypi/ --extra-index-url https://pypi.org/simple rfid_backend_FABLAB_BG --upgrade
```

* Review settings.toml file after installation.

* Database upgrades are applied by Alembic on start of the backend.

## Configuration file

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
python -m twine upload --repository testpypi dist/*
```

* To handle schema changes with existing installations, changes the database/models.py, check that the changes are properly captured by alembic, then generate a migration script, and apply it. Then commit all files and publish a new revision. 

```shell
alembic check
alembic revision --autogenerate -m "Description of change"
alembic upgrade head
```

* To handle data migration you have to manually edit the generated migration file in alembic folder.

## Main revision log

| Version | When | Release notes |
|--|--|--|
| 0.0.18 | January 2024 | first revision with Alembic for database version tracking to handle graceful updates |
