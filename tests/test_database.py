""" Test the database backend. """

# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import random
import unittest
from random import randint
from string import ascii_uppercase
from time import time

from sqlalchemy.exc import IntegrityError

from FabOMatic.database.DatabaseBackend import DatabaseBackend
from FabOMatic.database.models import (
    Role,
    MachineType,
    User,
    Machine,
    Maintenance,
    Authorization,
    Use,
    Intervention,
)
from tests.common import TEST_SETTINGS_PATH, get_empty_test_db, get_simple_db, configure_logger


def random_string(length=16):
    """Generate a random string of fixed length"""
    return "".join(random.choice(ascii_uppercase) for i in range(length))


def random_between(a, b):
    return random.randint(a, b - 1)


class TestDB(unittest.TestCase):
    def test_connection(self):
        _ = DatabaseBackend(TEST_SETTINGS_PATH)

    def test_drop(self):
        empty_db = get_empty_test_db()
        with empty_db.getSession() as session:
            self.assertEqual(len(empty_db.getMachineRepository(session).get_all()), 0)
            self.assertEqual(len(empty_db.getMachineTypeRepository(session).get_all()), 0)
            self.assertEqual(len(empty_db.getMachineRepository(session).get_all()), 0)
            self.assertEqual(len(empty_db.getUserRepository(session).get_all()), 0)
            self.assertEqual(len(empty_db.getRoleRepository(session).get_all()), 0)
            self.assertEqual(len(empty_db.getMaintenanceRepository(session).get_all()), 0)
            self.assertEqual(len(empty_db.getInterventionRepository(session).get_all()), 0)

    def test_simple_add_roles(self):
        empty_db = get_empty_test_db()
        role_names = ["user", "power user", "moderator", "crew", "admin", "super admin"]

        with empty_db.getSession() as session:
            role_repo = empty_db.getRoleRepository(session)
            for i, r in enumerate(role_names):
                role_repo.create(
                    Role(
                        role_id=i, role_name=r, reserved=True, authorize_all=True, maintenance=True, backend_admin=True
                    )
                )

            # check if roles were added
            self.assertEqual(len(role_names), len(role_repo.get_all()))

            # check if role parameters are real
            for i, r in enumerate(role_repo.get_all()):
                self.assertEqual(r.role_id, i)
                self.assertEqual(r.role_name, role_names[i])
                self.assertTrue(r.reserved)
                self.assertTrue(r.maintenance)
                self.assertTrue(r.authorize_all)
                self.assertTrue(r.backend_admin)

            # edit a role name
            new_name = "TEST ROLE WOW"
            role = role_repo.get_by_id(0)
            role.role_name = new_name
            role.maintenance = False
            role_repo.update(role)
            self.assertEqual(role_repo.get_by_id(0).role_name, new_name)
            self.assertFalse(role_repo.get_by_id(0).maintenance)
            self.assertEqual(len(role_repo.get_all()), len(role_names))

            # create a new role
            new_role = "ÜBER ADMIN"
            role_repo.create(Role(role_name=new_role, backend_admin=True))
            self.assertEqual(len(role_repo.get_all()), len(role_names) + 1)
            self.assertTrue(role_repo.get_by_role_name(new_role).backend_admin)
            self.assertFalse(role_repo.get_by_role_name(new_role).maintenance)
            self.assertFalse(role_repo.get_by_role_name(new_role).authorize_all)
            self.assertFalse(role_repo.get_by_role_name(new_role).reserved)

            # Check autoincrement
            self.assertEqual(role_repo.get_by_id(len(role_names)).role_name, new_role)

            # remove a role
            role_repo.delete(role_repo.get_by_id(0))
            self.assertEqual(len(role_repo.get_all()), len(role_names))

            # add a new role
            role_repo.create(Role(role_name="ÜBERÜBER ADMIN"))
            self.assertEqual(len(role_repo.get_all()), len(role_names) + 1)

            # add a duplicate role and catch exception
            with self.assertRaises(IntegrityError):
                role_repo.create(Role(role_name="ÜBERÜBER ADMIN", role_id=1))

    def test_types(self):
        empty_db = get_empty_test_db()
        type_names = ["3d printer", "laser cutter", "vertical drill", "saw"]

        with empty_db.getSession() as session:
            type_repo = empty_db.getMachineTypeRepository(session)
            for i, t in enumerate(type_names):
                type_repo.create(MachineType(type_id=i, type_name=t))

            # check if types were added
            self.assertEqual(len(type_repo.get_all()), len(type_names))

            # rename a machine type
            new_name = "TEST TYPE WOW"
            mt0 = type_repo.get_model_by_id(MachineType, 0)
            mt0.type_name = new_name
            type_repo.update(mt0)

            self.assertEqual(type_repo.get_model_by_id(MachineType, 0).type_name, new_name)

            # add a new type
            new_type = "ÜBER TYPE"
            mt_x = MachineType(type_name=new_type)
            type_repo.create(mt_x)

            self.assertEqual(len(type_repo.get_all()), len(type_names) + 1)

            # remove a type
            type_repo.delete(mt_x)
            self.assertEqual(len(type_repo.get_all()), len(type_names))

            # list the types
            for t in type_repo.get_all():
                print(t.serialize())

            # add a duplicate type_name and catch exception
            a = MachineType(type_name="TEST TYPE WOW")
            with self.assertRaises(IntegrityError):
                type_repo.create(a)

            type_repo.rollback()

            a = MachineType(type_name="Unique name", type_id=1)
            with self.assertRaises(IntegrityError):
                type_repo.create(a)
            type_repo.rollback()

    def test_users(self):
        empty_db = get_empty_test_db()
        with empty_db.getSession() as session:
            empty_db.getRoleRepository(session).create(Role(role_id=1, role_name="admin"))

            names = ["Alessandro", "Lorenzo", "Diego", "Tommaso", "Riccardo"]
            surnames = [
                "Rossi",
                "Bianchi",
                "Verdi",
                "Colombo",
                "Fumagalli",
            ]

            # just to make sure
            self.assertEqual(len(names), len(surnames))

            ids = []
            user_repo = empty_db.getUserRepository(session)
            # add roles
            for n, s in zip(names, surnames):
                usr = User(name=n, surname=s, role_id=1)
                user_repo.create(usr)
                self.assertEqual(user_repo.get_by_id(usr.user_id).name, n)
                self.assertEqual(user_repo.get_by_id(usr.user_id).surname, s)
                self.assertEqual(user_repo.get_by_id(usr.user_id).role_id, 1)
                ids.append(user_repo.get_by_id(usr.user_id).user_id)

            # check if user were added
            self.assertEqual(len(user_repo.get_all()), len(names))

            # check that every user is unique
            self.assertEqual(len(ids), len(set(ids)))

            # set a user card
            u = user_repo.get_by_id(ids[0])
            UUID = random_string(8)
            u.card_UUID = UUID
            user_repo.update(u)
            self.assertEqual(user_repo.get_by_id(ids[0]).card_UUID, UUID)

            # add another user
            user_repo.create(User(name="Andrea", surname="Bianchi", role_id=1))

            # test invalid role
            with self.assertRaises(IntegrityError):
                user_repo.create(User(name="Giorgio", surname="Rossi", role_id=10))

            user_repo.rollback()

            self.assertIsNone(user_repo.get_by_id(10))
            self.assertIsNone(user_repo.getUserByCardUUID(random_string(8)))

    def test_roles(self):
        empty_db = get_empty_test_db()
        with empty_db.getSession() as session:
            # add roles
            role_repo = empty_db.getRoleRepository(session)
            role_repo.create(Role(role_id=0, role_name="admin role"))
            role_repo.create(Role(role_id=1, role_name="user role"))

            # check if roles were added
            self.assertEqual(len(role_repo.get_all()), 2)

            # rename a role
            new_name = "ÜBER ADMIN"
            r0 = role_repo.get_by_id(0)
            r0.role_name = new_name
            role_repo.update(r0)
            self.assertEqual(role_repo.get_by_id(0).role_name, new_name)

            # check linked properties
            user_repo = empty_db.getUserRepository(session)
            new_user = User(name="Mario", surname="Rossi", role_id=1)
            user_repo.create(new_user)
            role_1 = role_repo.get_by_id(1)

            # check if the role is linked to the user
            self.assertIsNotNone(role_1)
            self.assertIsNone(role_repo.get_by_id(10))
            self.assertIsNone(role_repo.get_by_role_name("nonexistent role"))

    def test_get_user_authorizations(self):
        simple_db = get_simple_db()
        with simple_db.getSession() as session:
            userRepo = simple_db.getUserRepository(session)
            authRepo = simple_db.getAuthorizationRepository(session)
            machineRepo = simple_db.getMachineRepository(session)
            machineTypeRepo = simple_db.getMachineTypeRepository(session)
            roleRepo = simple_db.getRoleRepository(session)

            # add roles
            role = Role(role_name="normal role", authorize_all=False, maintenance=True)
            roleRepo.create(role)

            # add user with UUID
            card_UUID = random_string(8)
            user = User(name="Mario", surname="Rossi", role_id=role.role_id, card_UUID=card_UUID)
            userRepo.create(user)

            # create two machines with type 0
            machineType = MachineType(type_name="machine type: test")
            machineTypeRepo.create(machineType)

            machine1 = Machine(machine_name="test machine super", machine_type_id=machineType.type_id)
            machineRepo.create(machine1)
            machine2 = Machine(machine_name="test machine better", machine_type_id=machineType.type_id)
            machineRepo.create(machine2)

            # create one machine with type 1
            machineType1 = MachineType(type_name="machine type: another test")
            machineTypeRepo.create(machineType1)
            machine3 = Machine(machine_name="greatest machine", machine_type_id=machineType1.type_id)
            machineRepo.create(machine3)

            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine1, user), "T1 User should not be authorized for machine1"
            )
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine2, user), "T1 User should not be authorized for machine2"
            )
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine3, user), "T1 User should not be authorized for machine3"
            )

            auth = Authorization(user_id=user.user_id, machine_id=machine1.machine_id)
            authRepo.create(auth)
            user.authorizations = [auth]
            userRepo.update(user)
            # Reload user from db just be sure everything is saved
            user = userRepo.get_by_id(user.user_id)

            self.assertTrue(
                userRepo.IsUserAuthorizedForMachine(machine1, user), "T2 User should be authorized for machine1"
            )
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine2, user), "T2 User should not be authorized for machine2"
            )
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine3, user), "T2 User should not be authorized for machine3"
            )

            user = userRepo.getUserByCardUUID(card_UUID)
            self.assertTrue(
                userRepo.IsUserAuthorizedForMachine(machine1, user), "T3 User should be authorized for machine1"
            )
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine2, user), "T3 User should not be authorized for machine2"
            )
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine3, user), "T3 User should not be authorized for machine3"
            )

            # Check disabled is working
            user.disabled = True
            userRepo.update(user)
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine1, user),
                "T3 User should be disabled and not authorized for machine1",
            )
            user.disabled = False
            userRepo.update(user)
            self.assertTrue(
                userRepo.IsUserAuthorizedForMachine(machine1, user), "T3 User should be authorized for machine1"
            )

            # Check deleted is working
            user.deleted = True
            userRepo.update(user)
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine1, user),
                "T3 User should be deleted and not authorized for machine1",
            )
            user.deleted = False
            userRepo.update(user)
            self.assertTrue(
                userRepo.IsUserAuthorizedForMachine(machine1, user), "T3 User should be authorized for machine1"
            )

            # More auth checks
            auth2 = Authorization(user_id=user.user_id, machine_id=machine3.machine_id)
            authRepo.create(auth2)

            self.assertTrue(
                userRepo.IsUserAuthorizedForMachine(machine1, user), "T4 User should be authorized for machine1"
            )
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine2, user), "T4 User should not be authorized for machine2"
            )
            self.assertTrue(
                userRepo.IsUserAuthorizedForMachine(machine3, user), "T4 User should be authorized for machine3"
            )

            authRepo.delete(auth)
            authRepo.delete(auth2)

            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine1, user), "T4 User should not be authorized for machine1"
            )
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine2, user), "T4 User should not be authorized for machine2"
            )
            self.assertFalse(
                userRepo.IsUserAuthorizedForMachine(machine3, user), "T4 User should not be authorized for machine3"
            )

    def test_long_add_users(self):
        db = get_empty_test_db()
        with db.getSession() as session:
            USERS = 100
            name = "Mario"
            surname = "Rossi"

            role = Role(role_name="normal role", authorize_all=False, maintenance=False)
            db.getRoleRepository(session).create(role)
            userRepo = db.getUserRepository(session)

            for _ in range(USERS):
                user = User(name=name, surname=surname, role_id=role.role_id)
                userRepo.create(user)

            self.assertEqual(len(db.getUserRepository(session).get_all()), USERS)

    def test_machines(self):
        empty_db = get_empty_test_db()
        with empty_db.getSession() as session:
            TYPES = 10
            MACHINES = 10
            current_id = 0

            machineRepo = empty_db.getMachineRepository(session)
            mtypeRepo = empty_db.getMachineTypeRepository(session)

            # create machines for each type
            for i in range(1, TYPES + 1):
                NAME = random_string(10)
                mtype = MachineType(
                    type_name=NAME,
                    type_timeout_min=10,
                    grace_period_min=5,
                    access_management=MachineType.MANAGEMENT_WITH_AUTHORIZATION,
                )
                mtypeRepo.create(mtype)
                self.assertEqual(len(mtypeRepo.get_all()), i, "Machine type not added correctly")
                for _ in range(1, MACHINES + 1):
                    name = random_string(6)
                    machine = Machine(machine_name=name, machine_type_id=mtype.type_id)
                    machineRepo.create(machine)

            # test that they have been added
            self.assertEqual(MACHINES * TYPES, len(machineRepo.get_all()), "Machines not added correctly")

            for current_id in range(1, MACHINES * TYPES + 1):
                machine = machineRepo.get_by_id(current_id)
                self.assertIsNotNone(machine, f"Machine {current_id} not found")
                hours = random_between(10, 1000)
                machine.machine_hours = hours
                machineRepo.update(machine)
                # reload machine
                machine = machineRepo.get_by_id(current_id)
                self.assertEqual(machine.machine_hours, hours, "Hours not updated correctly")
                self.assertEqual(machine.machine_type.type_timeout_min, 10, "Machine Type type_timeout_min is wrong")
                self.assertEqual(machine.machine_type.grace_period_min, 5, "Machine Type grace_period_min is wrong")
                self.assertEqual(
                    machine.machine_type.access_management,
                    MachineType.MANAGEMENT_WITH_AUTHORIZATION,
                    "Machine Type timeout is wrong",
                )

            for current_id in range(1, MACHINES * TYPES + 1):
                machine = machineRepo.get_by_id(current_id)
                self.assertIsNotNone(machine, f"Machine {current_id} not found")
                # test rename
                NAME = random_string(10)
                machine.machine_name = NAME
                machineRepo.update(machine)

                self.assertEqual(
                    machineRepo.get_by_id(current_id).machine_name, NAME, "Machine name not updated correctly"
                )
                # test new type

                NEW_TYPE = randint(1, TYPES)
                machine.machine_type_id = NEW_TYPE
                machineRepo.update(machine)

                self.assertEqual(
                    NEW_TYPE, machineRepo.get_by_id(current_id).machine_type_id, "Machine type not updated correctly"
                )

                machineRepo.delete(machine)
                # test delete
                self.assertEqual(MACHINES * TYPES - current_id, len(machineRepo.get_all()), "Machine has been deleted")

            # test delete
            self.assertEqual(0, len(machineRepo.get_all()), "All machines should have been deleted")

    def test_maintenances(self):
        empty_db = get_empty_test_db()
        with empty_db.getSession() as session:
            maint_repo = empty_db.getMaintenanceRepository(session)

            m_type = MachineType(type_name="test type")
            empty_db.getMachineTypeRepository(session).create(m_type)

            machine = Machine(machine_name="test machine", machine_type_id=m_type.type_id)
            empty_db.getMachineRepository(session).create(machine)

            MAINTENANCES = 100

            for x in range(1, MAINTENANCES):
                hours_between = random_between(5, 10)
                description = random_string(50)
                maint = Maintenance(
                    hours_between=hours_between, description=description, machine_id=machine.machine_id
                )
                maint_repo.create(maint)

                # check getters and setters
                maint2 = maint_repo.get_model_by_id(Maintenance, maint.maintenance_id)
                self.assertIsNotNone(maint2, "Maintenance not found")

                self.assertEqual(maint2.hours_between, hours_between, "Hours between not set correctly")
                self.assertEqual(maint2.description, description, "Description not set correctly")

                maint2.hours_between = random_between(5, 10)
                maint2.description = random_string(50)
                maint_repo.update(maint2)

            # check removal
            for x in range(1, MAINTENANCES):
                maint = maint_repo.get_model_by_id(Maintenance, x)
                maint_repo.delete(maint)

            self.assertEqual(len(maint_repo.get_all()), 0, "All maintenances should have been deleted")

    def test_machine_maintenance_interaction(self):
        empty_db = get_empty_test_db()
        MACHINE_TYPE_NAME = "drill"
        MACHINES = 3

        # create simple machine types
        with empty_db.getSession() as session:
            mtr = empty_db.getMachineTypeRepository(session)
            machine_repo = empty_db.getMachineRepository(session)
            maint_repo = empty_db.getMaintenanceRepository(session)

            mt = MachineType(type_name=MACHINE_TYPE_NAME)
            mtr.create(mt)
            self.assertEqual(len(mtr.get_all()), 1, "Machine type not added correctly")

            # create simple machine
            for x in range(MACHINES):
                m = Machine(machine_name=f"TEST{x}", machine_type_id=mt.type_id)
                machine_repo.create(m)

            # create simple maintenances
            MAINTENANCES_DESC = ["change oil", "clean mirror", "empty bin"]
            for mac in machine_repo.get_all():
                for _, md in enumerate(MAINTENANCES_DESC):
                    maint = Maintenance(
                        description=md,
                        hours_between=10,
                        machine_id=mac.machine_id,
                        lcd_message="pulire",
                        instructions_url="https://www.google.com",
                    )
                    maint_repo.create(maint)

            self.assertEqual(
                len(maint_repo.get_all()), MACHINES * len(MAINTENANCES_DESC), "Maintenance not added correctly"
            )

            for m in machine_repo.get_all():
                self.assertEqual(
                    len(m.maintenances), len(MAINTENANCES_DESC), "Machine maintenances not added correctly"
                )
                for maint in m.maintenances:
                    maint_repo.delete(maint)
                m = machine_repo.get_by_id(m.machine_id)
                self.assertEqual(len(m.maintenances), 0, "Machine maintenances not removed correctly")

            self.assertEqual(0, len(maint_repo.get_all()), "All maintenances should have been deleted")

    def test_interventions(self):
        simple_db = get_simple_db()
        with simple_db.getSession() as session:
            int_repo = simple_db.getInterventionRepository(session)
            maint_repo = simple_db.getMaintenanceRepository(session)
            machine_repo = simple_db.getMachineRepository(session)
            user_repo = simple_db.getUserRepository(session)

            user = user_repo.get_by_id(1)
            machine = machine_repo.get_by_id(1)
            maint = maint_repo.get_model_by_id(Maintenance, 1)

            for inter in int_repo.get_all():
                int_repo.delete(inter)

            # create simple intervention
            inter = Intervention(
                maintenance_id=maint.maintenance_id,
                user_id=user.user_id,
                machine_id=machine.machine_id,
                timestamp=time(),
            )
            int_repo.create(inter)

            self.assertAlmostEqual(inter.timestamp, time(), delta=1000)

            self.assertEqual(len(int_repo.get_all()), 1, "Intervention not added correctly")
            self.assertEqual(len(maint.interventions), 1, "Maintenance intervention not added correctly")
            self.assertEqual(len(machine.interventions), 1, "Machine intervention not added correctly")
            self.assertEqual(len(user.interventions), 1, "User intervention not added correctly")

            int_repo.delete(inter)

            self.assertEqual(len(int_repo.get_all()), 0, "Intervention not deleted correctly")
            self.assertEqual(len(maint.interventions), 0, "Maintenance intervention not deleted correctly")
            self.assertEqual(len(machine.interventions), 0, "Machine intervention not deleted correctly")
            self.assertEqual(len(user.interventions), 0, "User intervention not deleted correctly")

    def test_user_use_interaction(self):
        simple_db = get_simple_db()
        with simple_db.getSession() as session:
            use_repo = simple_db.getUseRepository(session)
            user_repo = simple_db.getUserRepository(session)
            machine_repo = simple_db.getMachineRepository(session)

            userID1 = user_repo.get_by_id(1)
            machine = machine_repo.get_by_id(1)

            # create simple use
            self.assertEqual(len(userID1.uses), 0, "No previous user records should exist")
            self.assertTrue(use_repo.startUse(machine.machine_id, user=userID1, timestamp=time(), is_replay=False))
            self.assertEqual(len(userID1.uses), 1, "User start of usage is registered correctly")

            use_repo.endUse(machine_id=machine.machine_id, user=userID1, duration_s=1, is_replay=False)

            self.assertEqual(len(userID1.uses), 1, "User usage has been closed correctly")
            self.assertEqual(len(machine.uses), 1, "Machine use not added correctly")

            use_repo.delete(userID1.uses[0])

            self.assertEqual(len(userID1.uses), 0, "User use not deleted correctly")
            self.assertEqual(len(machine.uses), 0, "Machine use not deleted correctly")

            # invalid cases
            for _ in range(100):
                self.assertTrue(
                    use_repo.startUse(machine_id=machine.machine_id, user=userID1, timestamp=time(), is_replay=False)
                )

            self.assertEqual(
                1, len(session.query(Use).filter(Use.end_timestamp.is_(None)).all()), "Only one open use should exist"
            )
            self.assertEqual(
                99,
                len(session.query(Use).filter(Use.end_timestamp.is_not(None)).all()),
                "Auto-closing orphan uses should have closed 99 uses",
            )

            for _ in range(100):
                use_repo.inUse(machine_id=machine.machine_id, user=userID1, duration_s=1)

            self.assertEqual(
                99,
                len(session.query(Use).filter(Use.end_timestamp.is_not(None)).all()),
                "In use does not duplicate records",
            )

            for _ in range(100):
                use_repo.endUse(machine_id=machine.machine_id, user=userID1, duration_s=1, is_replay=False)

            self.assertEqual(
                199,
                len(session.query(Use).filter(Use.end_timestamp.is_not(None)).all()),
                "Auto-closing orphan uses should have closed 99 uses",
            )
            self.assertEqual(
                0, len(session.query(Use).filter(Use.end_timestamp.is_(None)).all()), "No open uses should exist"
            )

    def test_user_helpers(self):
        simple_db = get_simple_db()
        with simple_db.getSession() as session:
            use_repo = simple_db.getUseRepository(session)
            user_repo = simple_db.getUserRepository(session)
            machine_repo = simple_db.getMachineRepository(session)

            userID1 = user_repo.get_by_id(1)
            machine = machine_repo.get_by_id(1)

            # create simple use
            self.assertTrue(use_repo.startUse(machine.machine_id, user=userID1, timestamp=time(), is_replay=False))
            use_repo.endUse(machine_id=machine.machine_id, user=userID1, duration_s=1, is_replay=False)

            self.assertEqual(len(userID1.uses), 1, "User use not added correctly")
            self.assertEqual(len(machine.uses), 1, "Machine use not added correctly")

            use_repo.delete(userID1.uses[0])

            self.assertEqual(len(userID1.uses), 0, "User use not deleted correctly")
            self.assertEqual(len(machine.uses), 0, "Machine use not deleted correctly")

            # invalid cases
            for _ in range(100):
                self.assertTrue(
                    use_repo.startUse(machine_id=machine.machine_id, user=userID1, timestamp=time(), is_replay=False)
                )
                self.assertTrue(use_repo.inUse(machine_id=machine.machine_id, user=userID1, duration_s=1))

            self.assertEqual(
                1, len(session.query(Use).filter(Use.end_timestamp.is_(None)).all()), "Only one open use should exist"
            )
            self.assertEqual(
                99,
                len(session.query(Use).filter(Use.end_timestamp.is_not(None)).all()),
                "Auto-closing orphan uses should have closed 99 uses",
            )

            for _ in range(100):
                use_repo.endUse(machine_id=machine.machine_id, user=userID1, duration_s=1, is_replay=False)

            self.assertEqual(
                199,
                len(session.query(Use).filter(Use.end_timestamp.is_not(None)).all()),
                "Auto-closing orphan uses should have closed 99 uses",
            )
            self.assertEqual(
                0, len(session.query(Use).filter(Use.end_timestamp.is_(None)).all()), "No open uses should exist"
            )

    def test_use_helpers(self):
        simple_db = get_simple_db()
        with simple_db.getSession() as session:
            mac_repo = simple_db.getMachineRepository(session)
            use_repo = simple_db.getUseRepository(session)
            user_repo = simple_db.getUserRepository(session)

            self.assertEqual(0, len(mac_repo.getCurrentlyUsedMachines()), "No machines should be in use")

            self.assertTrue(
                user_repo.IsUserAuthorizedForMachine(machine=mac_repo.get_by_id(1), user=user_repo.get_by_id(1)),
                "User should be authorized",
            )
            self.assertEqual(0, user_repo.getUserTotalTime(user_id=1), "User should have no total time")
            self.assertEqual(0, mac_repo.getRelativeUseTime(machine_id=1), "Machine should have no relative time")
            self.assertEqual(0, mac_repo.getTotalUseTime(machine_id=1), "Machine should have no total time")

            self.assertFalse(
                mac_repo.getMachineMaintenanceNeeded(machine_id=1)[0], "Machine should not need maintenance"
            )

            self.assertTrue(
                use_repo.startUse(machine_id=1, user=user_repo.get_by_id(1), timestamp=time() - 240, is_replay=False)
            )

            self.assertTrue(mac_repo.isMachineCurrentlyUsed(1), "Machine should be in use")
            self.assertEqual(1, len(mac_repo.getCurrentlyUsedMachines()), "One machine should be in use")

            use_repo.endUse(machine_id=1, user=user_repo.get_by_id(1), duration_s=60, is_replay=False)
            self.assertFalse(mac_repo.isMachineCurrentlyUsed(1), "Machine should not be in use")
            self.assertEqual(0, len(mac_repo.getCurrentlyUsedMachines()), "No machine should be in use")

            self.assertLess(59.0, user_repo.getUserTotalTime(user_id=1), "User should have >59s total time")
            self.assertLess(59.0, mac_repo.getRelativeUseTime(machine_id=1), "Machine should have >59s relative time")
            self.assertLess(59.0, mac_repo.getTotalUseTime(machine_id=1), "Machine should have >59s total time")

            # Register another use
            self.assertTrue(
                use_repo.startUse(machine_id=1, user=user_repo.get_by_id(1), timestamp=time() - 120, is_replay=False)
            )
            use_repo.endUse(machine_id=1, user=user_repo.get_by_id(1), duration_s=60, is_replay=False)

            self.assertFalse(mac_repo.isMachineCurrentlyUsed(1), "Machine should not be in use")
            self.assertEqual(0, len(mac_repo.getCurrentlyUsedMachines()), "No machine should be in use")

            self.assertLess(119.0, user_repo.getUserTotalTime(user_id=1), "User should have >119s total time")
            self.assertLess(
                119.0, mac_repo.getRelativeUseTime(machine_id=1), "Machine should have >119s relative time"
            )
            self.assertLess(119.0, mac_repo.getTotalUseTime(machine_id=1), "Machine should have >119s total time")

            # register an intervention between both uses
            int_repo = simple_db.getInterventionRepository(session)
            int_repo.create(Intervention(user_id=1, machine_id=1, timestamp=time() - 180, maintenance_id=1))

            # relative use shall be only the last use duration
            self.assertLess(59.0, mac_repo.getRelativeUseTime(machine_id=1), "Machine should have >59s relative time")
            # total use shall not be changed
            self.assertLess(119.0, mac_repo.getTotalUseTime(machine_id=1), "Machine should have >119s total time")

            # Check maintenance status
            self.assertFalse(
                mac_repo.getMachineMaintenanceNeeded(machine_id=1)[0], "Machine should not need maintenance"
            )

            maint_repo = simple_db.getMaintenanceRepository(session)
            maint = maint_repo.get_model_by_id(Maintenance, 1)
            maint.hours_between = 1 / 3600  # every second
            maint_repo.update(maint)

            # Check tuple values of getMachineMaintenanceNeeded
            self.assertTrue(mac_repo.getMachineMaintenanceNeeded(machine_id=1)[0], "Machine shall need maintenance")
            self.assertEqual(
                mac_repo.getMachineMaintenanceNeeded(machine_id=1)[1],
                maint.lcd_message,
                "Correct maintenance description shall be returned",
            )

            # Perform maintenance
            inter_repo = simple_db.getInterventionRepository(session)
            inter_repo.registerInterventionsDone(machine_id=1, user_id=1)
            self.assertFalse(
                mac_repo.getMachineMaintenanceNeeded(machine_id=1)[0], "Machine shall not need maintenance anymore"
            )

            # Check user's use history
            self.assertGreater(len(user_repo.getUserUses(user_repo.get_by_id(1))), 0, "User should have use history")

    def test_boards(self):
        simple_db = get_simple_db()
        with simple_db.getSession() as session:
            board_repo = simple_db.getBoardsRepository(session)
            machine_repo = simple_db.getMachineRepository(session)
            for mac in machine_repo.get_all():
                board_repo.registerBoard(f"1.2.3.{mac.machine_id}", "0.1.2", f"SN{mac.machine_id}", 300000, mac)

            # check if boards were added
            self.assertEqual(len(board_repo.get_all()), len(machine_repo.get_all()))

            for mac in machine_repo.get_all():
                board_repo.registerBoard(f"1.3.4.{mac.machine_id}", "0.1.3", f"SN{mac.machine_id}", 300000, mac)

            # check no duplicates were created
            self.assertEqual(len(board_repo.get_all()), len(machine_repo.get_all()))

            # check last_seen is updated
            for board in board_repo.get_all():
                self.assertAlmostEqual(board.last_seen, time(), delta=1000)

    def test_orphans(self):
        simple_db = get_simple_db()
        simple_db.closeOrphans()


if __name__ == "__main__":
    configure_logger()
    unittest.main()
