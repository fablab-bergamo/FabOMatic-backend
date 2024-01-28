from time import time
import unittest
from rfid_backend_FABLAB_BG.database.models import Use

from rfid_backend_FABLAB_BG.mqtt.mqtt_types import (
    UserQuery,
    AliveQuery,
    MachineQuery,
    StartUseQuery,
    EndUseQuery,
    RegisterMaintenanceQuery,
    InUseQuery,
)

from rfid_backend_FABLAB_BG.mqtt.MQTTInterface import MQTTInterface
from rfid_backend_FABLAB_BG.logic.MsgMapper import MsgMapper
from rfid_backend_FABLAB_BG.logic.MachineLogic import MachineLogic
from tests.common import TEST_SETTINGS_PATH, get_simple_db


class TestLogic(unittest.TestCase):
    def test_missed_messages_1(self):
        db = get_simple_db()
        with db.getSession() as session:
            MachineLogic.database = db
            mac = db.getMachineRepository(session).get_all()[0]
            user = db.getUserRepository(session).get_all()[0]
            user.card_UUID = "1234"
            db.getUserRepository(session).update(user)
            ml = MachineLogic(mac.machine_id)

            use_repo = db.getUseRepository(session)

            for use in use_repo.get_all():
                use_repo.delete(use)

            # Call inUse without startUse
            response = ml.inUse("1234", 10)
            self.assertTrue(response.request_ok, "inUse succeeded")

            session.commit()
            # Check a usage has been created with the correct duration
            usage = session.query(Use).filter(Use.machine_id.__eq__(mac.machine_id)).first()
            self.assertIsNotNone(usage, "Usage not created")
            self.assertAlmostEqual(time() - usage.start_timestamp, 10, 0, "Usage duration is not correct")
            self.assertIsNone(usage.end_timestamp, "Usage end timestamp is not None (1)")

            # Call again with another duration
            response = ml.inUse("1234", 20)

            session.commit()
            # Check that no new usage has been created and start time is not updated
            usage = session.query(Use).filter(Use.machine_id.__eq__(mac.machine_id)).first()
            self.assertEqual(len(use_repo.get_all()), 1, "Usage has been duplicated")
            self.assertTrue(response.request_ok, "inUse (2) failed")
            self.assertAlmostEqual(time() - usage.start_timestamp, 10, 0, "Usage duration is not updated")
            self.assertIsNone(usage.end_timestamp, "Usage end timestamp is not None (2)")

            session.commit()

            # Finally close the record
            response = ml.endUse("1234", 30)  # duration will override the previous calculated start
            self.assertTrue(response.request_ok, "endUse failed")

            session.commit()
            usage = session.query(Use).filter(Use.machine_id.__eq__(mac.machine_id)).first()
            self.assertIsNotNone(usage.end_timestamp, f"Usage end timestamp is None : {response}")
            self.assertAlmostEqual(usage.end_timestamp - usage.start_timestamp, 30, 0, "Usage duration is not correct")
            self.assertEqual(len(use_repo.get_all()), 1, "Usage has been duplicated")

    def test_missed_messages_2(self):
        db = get_simple_db()
        with db.getSession() as session:
            MachineLogic.database = db
            mac = db.getMachineRepository(session).get_all()[0]
            user = db.getUserRepository(session).get_all()[0]
            user.card_UUID = "1234"
            db.getUserRepository(session).update(user)
            ml = MachineLogic(mac.machine_id)

            use_repo = db.getUseRepository(session)

            for use in use_repo.get_all():
                use_repo.delete(use)

            session.commit()
            # Call inUse without startUse
            response = ml.inUse("1234", 10)
            self.assertTrue(response.request_ok, "inUse succeeded")

            # Check a usage has been created with the correct duration
            usage = session.query(Use).filter(Use.machine_id.__eq__(mac.machine_id)).first()
            self.assertIsNotNone(usage, "Usage not created")
            self.assertAlmostEqual(time() - usage.start_timestamp, 10, 0, "Usage duration is not correct")
            self.assertIsNone(usage.end_timestamp, "Usage end timestamp is not None (1)")

            # Call again with another duration
            response = ml.startUse("1234")
            self.assertTrue(response.request_ok, "startUse failed")

            session.commit()
            # Check that inuse has been closed with duration 10s
            usage = (
                session.query(Use)
                .filter(Use.machine_id.__eq__(mac.machine_id))
                .order_by(Use.start_timestamp.asc())
                .first()
            )
            self.assertIsNotNone(usage.end_timestamp, f"Usage end timestamp is None : {usage}")
            self.assertAlmostEqual(
                usage.end_timestamp - usage.start_timestamp, 10, 0, f"Usage duration is not correct {usage}"
            )

            # Check that another record has been opened
            usage = (
                session.query(Use)
                .filter(Use.machine_id.__eq__(mac.machine_id))
                .order_by(Use.start_timestamp.desc())
                .first()
            )
            self.assertIsNone(usage.end_timestamp, "Usage end timestamp is not None (2)")

            response = ml.endUse("1234", 1)
            self.assertTrue(response.request_ok, "endUse failed")

            session.commit()
            usage = (
                session.query(Use)
                .filter(Use.machine_id.__eq__(mac.machine_id))
                .order_by(Use.start_timestamp.desc())
                .first()
            )
            self.assertIsNotNone(usage.end_timestamp, f"Usage end timestamp is None : {response}")
            # Check that we have two records
            self.assertEqual(len(use_repo.get_all()), 2, "wrong number of request")

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
            self.assertTrue(response.is_valid, "isAuthorized returns invalid with valid card")

            response = ml.isAuthorized("12345678")
            self.assertTrue(response.request_ok, "isAuthorized must succeed with invalid card")
            self.assertFalse(response.is_valid, "isAuthorized must return invalid with invalid card")

            response = ml.startUse("1234")
            self.assertTrue(response.request_ok, "startUse failed")

            response = ml.inUse("1234", 1)
            self.assertTrue(response.request_ok, "inUse failed")

            response = ml.endUse("1234", 123)
            self.assertTrue(response.request_ok, "endUse failed")

            ml.registerMaintenance("1234")
            self.assertTrue(response.request_ok, "registerMaintenance failed")

    def test_msg_mapper(self):
        db = get_simple_db()

        mqtt = MQTTInterface(TEST_SETTINGS_PATH)
        mqtt.connect()
        mapper = MsgMapper(mqtt, db)
        mapper.registerHandlers()

        # Try all messagges
        query = UserQuery("1234")
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = AliveQuery()
        self.assertFalse(mapper.messageReceived("1", query), "Alive message has no response")
        query = MachineQuery()
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = StartUseQuery("1234")
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = InUseQuery("1234", 123)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = EndUseQuery("1234", 123)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = RegisterMaintenanceQuery("1234")
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")

        # Try all with invalid card
        query = UserQuery("DEADBEEF")
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = StartUseQuery("DEADBEEF")
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = InUseQuery("DEADBEEF", 123)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = EndUseQuery("DEADBEEF", 123)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = RegisterMaintenanceQuery("DEADBEEF")
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
