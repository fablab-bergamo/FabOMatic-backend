"""Main module of the backend."""
import logging
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

    def connect(self) -> bool:
        """Connect to the MQTT broker and the database."""
        try:
            self._mqtt.connect()
            self.createDatabase()
            return True
        except Exception as ex:
            logging.error("Connection failed: %s", ex, exc_info=True)
            return False

    def disconnect(self):
        """Disconnect from the MQTT broker"""
        self._mqtt.disconnect()

    def publishStats(self):
        self._mqtt.publishStats()

    def createDatabase(self) -> None:
        """Create the database if needed."""
        self._db.createDatabase()


def main():
    """Main function of the backend."""
    configure_logger()
    logging.info("Starting backend...")
    back = Backend()

    while not back.connect():
        logging.warning("Failed to connect. Retrying...")
        sleep(5)

    logging.info("Connected to MQTT broker and database.")
    logging.info(back.stats())

    while True:
        back.publishStats()
        sleep(1)


def test():
    configure_logger()
    back = Backend()
    back.connect()

    if not back._mqtt.connected:
        logging.error("MQTT not connected")
        return

    while True:
        logging.debug("TEST - I'm alive")
        with back._db.getSession() as session:
            for mac in back._db.getMachineRepository(session).get_all():
                back._mqtt.publishQuery(mac.machine_id, '{"action": "alive"}')
                back._mqtt.publishQuery(mac.machine_id, '{"action": "check_machine"}')
                back._mqtt.publishQuery(mac.machine_id, '{"action": "alive"}')
                back._mqtt.publishQuery(mac.machine_id, '{"action": "check_machine"}')
                back._mqtt.publishQuery(mac.machine_id, '{"action": "check_user", "uid": "1234567890"}')
                back._mqtt.publishQuery(mac.machine_id, '{"action": "startuse", "uid": "1234567890"}')
                back._mqtt.publishQuery(mac.machine_id, '{"action": "stopuse", "uid": "1234567890", "duration": 10}')
                back._mqtt.publishQuery(mac.machine_id, '{"action": "maintenance", "uid": "1234567890"}')
        back.publishStats()
        sleep(1)
