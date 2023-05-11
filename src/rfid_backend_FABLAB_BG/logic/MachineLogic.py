import logging

from rfid_backend_FABLAB_BG.mqtt.mqtt_types import *
from time import time

from rfid_backend_FABLAB_BG.database.DatabaseBackend import DatabaseBackend


class MachineLogic:
    database: DatabaseBackend = None

    def __init__(self, machine_id):
        self._machine_id = machine_id
        self._last_alive = 0

        if MachineLogic.database is None:
            raise Exception("Database not initialized")

        with self.database.getSession() as session:
            machine_repo = MachineLogic.database.getMachineRepository(
                session)
            if machine_repo.get_by_id(machine_id) is None:
                raise Exception("Invalid machine id")

        logging.info(f"Machine logic instance for ID:{machine_id} initialized")

    def machineStatus(self):
        try:
            with MachineLogic.database.getSession() as session:
                machine_repo = MachineLogic.database.getMachineRepository(
                    session)
                machine = machine_repo.get_by_id(self._machine_id)
                if machine is None:
                    return MachineResponse(True, False, False, False)

                return MachineResponse(True, True,
                                       machine_repo.getMachineMaintenanceNeeded(
                                           machine.machine_id)[0],
                                       not machine.blocked)
        except Exception as e:
            logging.error("machineStatus exception %s", str(e), exc_info=True)
            return MachineResponse(False, False, False, False)

    def machineAlive(self):
        """Called when a machine sends an alive message"""
        logging.debug(f"Machine {self._machine_id} alive")
        self._last_alive = time()

    def isAuthorized(self, card_uuid: str) -> SimpleResponse:
        try:
            with MachineLogic.database.getSession() as session:
                machine_repo = MachineLogic.database.getMachineRepository(
                    session)
                user_repo = MachineLogic.database.getUserRepository(
                    session)
                user = user_repo.getUserByCardUUID(card_uuid)
                machine = machine_repo.get_by_id(self._machine_id)
                if machine is None or user is None:
                    return SimpleResponse(False, "Invalid card or machine")

                if user_repo.IsUserAuthorizedForMachine(machine, user):
                    return SimpleResponse(True)
                else:
                    return SimpleResponse(False, "User not authorized")
        except Exception as e:
            logging.error("isAuthorized exception %s", str(e), exc_info=True)
            return SimpleResponse(False, "BACKEND EXCEPTION")

    def startUse(self, card_uuid: str) -> SimpleResponse:
        try:
            with MachineLogic.database.getSession() as session:
                user_repo = MachineLogic.database.getUserRepository(
                    session)
                user = user_repo.getUserByCardUUID(card_uuid)
                if user is None:
                    return SimpleResponse(False, "Invalid card")

                use_repo = MachineLogic.database.getUseRepository()
                use_repo.startUse(self._machine_id, user, time())

                return SimpleResponse(True, "")
        except Exception as e:
            logging.error("startUse exception %s", str(e), exc_info=True)
            return SimpleResponse(False, "BACKEND EXCEPTION")

    def endUse(self, card_uuid: str, duration_s: int) -> SimpleResponse:
        try:
            with MachineLogic.database.getSession() as session:
                user_repo = MachineLogic.database.getUserRepository(
                    session)
                user = user_repo.getUserByCardUUID(card_uuid)
                if user is None:
                    return SimpleResponse(False, "Invalid card")

                use_repo = MachineLogic.database.getUseRepository()
                use_repo.endUse(self._machine_id, user, duration_s)

                return SimpleResponse(True, "")
        except Exception as e:
            logging.error("enduse exception %s", str(e), exc_info=True)
            return SimpleResponse(False, "BACKEND EXCEPTION")

    def registerMaintenance(self, card_uuid: str) -> SimpleResponse:
        try:
            with MachineLogic.database.getSession() as session:
                user_repo = MachineLogic.database.getUserRepository(
                    session)
                user = user_repo.getUserByCardUUID(card_uuid)
                if user is None:
                    return SimpleResponse(False, "Wrong user card")

                intervention_repo = MachineLogic.database.getInterventionRepository(
                    session)
                intervention_repo.registerInterventionsDone(
                    self._machine_id, user.user_id)

                return SimpleResponse(True, "")
        except Exception as e:
            logging.error("registerMaintenance exception %s",
                          str(e), exc_info=True)
            return SimpleResponse(False, "BACKEND EXCEPTION")
