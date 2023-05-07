# rfid-backend

Build & Test status [![Python package](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/python-package.yml/badge.svg)](https://github.com/fablab-bergamo/rfid-backend/actions/workflows/python-package.yml)

## Python dependencies

* toml (for configuration file)
* paho.mqtt (for MQTT client)
* SQLAlchemy (for database interface)

## Backend runtime requirements

* An external MQTT Broker. Mosquitto has been used for testing.
* A database engine. SQLAlchemy supports several, but this has been tested with SQLite only.

## Configuration

* See file conf\settings.toml

