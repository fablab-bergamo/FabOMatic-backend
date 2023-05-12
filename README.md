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

* Missing

## Configuration file

* See file conf\settings.toml to setup MQTT server, database connections. Example below

```
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
```

## Dev environment settings

* Developped with VSCode
* Create a python venv with Python >=3.11.
* Test settings are into tests\test_settings.toml file, to run tests from root folder (or Terminal)
```
pytest -v
```
* VSCode extensions : Python, Black extension for automatic code formatting
* How to run the server from Terminal (from root folder)
```
pip install -e . 
python .\run.py
```
* Package requirements / How to package (see https://packaging.python.org/en/latest/tutorials/packaging-projects/)
```
pip install --upgrade build
pip install --upgrade twine
```
To update
```
py -m build
py -m twine upload --repository testpypi dist/*
```
