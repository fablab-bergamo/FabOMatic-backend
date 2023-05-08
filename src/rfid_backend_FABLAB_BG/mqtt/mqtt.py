import os

import paho.mqtt.client as mqtt
import toml
import logging

from rfid_backend_FABLAB_BG.mqtt.mqtt_types import AliveQuery, EndUseQuery, MachineQuery, Parser, StartUseQuery, UserQuery

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(MODULE_DIR, "conf\\settings.toml")


class MQTTInterface:
    def __init__(self, path=CONFIG_FILE):
        self._settings_path = path
        self._messageCallback = None
        self._connected = False

        self._awaiting_authorization = set()
        self._machineAlive = {}

        self._loadSettings()

    def _loadSettings(self) -> None:
        settings = toml.load(self._settings_path)["MQTT"]
        self._broker = settings["broker"]
        self._port = settings["port"]
        self._client_id = settings["client_id"]
        self._topic = settings["topic"]
        self._reply_subtopic = settings["reply_subtopic"]
        logging.info("Loaded MQTT settings from file %s", self._settings_path)

    def _extractMachineFromTopic(self, topic: str) -> str:
        if not topic.startswith(self._topic[:-1]):
            return None

        return topic.split("/")[-1:][0]

    def _onMessage(self, *args):
        topic = args[2].topic
        message = args[2].payload.decode("utf-8")

        if self._messageCallback is not None:
            self._messageCallback(topic, message)

        machine = self._extractMachineFromTopic(topic)
        if not machine:
            return

        try:
            query = Parser.parse(message)
            if type(query) not in self._handlers:
                logging.warning(
                    f"No handler for query {query} on topic {topic}")
                return

            logging.debug(
                f"Handling query {query} with handler {self._handlers[type(query)]} on topic {topic}")

            response = self._handlers[type(query)](machine, query)

            if response is not None:
                logging.debug("Sending response %s on topic %s", response,
                              f"{self._topic}{machine}/{self._reply_subtopic}")
                self._client.publish(
                    f"{self._topic}{machine}/{self._reply_subtopic}", response)

        except ValueError:
            logging.warning(
                f"Invalid message received: {message} on topic {topic}")
            return

    def _onDisconnect(self, *args):
        self._connected = False


    def connect(self):
        self._client = mqtt.Client(self._client_id)
        self._client.on_message = self._onMessage
        self._client.on_disconnect = self._onDisconnect

        self._client.connect(self._broker, port=self._port)
        self._connected = True
        self._client.subscribe(self._topic)
        self._client.loop_start()
        logging.info("Connected to MQTT broker %s", self._broker)

    def setMessageCallback(self, callback: callable):
        self._messageCallback = callback

    def setHandler(self, query: type, handler: callable):
        self._handlers[query] = handler

    def disconnect(self):
        self._client.unsubscribe(self._topic)
        self._client.loop_stop()
        self._client.disconnect()
        logging.info("Disconnected from MQTT broker %s", self._broker)

    @property
    def connected(self):
        return self._connected
