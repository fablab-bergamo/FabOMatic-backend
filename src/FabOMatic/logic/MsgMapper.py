""" This module provides the MsgMapper class"""

import logging

from FabOMatic.database.DatabaseBackend import DatabaseBackend
from FabOMatic.mqtt import MQTTInterface
from FabOMatic.mqtt.mqtt_types import (
    UserQuery,
    StartUseQuery,
    InUseQuery,
    EndUseQuery,
    RegisterMaintenanceQuery,
    AliveQuery,
    MachineQuery,
    BaseJson,
    SimpleResponse,
)

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

    def getMachineLogic(self, mid: int) -> MachineLogic | None:
        """
        Retrieves the MachineLogic object associated with the given machine ID.

        Args:
            machineId (str): The ID of the machine.

        Returns:
            MachineLogic | None: The MachineLogic object if found, None otherwise.
        """
        if mid not in self._machines:
            try:
                self._machines[mid] = MachineLogic(mid)
                logging.info(
                    "Created MachineLogic instance for machine %s, %d machines total.", mid, len(self._machines)
                )
            except Exception as e:
                logging.error("MachineLogic creation exception %s", str(e))
                return None
        return self._machines[mid]

    def handleUserQuery(self, machine_logic: MachineLogic, userquery: UserQuery) -> str:
        response = machine_logic.isAuthorized(userquery.uid)
        logging.debug("User query: %s -> response: %s", userquery.toJSON(), response.serialize())
        return response.serialize()

    def handleStartUseQuery(self, machine_logic: MachineLogic, startUse: StartUseQuery) -> str:
        response = machine_logic.startUse(startUse.uid, startUse.replay)
        logging.info(
            "[Machine %d] Start use query: %s -> response: %s",
            machine_logic.getMachineId(),
            startUse.toJSON(),
            response.serialize(),
        )
        return response.serialize()

    def handleInUseQuery(self, machine_logic: MachineLogic, inUse: InUseQuery) -> str:
        response = machine_logic.inUse(inUse.uid, inUse.duration)
        logging.info(
            "[Machine %d] In use query: %s -> response: %s",
            machine_logic.getMachineId(),
            inUse.toJSON(),
            response.serialize(),
        )
        return response.serialize()

    def handleEndUseQuery(self, machine_logic: MachineLogic, stopUse: EndUseQuery) -> str:
        response = machine_logic.endUse(stopUse.uid, stopUse.duration, stopUse.replay)
        logging.info(
            "[Machine %d] End use query: %s -> response: %s",
            machine_logic.getMachineId(),
            stopUse.toJSON(),
            response.serialize(),
        )
        return response.serialize()

    def handleMaintenanceQuery(self, machine_logic: MachineLogic, maintenance: RegisterMaintenanceQuery) -> str:
        response = machine_logic.registerMaintenance(maintenance.uid, maintenance.replay)
        logging.info(
            "[Machine %d] Start use query: %s -> response: %s",
            machine_logic.getMachineId(),
            maintenance.toJSON(),
            response.serialize(),
        )
        return response.serialize()

    def handleAliveQuery(self, machine_logic: MachineLogic, alive: AliveQuery) -> str:
        """
        Handles an alive query message.

        Args:
            machine_logic (MachineLogic): The machine logic instance.
            alive (AliveQuery): The alive query message.

        Returns:
            str: None
        """
        machine_logic.machineAlive(alive)
        logging.debug("Alive query: %s", alive.toJSON())
        return None

    def handleMachineQuery(self, machine_logic: MachineLogic, machineQuery: MachineQuery) -> str:
        """
        Handles a machine query and returns the serialized machine status.

        Args:
            machine_logic (MachineLogic): The machine logic object.
            machineQuery (MachineQuery): The machine query object.

        Returns:
            str: The serialized machine status.
        """
        status = machine_logic.machineStatus()
        logging.debug("Machine query: %s -> response: %s", machineQuery.toJSON(), status.serialize())
        return status.serialize()

    def messageReceived(self, machine: int, query: BaseJson) -> bool:
        """This function is called when a message is received from the MQTT broker.
        It calls the appropriate handler for the message type."""

        if type(query) not in self._handlers:
            logging.warning(f"No handler for query {query} on machine {machine}")
            return False

        machine_logic = self.getMachineLogic(machine)
        if machine_logic is None:
            logging.error(f"Failed to create MachineLogic instance for machine {machine}")
            response = SimpleResponse(False, "Invalid machine ID").serialize()
            if not self._mqtt.publishReply(machine, response):
                logging.error(f"Failed to publish response for machine {machine} to MQTT broker: {response}")
            return False

        response = self._handlers[type(query)](machine_logic, query)

        if response is not None:
            if not self._mqtt.publishReply(machine, response):
                logging.error(f"Failed to publish response for machine {machine} to MQTT broker: {response}")
                return False
        else:
            logging.warning(f"Machine {machine} query: {query.toJSON()} -> no response")
            return False

        return True

    def registerHandlers(self):
        """This function registers the handlers for the different message types from the boards."""
        self._setHandler(AliveQuery, self.handleAliveQuery)
        self._setHandler(MachineQuery, self.handleMachineQuery)
        self._setHandler(UserQuery, self.handleUserQuery)
        self._setHandler(StartUseQuery, self.handleStartUseQuery)
        self._setHandler(InUseQuery, self.handleInUseQuery)
        self._setHandler(EndUseQuery, self.handleEndUseQuery)
        self._setHandler(RegisterMaintenanceQuery, self.handleMaintenanceQuery)
        self._mqtt.setMessageCallback(self.messageReceived)

    def _setHandler(self, query: type, handler: callable):
        self._handlers[query] = handler

    def remoteStart(self, machine_id: int, card_uuid: str) -> bool:
        machine_logic = self.getMachineLogic(machine_id)

        if machine_logic is None:
            logging.error(f"Failed to create MachineLogic instance for machine {machine_id}")
            return False

        return machine_logic.remoteStart(card_uuid, self._mqtt)

    def remoteStop(self, machine_id: int, card_uuid: str) -> bool:
        machine_logic = self.getMachineLogic(machine_id)

        if machine_logic is None:
            logging.error(f"Failed to create MachineLogic instance for machine {machine_id}")
            return False

        return machine_logic.remoteStop(card_uuid, self._mqtt)
