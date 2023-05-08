from rfid_backend_FABLAB_BG.database.database import DatabaseBackend
from rfid_backend_FABLAB_BG.mqtt.machine_logic import MachineLogic
from rfid_backend_FABLAB_BG.mqtt.mqtt_types import *


class Mapper:
    """ This class provides the handlers that incoming parsed MQTT message 
    to the machine_logic instance, and returns the response as a string ."""

    def __init__(self, database: DatabaseBackend):
        self._mapping = {}
        MachineLogic.database = database

    def handleUserQuery(self, machine: str, userquery: UserQuery) -> str:
        if machine not in self._mapping:
            self._mapping[machine] = MachineLogic(machine)

        response = self._mapping[machine].isAuthorized(userquery.uid)
        return response.serialize()

    def handleStartUseQuery(self, machine: str, startUse: StartUseQuery) -> str:
        if machine not in self._mapping:
            self._mapping[machine] = MachineLogic(machine)

        response = self._mapping[machine].startUse(startUse.uid)
        return response.serialize()

    def handleEndUseQuery(self, machine: str, stopUse: EndUseQuery) -> str:
        if machine not in self._mapping:
            self._mapping[machine] = MachineLogic(machine)

        response = self._mapping[machine].endUse(
            stopUse.uid, stopUse.duration)
        return response.serialize()

    def handleMaintenanceQuery(self, machine: str, maintenance: RegisterMaintenanceQuery) -> str:
        if machine not in self._mapping:
            self._mapping[machine] = MachineLogic(machine)

        response = self._mapping[machine].registerMaintenance(
            maintenance.card_uuid)
        return response.serialize()

    def handleAliveQuery(self, machine: str, alive: AliveQuery) -> str:
        if machine not in self._mapping:
            self._mapping[machine] = MachineLogic(machine)

        self._mapping[machine].machineAlive()
        return None

    def handleMachineQuery(self, machine: str, machineQuery: MachineQuery) -> str:
        if machine not in self._mapping:
            self._mapping[machine] = MachineLogic(machine)

        return self._mapping[machine].machineStatus().serialize()
