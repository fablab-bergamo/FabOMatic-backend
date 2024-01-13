import unittest

from rfid_backend_FABLAB_BG.mqtt.mqtt_types import (
    UserQuery,
    AliveQuery,
    MachineQuery,
    StartUseQuery,
    EndUseQuery,
    RegisterMaintenanceQuery,
)

from rfid_backend_FABLAB_BG.mqtt.MQTTInterface import MQTTInterface
from rfid_backend_FABLAB_BG.logic.MsgMapper import MsgMapper
from rfid_backend_FABLAB_BG.logic.MachineLogic import MachineLogic
from tests.common import TEST_SETTINGS_PATH, get_simple_db


class TestLogic(unittest.TestCase):
    def test_machine_logic(self):
        db = get_simple_db()
        with db.getSession() as session:
            MachineLogic.database = db
            mac = db.getMachineRepository(session).get_all()[0]
            user = db.getUserRepository(session).get_all()[0]

            user.card_UUID = "1234"
            db.getUserRepository(session).update(user)

            ml = MachineLogic(mac.machine_id)
            status = ml.machineStatus()
            self.assertTrue(status.is_valid, "Machine is not valid")
            self.assertTrue(status.request_ok, "Request is not ok")
            self.assertFalse(status.maintenance, "Machine is in maintenance")
            self.assertTrue(status.allowed, "Machine is not allowed")

            mac.blocked = True
            db.getMachineRepository(session).update(mac)
            status = ml.machineStatus()
            self.assertTrue(status.is_valid, "Machine is not valid")
            self.assertTrue(status.request_ok, "Request is not ok")
            self.assertFalse(status.maintenance, "Machine is in maintenance")
            self.assertFalse(status.allowed, "Machine is allowed")

            mac.blocked = False
            db.getMachineRepository(session).update(mac)

            ml.machineAlive()

            response = ml.isAuthorized("1234")
            self.assertTrue(response.request_ok, "isAuthorized failed")

            response = ml.startUse("1234")
            self.assertTrue(response.request_ok, "startUse failed")

            response = ml.endUse("1234", 123)
            self.assertTrue(response.request_ok, "endUse failed")

            ml.registerMaintenance("1234")
            self.assertTrue(response.request_ok, "registerMaintenance failed")

    def test_msg_mapper(self):
        db = get_simple_db()

        mqtt = MQTTInterface(TEST_SETTINGS_PATH)
        mapper = MsgMapper(mqtt, db)
        mapper.registerHandlers()

        # Try all messagges
        query = UserQuery("1234")
        mapper.messageReceived("1", query)
        query = AliveQuery()
        mapper.messageReceived("1", query)
        query = MachineQuery()
        mapper.messageReceived("1", query)
        query = StartUseQuery("1234")
        mapper.messageReceived("1", query)
        query = EndUseQuery("1234", 123)
        mapper.messageReceived("1", query)
        query = RegisterMaintenanceQuery("1234")
        mapper.messageReceived("1", query)
