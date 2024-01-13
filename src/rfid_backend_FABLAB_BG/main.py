"""Main module of the backend."""
import logging
import threading
from time import sleep

from rfid_backend_FABLAB_BG.database.DatabaseBackend import DatabaseBackend
from rfid_backend_FABLAB_BG.mqtt.MQTTInterface import MQTTInterface
from rfid_backend_FABLAB_BG.logic.MsgMapper import MsgMapper
from rfid_backend_FABLAB_BG.logger import configure_logger


class Backend:
    """Backend class."""

    def __init__(self):
        self._db = DatabaseBackend()

        self._mqtt = MQTTInterface()
        self._mapper = MsgMapper(self._mqtt, self._db)
        self._mapper.registerHandlers()
        self._flaskThread = None

    def connect(self) -> bool:
        """Connect to the MQTT broker and the database."""
        try:
            session = self._db.getSession()
            logging.info(f"Session info: {session.info}")
            self.createDatabase()
            self._mqtt.connect()
            return True
        except Exception as ex:
            logging.error("Connection failed: %s", ex, exc_info=True)
            return False

    @property
    def connected(self) -> bool:
        """Check if the MQTT broker is connected."""
        return self._mqtt.connected

    def disconnect(self):
        """Disconnect from the MQTT broker"""
        self._mqtt.disconnect()

    def publishStats(self):
        self._mqtt.publishStats()

    def createDatabase(self) -> None:
        """Create the database if needed."""
        self._db.createDatabase()


_flaskThread: threading.Thread = None


def _startApp() -> None:
    from rfid_backend_FABLAB_BG.web.webapplication import app

    app.run(host="0.0.0.0", port=23336, debug=True, use_reloader=False, ssl_context="adhoc")


def startServer() -> None:
    global _flaskThread
    _flaskThread = threading.Thread(target=lambda: _startApp(), daemon=True)
    _flaskThread.start()


def start(loglevel):
    """Main function of the backend."""
    configure_logger(loglevel)
    logging.info("Starting backend...")
    back = Backend()
    startServer()

    while True:
        if not back.connected:
            if not back.connect():
                logging.error("Failed to connect to Database or MQTT broker")
        else:
            back.publishStats()
        sleep(5)
