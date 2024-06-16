from time import time
import unittest
from FabOMatic.database.models import Authorization, MachineType, Use

from FabOMatic.mqtt.mqtt_types import (
    UserQuery,
    AliveQuery,
    MachineQuery,
    StartUseQuery,
    EndUseQuery,
    RegisterMaintenanceQuery,
    InUseQuery,
)

from FabOMatic.mqtt.MQTTInterface import MQTTInterface
from FabOMatic.logic.MsgMapper import MsgMapper
from FabOMatic.logic.MachineLogic import MachineLogic
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
            response = ml.endUse("1234", 30, True)  # duration will override the previous calculated start
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

            user = db.getUserRepository(session).get_all()[0]
            user.card_UUID = "1234"
            db.getUserRepository(session).update(user)

            use_repo = db.getUseRepository(session)

            for mac_id in range(1, 4):
                mac = db.getMachineRepository(session).get_by_id(mac_id)
                ml = MachineLogic(mac.machine_id)

                for use in use_repo.get_all():
                    use_repo.delete(use)

                session.commit()

                for d in range(10):
                    # Call inUse without startUse
                    response = ml.inUse("1234", 10 + d)
                    self.assertTrue(response.request_ok, "inUse succeeded")

                    # Check a usage has been created with the correct duration
                    usage = session.query(Use).filter(Use.machine_id == mac.machine_id).first()
                    self.assertIsNotNone(usage, "Usage not created")
                    self.assertAlmostEqual(time() - usage.start_timestamp, 10, 0, "Usage duration is not correct")
                    self.assertIsNone(usage.end_timestamp, "Usage end timestamp is not None (1)")

                    # Check for duplicated records
                    self.assertEqual(len(use_repo.get_all()), 1, "Usage has been duplicated")

                # Call again with another duration
                response = ml.startUse("1234", False)
                self.assertTrue(response.request_ok, "startUse failed")

                session.commit()
                # Check that inuse has been closed with duration 10s
                usage = (
                    session.query(Use)
                    .filter(Use.machine_id == mac.machine_id)
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
                    .filter(Use.machine_id == mac.machine_id)
                    .order_by(Use.start_timestamp.desc())
                    .first()
                )
                self.assertIsNone(usage.end_timestamp, "Usage end timestamp is not None (2)")

                response = ml.endUse("1234", 1, False)
                self.assertTrue(response.request_ok, "endUse failed")

                session.commit()
                usage = (
                    session.query(Use)
                    .filter(Use.machine_id == mac.machine_id)
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

            query = AliveQuery("0.1.32", "127.0.0.1", "SN0", 1000)
            ml.machineAlive(query)

            response = ml.isAuthorized("1234")
            self.assertTrue(response.request_ok, "isAuthorized failed")
            self.assertTrue(response.is_valid, "isAuthorized returns invalid with valid card")

            response = ml.isAuthorized("12345678")
            self.assertTrue(response.request_ok, "isAuthorized must succeed with invalid card")
            self.assertFalse(response.is_valid, "isAuthorized must return invalid with invalid card")

            response = ml.startUse("1234", True)
            self.assertTrue(response.request_ok, "startUse failed")

            response = ml.inUse("1234", 1)
            self.assertTrue(response.request_ok, "inUse failed")

            response = ml.endUse("1234", 123, True)
            self.assertTrue(response.request_ok, "endUse failed")

            ml.registerMaintenance("1234", False)
            self.assertTrue(response.request_ok, "registerMaintenance failed")

            ml.registerMaintenance("1234", True)
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
        query = AliveQuery("0.1.32", "127.0.0.1", "SN0", 1000)
        self.assertFalse(mapper.messageReceived("1", query), "Alive message has no response")
        query = MachineQuery()
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = StartUseQuery("1234", False)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = InUseQuery("1234", 123)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = EndUseQuery("1234", 123, False)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = RegisterMaintenanceQuery("1234", False)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")

        # Try all with invalid card
        query = UserQuery("DEADBEEF")
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = StartUseQuery("DEADBEEF", False)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = InUseQuery("DEADBEEF", 123)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = EndUseQuery("DEADBEEF", 123, False)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")
        query = RegisterMaintenanceQuery("DEADBEEF", True)
        self.assertTrue(mapper.messageReceived("1", query), "Message not processed")

    def test_machine_auth(self):
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

            mac.blocked = False
            db.getMachineRepository(session).update(mac)

            mac.machine_type.access_management = MachineType.MANAGEMENT_WITH_AUTHORIZATION
            db.getMachineTypeRepository(session).update(mac.machine_type)

            # Test success
            response = ml.isAuthorized("1234")
            self.assertTrue(response.request_ok, "isAuthorized failed")
            self.assertTrue(response.is_valid, "isAuthorized returns invalid with authorized user")

            try:
                authorization = (
                    session.query(Authorization).filter_by(user_id=user.user_id, machine_id=mac.machine_id).one()
                )
                session.delete(authorization)
                session.commit()
            except:
                pass

            user.role.authorize_all = False
            db.getRoleRepository(session).update(user.role)

            # Test failure
            response = ml.isAuthorized("1234")
            self.assertTrue(response.request_ok, "isAuthorized failed")
            self.assertFalse(response.is_valid, "isAuthorized returns true without authorization by machine type")

            # Authorize all
            mac.machine_type.access_management = MachineType.MANAGEMENT_WITHOUT_AUTHORIZATION
            db.getMachineTypeRepository(session).update(mac.machine_type)

            # Test success without authorization
            response = ml.isAuthorized("1234")
            self.assertTrue(response.request_ok, "isAuthorized failed")
            self.assertTrue(
                response.is_valid, "isAuthorized returns invalid while machine type has no authorization required"
            )
