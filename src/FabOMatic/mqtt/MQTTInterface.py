""" A module for the MQTTInterface class. """

import logging
import os
import json
from time import sleep
import toml
import paho.mqtt.client as mqtt
from .mqtt_types import BaseJson, Parser

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(MODULE_DIR, "conf", "settings.toml")


class MQTTInterface:
    """
    A class representing an MQTT interface.

    Attributes:
        _settings_path (str): The path to the MQTT settings file.
        _broker (str): The MQTT broker address.
        _port (int): The MQTT broker port.
        _client_id (str): The client ID for connecting to the MQTT broker.
        _topic (str): The MQTT topic for publishing queries.
        _reply_subtopic (str): The MQTT subtopic for publishing replies.
        _statsTopic (str): The MQTT topic for publishing statistics.
        _messageCallback (callable): The callback function for processing received messages.
        _connected (bool): Indicates whether the MQTT interface is connected to the broker.
        _handlers (dict): A dictionary of message handlers.
        _msg_send_count (int): The count of sent messages.
        _msg_recv_count (int): The count of received messages.
    """

    def __init__(self, path=CONFIG_FILE):
        """
        Initializes an instance of the MQTTInterface class.

        Args:
            path (str, optional): The path to the MQTT settings file. Defaults to CONFIG_FILE.
        """
        self._settings_path = path
        self._messageCallback = None
        self._connected = False
        self._handlers = {}
        self._loadSettings()
        self._msg_send_count = 0
        self._msg_recv_count = 0

    def _loadSettings(self) -> None:
        """
        Loads the MQTT settings from the settings file.
        """
        settings: dict = toml.load(self._settings_path)["MQTT"]
        self._broker = settings["broker"]
        self._port = settings["port"]
        self._client_id = settings["client_id"]
        self._topic = settings["topic"]
        self._reply_subtopic = settings["reply_subtopic"]

        if "request_subtopic" in settings.keys():
            self._request_subtopic = settings["request_subtopic"]
        else:
            self._request_subtopic = "/request"

        self._statsTopic = settings["stats_topic"] + "/" + self._client_id
        logging.info("Loaded MQTT settings from file %s", self._settings_path)

    def _extractMachineFromTopic(self, topic: str) -> str:
        """
        Extracts the machine name from the MQTT topic.

        Args:
            topic (str): The MQTT topic.

        Returns:
            str: The machine name extracted from the topic.
        """
        elems = topic.split("/")
        if len(elems) < 2:
            return None
        if elems[0].capitalize() != self._topic.capitalize():
            return None

        return elems[1]

    def _onMessage(self, *args):
        """
        Callback function for handling received MQTT messages.

        Args:
            *args: Variable length argument list.
        """
        topic: str = args[2].topic
        message: str = args[2].payload.decode("utf-8")
        self._msg_recv_count += 1

        if topic.endswith(self._reply_subtopic) or topic.endswith(self._request_subtopic):
            # ignore own answers
            logging.debug("Ignoring notification on topic : %s", topic)
            return

        machine = self._extractMachineFromTopic(topic)
        if not machine:
            logging.warning("Could not extract machine from topic : %s", topic)
            return

        if self._messageCallback is None:
            logging.warning("No message callback set, message will be ignored")
            return

        try:
            query: BaseJson = Parser.parse(message)
            if query is not None and machine.isdigit():
                self._messageCallback(int(machine), query)
        except ValueError:
            logging.warning("Invalid message received: %s on machine %s", message, machine)
            return

    def publishQuery(self, machine: str, message: str) -> bool:
        """
        Publishes a query message to a specific machine.

        Args:
            machine (str): The ID of the machine.
            message (str): The query message.

        Returns:
            bool: True if the message was published successfully, False otherwise.
        """
        return self._publish(f"{self._topic}{machine}", message)

    def publishRequest(self, machine: str, message: str) -> bool:
        """
        Publishes a request message to a specific machine.

        Args:
            machine (str): The ID of the machine.
            message (str): The request message as a JSON-string.

        Returns:
            bool: True if the message was published successfully, False otherwise.
        """
        return self._publish(f"{self._topic}/{machine}{self._request_subtopic}", message)

    def publishReply(self, machine: str, message: str) -> bool:
        """
        Publishes a reply message to a specific machine.

        Args:
            machine (str): The ID of the machine.
            message (str): The reply message.

        Returns:
            bool: True if the message was published successfully, False otherwise.
        """
        self._msg_send_count += 1
        return self._publish(f"{self._topic}/{machine}{self._reply_subtopic}", message)

    def _publish(self, topic: str, message: str) -> bool:
        """
        Publishes a message to the MQTT broker.

        Args:
            topic (str): The MQTT topic.
            message (str): The message to publish.

        Returns:
            bool: True if the message was published successfully, False otherwise.
        """
        if self.connected:
            result = self._client.publish(topic, message, qos=0, retain=False)
            logging.debug("Publishing %s : %s, result: %s", topic, message, result)
            return True
        logging.error("Not connected to MQTT broker %s", self._broker)
        return False

    def _onDisconnect(self, client, userdata, rc):
        """
        Callback function for handling MQTT disconnection.

        Args:
            client: The MQTT client.
            userdata: The user data.
            rc (int): The reason code for disconnection.
        """
        if self._connected:
            logging.info("Disconnected to MQTT broker reason code:%d", rc)
        self._connected = False
        self._client.loop_stop()

    def _onConnect(self, *args):
        """
        Callback function for handling MQTT connection.

        Args:
            *args: Variable length argument list.
        """
        if not self._connected:
            logging.info("Connected to MQTT broker [%s:%s] as %s", self._broker, self._port, self._client_id)
        self._connected = True

    def connect(self):
        """
        Connects to the MQTT broker.
        """
        self._client = mqtt.Client(self._client_id, clean_session=False)
        self._client.on_message = self._onMessage
        self._client.on_disconnect = self._onDisconnect
        self._client.on_connect = self._onConnect
        self._client.username_pw_set("backend", None)

        logging.debug("Connecting to MQTT broker [%s:%s] as %s...", self._broker, self._port, self._client_id)

        self._client.connect(self._broker, port=self._port)
        # Subscribe to all first-level subtopics of machine
        topic = self._topic + "/+"
        result = self._client.subscribe(topic, qos=1)
        if result[0] != mqtt.MQTT_ERR_SUCCESS:
            logging.error("Failure to subscribe topic [%s] : error %d", topic, result[0])
        else:
            logging.debug("Subscribed to topic [%s]", topic)

        self._client.loop_start()
        sleep(0.5)

    def setMessageCallback(self, callback: callable):
        """
        Sets the callback function for processing received messages.

        Args:
            callback (callable): The callback function.
        """
        self._messageCallback = callback

    def disconnect(self):
        """
        Disconnects from the MQTT broker.
        """
        self._client.unsubscribe(self._topic)
        self._client.loop_stop()
        self._client.disconnect()

    @property
    def connected(self):
        """
        Gets the connection status to the MQTT broker.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._connected

    def stats(self) -> dict:
        """
        Gets the statistics of the MQTT interface.

        Returns:
            dict: A dictionary containing the statistics.
        """
        import socket

        hostname = socket.gethostname()
        ipaddress = socket.gethostbyname(hostname)
        return {
            "Connected": self.connected,
            "Backend host": hostname,
            "Backend IP": ipaddress,
            "Received": self._msg_recv_count,
            "Sent": self._msg_send_count,
        }

    def publishStats(self):
        """
        Publishes the statistics to the MQTT broker.
        """
        self._publish(self._statsTopic, json.dumps(self.stats()))
