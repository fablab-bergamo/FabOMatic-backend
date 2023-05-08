import logging
from rfid_backend_FABLAB_BG.database.database import DatabaseBackend
from rfid_backend_FABLAB_BG.mqtt.mqtt_types import MachineResponse, SimpleResponse
from time import time


class MachineLogic:
    database: DatabaseBackend = None

    def __init__(self, machine_id):
        self._machine_id = machine_id
        self._last_alive = 0

        if MachineLogic.database is None:
            raise Exception("Database not initialized")

        machine_repo = MachineLogic.database.getMachineRepository()
        if machine_repo.get_by_id(machine_id) is None:
            raise Exception("Invalid machine id")

        logging.info(f"Machine logic instance for ID:{machine_id} initialized")

    def machineStatus(self):
        machine_repo = MachineLogic.database.getMachineRepository()
        machine = machine_repo.get_by_id(self._machine_id)
        if machine is None:
            return MachineResponse(True, False, False, False)

        return MachineResponse(True, True,
                               machine_repo.isMachineNeedingMaintenance(
                                   machine),
                               not machine.blocked)

    def machineAlive(self):
        """Called when a machine sends an alive message"""
        logging.debug(f"Machine {self._machine_id} alive")
        self._last_alive = time()

    def isAuthorized(self, card_uuid: str) -> SimpleResponse:
        machine_repo = MachineLogic.database.getMachineRepository()
        user_repo = MachineLogic.database.getUserRepository()
        user = user_repo.getUserByCardUUID(card_uuid)
        machine = machine_repo.get_by_id(self._machine_id)
        if machine is None or user is None:
            return SimpleResponse(False, "Invalid card or machine")

        if user_repo.IsUserAuthorizedForMachine(machine, user):
            return SimpleResponse(True)
        else:
            return SimpleResponse(False, "User not authorized")

    def startUse(self, card_uuid: str) -> SimpleResponse:
        user_repo = MachineLogic.database.getUserRepository()
        user = user_repo.getUserByCardUUID(card_uuid)
        if user is None:
            return SimpleResponse(False, "Invalid card")
        return SimpleResponse(False, "Not implemented")

    def endUse(self, card_uuid: str, duration_s: int) -> SimpleResponse:
        user_repo = MachineLogic.database.getUserRepository()
        user = user_repo.getUserByCardUUID(card_uuid)
        if user is None:
            return SimpleResponse(False, "Invalid card")

        return SimpleResponse(False, "Not implemented")

    def registerMaintenance(self, card_uuid: str) -> SimpleResponse:
        user_repo = MachineLogic.database.getUserRepository()
        user = user_repo.getUserByCardUUID(card_uuid)
        if user is None:
            return SimpleResponse(False, "Invalid card")

        return SimpleResponse(False, "Not implemented")
