# rfid-backend

Build & Test status [![Python package](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/python-package.yml/badge.svg)](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/python-package.yml)

## Python dependencies

* toml (for configuration file)
* paho.mqtt (for MQTT client)
* SQLAlchemy (for database interface)
* colorlog (for nicer logs in the console)

## Backend runtime requirements

* An external MQTT Broker. Mosquitto has been used for testing.
* A database engine. SQLAlchemy supports several, but this has been tested with SQLite only (so far)

## Installation instructions

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

* Setup backup strategy for SQLDB file.

## How to upgrade release

* Use pip --upgrade :

```shell
pip install -i https://test.pypi.org/pypi/ --extra-index-url https://pypi.org/simple rfid_backend_FABLAB_BG --upgrade
```

* Review settings.toml file after installation.

* TODO : database schema upgrade instructions

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

## Dev environment settings

* Developped with VSCode
* Create a python venv with Python >=3.10
* Test settings are into tests\test_settings.toml file, to run tests from root folder (or Terminal)

```shell
pytest -v
```

* VSCode extensions : Python, Black extension for automatic code formatting
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
py -m build
py -m twine upload --repository testpypi dist/*
```
