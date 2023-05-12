import logging
import os

import paho.mqtt.client as mqtt
import toml
from .mqtt_types import *

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(MODULE_DIR, "conf\\settings.toml")


class MQTTInterface:
    def __init__(self, path=CONFIG_FILE):
        self._settings_path = path
        self._messageCallback = None
        self._connected = False
        self._handlers = {}
        self._loadSettings()
        self._msg_send_count = 0
        self._msg_recv_count = 0

    def _loadSettings(self) -> None:
        settings = toml.load(self._settings_path)["MQTT"]
        self._broker = settings["broker"]
        self._port = settings["port"]
        self._client_id = settings["client_id"]
        self._topic = settings["topic"]
        self._reply_subtopic = settings["reply_subtopic"]
        self._statsTopic = settings["stats_topic"]
        logging.info("Loaded MQTT settings from file %s", self._settings_path)

    def _extractMachineFromTopic(self, topic: str) -> str:
        if not topic.startswith(self._topic[:-1]):
            return None

        return topic.split("/")[-1:][0]

    def _onMessage(self, *args):
        topic = args[2].topic
        message = args[2].payload.decode("utf-8")
        self._msg_recv_count += 1

        machine = self._extractMachineFromTopic(topic)
        if not machine:
            return

        try:
            query = Parser.parse(message)
            if query is not None:
                self._messageCallback(machine, query)
        except ValueError:
            logging.warning("Invalid message received: %s on machine %s", message, machine)
            return

    def publishQuery(self, machine: str, message: str) -> bool:
        return self._publish(f"{self._topic}{machine}", message)

    def publishReply(self, machine: str, message: str) -> bool:
        self._msg_send_count += 1
        return self._publish(f"{self._topic}{machine}/reply", message)

    def _publish(self, topic: str, message: str) -> bool:
        if self.connected:
            result = self._client.publish(topic, message)
            logging.info("Publishing %s : %s, result: %s", topic, message, result)
            return True
        logging.error("Not connected to MQTT broker %s", self._broker)
        return False

    def _onDisconnect(self, *args):
        self._connected = False

    def connect(self):
        self._client = mqtt.Client(self._client_id)
        self._client.on_message = self._onMessage
        self._client.on_disconnect = self._onDisconnect

        self._client.connect(self._broker, port=self._port)
        # Subscribe to all first-level subtopics of machine
        self._client.subscribe(self._topic + "+")
        self._client.loop_start()
        logging.info("Connected to MQTT broker %s", self._broker)
        self._connected = True

    def setMessageCallback(self, callback: callable):
        self._messageCallback = callback

    def disconnect(self):
        self._client.unsubscribe(self._topic)
        self._client.loop_stop()
        self._client.disconnect()
        logging.info("Disconnected from MQTT broker %s", self._broker)

    @property
    def connected(self):
        return self._connected

    def stats(self) -> dict:
        return {
            "Connected": self.connected,
            "MQTT Broker": self._broker,
            "Received": self._msg_recv_count,
            "Sent": self._msg_send_count,
        }

    def publishStats(self):
        self._publish(self._statsTopic, json.dumps(self.stats()))
