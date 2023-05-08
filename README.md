# rfid-backend

Build & Test status [![Python package](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/python-package.yml/badge.svg)](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/python-package.yml)

## Python dependencies

* toml (for configuration file)
* paho.mqtt (for MQTT client)
* SQLAlchemy (for database interface)
* colorlog (for nicer logs in the console)

## Backend runtime requirements

* An external MQTT Broker. Mosquitto has been used for testing.
* A database engine. SQLAlchemy supports several, but this has been tested with SQLite only.

## Configuration

* See file conf\settings.toml to setup MQTT server, database connections.

## Dev environments

* Developped with VSCode with Python extension. Create a python venv with Python >=3.11. To run tests, install pytest from Terminal window.
* Test settings are into tests\test_settings.toml file

