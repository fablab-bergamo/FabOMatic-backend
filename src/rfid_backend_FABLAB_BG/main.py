"""Main module of the backend."""
from time import sleep, time
import logging
import colorlog
import os
from logging.handlers import RotatingFileHandler

from database import DatabaseBackend
from mqtt import MQTTInterface, Mapper
from rfid_backend_FABLAB_BG.mqtt.mqtt_types import *


class Backend:
    """Backend class."""

    def __init__(self):
        self._m = MQTTInterface()
        self._db = DatabaseBackend()
        self._mapper: Mapper = Mapper(self._db)
        self._last_alive = {}

    def registerHandlers(self):
        self.setHandler(AliveQuery, self._mapper.handleAliveQuery)
        self.setHandler(MachineQuery, self._mapper.handleMachineQuery)
        self.setHandler(UserQuery, self._mapper.handleUserQuery)
        self.setHandler(StartUseQuery, self._mapper.handleStartUseQuery)
        self.setHanlder(EndUseQuery, self._mapper.handleEndUseQuery)
        self.setHandler(RegisterMaintenanceQuery,
                        self._mapper.handleMaintenanceQuery)

    def connect(self) -> bool:
        """Connect to the MQTT broker and the database."""
        try:
            self._m.connect()
            self.createDatabase()
            self.registerHandlers()
            return True
        except Exception as e:
            logging.error("Connection failed: %s", e, exc_info=True)
            return False

    def disconnect(self):
        """Disconnect from the MQTT broker """
        self._m.disconnect()

    def stats(self) -> str:
        """Return a string with the stats of the backend."""
        machines = self._db.getMachineRepository().get_all()
        users = self._db.getUserRepository().get_all()
        return f"{len(machines)} machines, {len(users)} users loaded."

    def createDatabase(self) -> None:
        """Create the database."""
        self._db.createDatabase()


def configure_logger():
    # Create a logger object
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create a formatter for the logs
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Create a rotating file handler with a maximum size of 1 MB
    log_file = os.path.join(os.path.dirname(__file__), 'log.txt')
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1000000, backupCount=1)
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger object
    logger.addHandler(file_handler)

    # Create a stream handler to log to console
    console_handler = logging.StreamHandler()
    formatter2 = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        })
    console_handler.setFormatter(formatter2)

    # Add the stream handler to the logger object
    logger.addHandler(console_handler)


def main():
    """Main function of the backend."""
    configure_logger()
    logging.info("Starting backend...")
    back = Backend()

    while not back.connect():
        logging.warning("Failed to connect. Retrying...")
        sleep(5)

    logging.info("Connected to MQTT broker and database.")
    print(back.stats())

    while True:
        logging.debug("I'm alive")
        sleep(1)


if __name__ == "__main__":
    main()
