import os
import unittest

from rfid_backend_FABLAB_BG.mqtt.mqtt_types import *
from rfid_backend_FABLAB_BG.mqtt.MQTTInterface import MQTTInterface
from rfid_backend_FABLAB_BG.logic.MsgMapper import MsgMapper
from tests.common import configure_logger, TEST_SETTINGS_PATH, get_simple_db


class TestMQTT(unittest.TestCase):
    def test_json_deserialize(self):
        json_user_query = '{"action": "check_user", "uid": "1234567890"}'
        user_query = UserQuery.deserialize(json_user_query)
        self.assertEqual(user_query.uid, "1234567890")
        self.assertEqual(user_query.action, "check_user")
        self.assertEqual(user_query.__class__, UserQuery)

        json_machine_query = '{"action": "check_machine"}'
        machine_query = MachineQuery.deserialize(json_machine_query)
        self.assertEqual(machine_query.action, "check_machine")
        self.assertEqual(machine_query.__class__, MachineQuery)

        json_start_use_query = '{"action": "startuse", "uid": "1234"}'
        start_use_query = StartUseQuery.deserialize(json_start_use_query)
        self.assertEqual(start_use_query.uid, "1234")
        self.assertEqual(start_use_query.action, "startuse")
        self.assertEqual(start_use_query.__class__, StartUseQuery)

        json_stop_use_query = '{"action": "stopuse", "uid": "1234", "duration": 123}'
        stop_use_query = EndUseQuery.deserialize(json_stop_use_query)
        self.assertEqual(stop_use_query.uid, "1234")
        self.assertEqual(stop_use_query.duration, 123)
        self.assertEqual(stop_use_query.action, "stopuse")

        json_RegisterMaintenanceQuery = '{"action": "maintenance", "uid": "1234"}'
        register_maintenance_query = RegisterMaintenanceQuery.deserialize(json_RegisterMaintenanceQuery)
        self.assertEqual(register_maintenance_query.uid, "1234")
        self.assertEqual(register_maintenance_query.action, "maintenance")
        self.assertEqual(register_maintenance_query.__class__, RegisterMaintenanceQuery)

        json_alive_query = '{"action": "alive"}'
        alive_query = AliveQuery.deserialize(json_alive_query)
        self.assertEqual(alive_query.action, "alive")
        self.assertEqual(alive_query.__class__, AliveQuery)

    def test_json_serialize(self):
        response = UserResponse(True, True, "user name", 2)
        json_response = response.serialize()
        self.assertEqual(json_response, '{"request_ok": true, "is_valid": true, "name": "user name", "level": 2}')

        response = MachineResponse(True, True, False, True)
        json_response = response.serialize()
        self.assertEqual(
            json_response, '{"request_ok": true, "is_valid": true, "maintenance": false, "allowed": true}'
        )

        response = SimpleResponse(True)
        json_response = response.serialize()
        self.assertEqual(json_response, '{"request_ok": true, "message": ""}')

    def test_init(self):
        d = MQTTInterface(TEST_SETTINGS_PATH)
        self.assertIsNotNone(d)
        d.connect()
        self.assertTrue(d.connected)

    def test_alive(self):
        CARD_UUID = "1234567890"
        NB_TESTS = 10

        db = get_simple_db()
        session = db.getSession()
        mqtt = MQTTInterface(TEST_SETTINGS_PATH)
        mapper = MsgMapper(mqtt, db)
        mapper.registerHandlers()
        mqtt.connect()
        self.assertTrue(mqtt.connected)
        user_repo = db.getUserRepository(session)

        # Create card if not presents
        user = user_repo.getUserByCardUUID(CARD_UUID)
        if user is None:
            user = user_repo.get_all()[0]
            user.card_UUID = CARD_UUID
            user_repo.update(user)

        # Generate all possible messages from the boards on all machines
        for _ in range(NB_TESTS):
            for mac in db.getMachineRepository(session).get_all():
                self.assertTrue(mqtt.publishQuery(mac.machine_id, '{"action": "alive"}'))
                self.assertTrue(mqtt.publishQuery(mac.machine_id, '{"action": "check_machine"}'))
                self.assertTrue(
                    mqtt.publishQuery(mac.machine_id, '{"action": "check_user", "uid": "' + CARD_UUID + '"}')
                )
                self.assertTrue(
                    mqtt.publishQuery(mac.machine_id, '{"action": "startuse", "uid": "' + CARD_UUID + '"}')
                )
                self.assertTrue(
                    mqtt.publishQuery(
                        mac.machine_id, '{"action": "stopuse", "uid": "' + CARD_UUID + '", "duration": 123}'
                    )
                )
                self.assertTrue(
                    mqtt.publishQuery(mac.machine_id, '{"action": "maintenance", "uid": "' + CARD_UUID + '"}')
                )


if __name__ == "__main__":
    unittest.main()
