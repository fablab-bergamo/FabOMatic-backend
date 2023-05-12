import logging
from rfid_backend_FABLAB_BG.database.DatabaseBackend import DatabaseBackend
from rfid_backend_FABLAB_BG.mqtt import MQTTInterface
from rfid_backend_FABLAB_BG.mqtt.mqtt_types import *

from .MachineLogic import MachineLogic


class MsgMapper:
    """This class provides the handlers that incoming parsed MQTT message
    to the machine_logic instance, and returns the response as a string ."""

    def __init__(self, mqtt: MQTTInterface, db: DatabaseBackend):
        MachineLogic.database = db
        self._mqtt = mqtt
        self._db = db
        self._machines = {}
        self._handlers = {}

    def handleUserQuery(self, machine: str, userquery: UserQuery) -> str:
        if machine not in self._machines:
            self._machines[machine] = MachineLogic(machine)

        response = self._machines[machine].isAuthorized(userquery.uid)
        return response.serialize()

    def handleStartUseQuery(self, machine: str, startUse: StartUseQuery) -> str:
        if machine not in self._machines:
            self._machines[machine] = MachineLogic(machine)

        response = self._machines[machine].startUse(startUse.uid)
        return response.serialize()

    def handleEndUseQuery(self, machine: str, stopUse: EndUseQuery) -> str:
        if machine not in self._machines:
            self._machines[machine] = MachineLogic(machine)

        response = self._machines[machine].endUse(stopUse.uid, stopUse.duration)
        return response.serialize()

    def handleMaintenanceQuery(self, machine: str, maintenance: RegisterMaintenanceQuery) -> str:
        if machine not in self._machines:
            self._machines[machine] = MachineLogic(machine)

        response = self._machines[machine].registerMaintenance(maintenance.uid)
        return response.serialize()

    def handleAliveQuery(self, machine: str, alive: AliveQuery) -> str:
        if machine not in self._machines:
            self._machines[machine] = MachineLogic(machine)

        self._machines[machine].machineAlive()
        return None

    def handleMachineQuery(self, machine: str, machineQuery: MachineQuery) -> str:
        if machine not in self._machines:
            self._machines[machine] = MachineLogic(machine)

        return self._machines[machine].machineStatus().serialize()

    def messageReceived(self, machine: str, query: BaseJson) -> None:
        """This function is called when a message is received from the MQTT broker.
        It calls the appropriate handler for the message type."""

        if type(query) not in self._handlers:
            logging.warning(f"No handler for query {query} on machine {machine}")
            return

        response = self._handlers[type(query)](machine, query)

        if response is not None:
            logging.info("Machine %s query: %s -> response: %s", machine, query.toJSON(), response)
            if not self._mqtt.publishReply(machine, response):
                logging.error("Failed to publish response for machine %s to MQTT broker: %s", machine, response)

    def registerHandlers(self):
        """This function registers the handlers for the different message types from the boards."""
        self._setHandler(AliveQuery, self.handleAliveQuery)
        self._setHandler(MachineQuery, self.handleMachineQuery)
        self._setHandler(UserQuery, self.handleUserQuery)
        self._setHandler(StartUseQuery, self.handleStartUseQuery)
        self._setHandler(EndUseQuery, self.handleEndUseQuery)
        self._setHandler(RegisterMaintenanceQuery, self.handleMaintenanceQuery)
        self._mqtt.setMessageCallback(self.messageReceived)

    def _setHandler(self, query: type, handler: callable):
        self._handlers[query] = handler
