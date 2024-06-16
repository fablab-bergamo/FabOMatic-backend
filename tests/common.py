""" This module contains common functions used in the tests. """

import logging
import os
from logging.handlers import RotatingFileHandler
import random
from time import time

from sqlalchemy import text

from FabOMatic.database.DatabaseBackend import DatabaseBackend, getSetting
from FabOMatic.database.models import Machine, MachineType, Maintenance, Role, Use, User, Intervention

FIXTURE_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_SETTINGS_PATH = os.path.join(FIXTURE_DIR, "test_settings.toml")


def configure_logger():
    """
    Configures a logger object with a rotating file handler.

    The logger is named "test_logger" and is set to log messages at the DEBUG level.
    The logs are formatted with the timestamp, log level, and message.
    The logs are written to a file named "test-log.txt" in the same directory as this script.
    The file handler rotates the log file when it reaches a maximum size of 1 MB, keeping 1 backup file.
    The file is encoded using the "latin-1" encoding.

    Returns:
        None
    """
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    log_file = os.path.join(os.path.dirname(__file__), "test-log.txt")
    file_handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=1, encoding="latin-1")
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)


def get_empty_test_db() -> DatabaseBackend:
    """
    Returns an instance of DatabaseBackend with an empty database.

    Returns:
        DatabaseBackend: An instance of DatabaseBackend with an empty database.
    """
    d = DatabaseBackend(TEST_SETTINGS_PATH)
    d.deleteExistingDatabase()
    d.createAndUpdateDatabase()
    d.dropContents()
    return d


def seed_test_db() -> DatabaseBackend:
    """
    Seeds the database with initial data for testing purposes.

    Returns:
        DatabaseBackend: The seeded database instance.
    """
    empty_db = DatabaseBackend(TEST_SETTINGS_PATH)
    empty_db.deleteExistingDatabase()
    empty_db.createAndUpdateDatabase()
    empty_db.dropContents()

    with empty_db.getSession() as session:
        mt1 = MachineType(type_id=1, type_name="Default type")
        empty_db.getMachineTypeRepository(session).create(mt1)

        r1 = Role(role_name="admins", authorize_all=True, reserved=True, maintenance=True, backend_admin=True)
        empty_db.getRoleRepository(session).create(r1)

        r3 = Role(role_name="Fab Staff", authorize_all=False, reserved=False, maintenance=True, backend_admin=False)
        empty_db.getRoleRepository(session).create(r3)

        r2 = Role(role_name="Fab Users", authorize_all=False, reserved=False, maintenance=False, backend_admin=False)
        empty_db.getRoleRepository(session).create(r2)

        u1 = User(
            name="admin",
            surname="admin",
            role_id=r1.role_id,
            card_UUID="12345678",
            email=getSetting("web", "default_admin_email"),
        )

        u1.set_password(User.DEFAULT_ADMIN_PASSWORD)

        empty_db.getUserRepository(session).create(u1)

        m1 = Machine(machine_name="Sample machine", machine_type_id=mt1.type_id)
        empty_db.getMachineRepository(session).create(m1)

        maint1 = Maintenance(
            hours_between=10,
            description="sample maintenance - clean machine",
            machine_id=m1.machine_id,
            lcd_message="allineare",
            instructions_url="https://www.fablabbergamo.it/",
        )
        empty_db.getMaintenanceRepository(session).create(maint1)

    return empty_db


def add_test_data(db: DatabaseBackend, nb_records: int) -> DatabaseBackend:
    with db.getSession() as session:
        use_repo = db.getUseRepository(session)
        inter_repo = db.getInterventionRepository(session)
        # generate 100 more users
        users = []
        for i in range(100, 201):
            temp_user = User(
                name="User" + str(i),
                surname="Surname" + str(i),
                role_id=2,
                card_UUID=(str(i * 100) * 8)[:8],
                disabled=random.choice([True, False]),
            )
            temp_user.set_password("")
            temp_user.email = f"user{str(i)*2}@fablab.org"
            users.append(temp_user)
        db.getUserRepository(session).bulk_create(users)
        session.commit()

        for m in db.getMachineRepository(session).get_all():
            uses = []
            for i in range(1, nb_records):
                start = time() - 100000 * i
                end = start + random.randint(1, 100000)

                use = Use(
                    user_id=random.choice(range(1, 10)),
                    machine_id=m.machine_id,
                    start_timestamp=start,
                    end_timestamp=end,
                    last_seen=end,
                )
                uses.append(use)
            use_repo.bulk_create(uses)

            for mt in m.maintenances:
                interventions = []
                for i in range(1, nb_records // 5):
                    inter = Intervention(
                        maintenance_id=mt.maintenance_id,
                        user_id=random.choice(range(1, 10)),
                        machine_id=m.machine_id,
                        timestamp=time() - 100000 * i,
                    )
                    inter_repo.create(inter)
                inter_repo.bulk_create(interventions)
        session.commit()
    # Make a copy in current folder to ease testing with UI/archival into tests/databases
    db.copy("test-full.sqldb")
    return db


def get_simple_db() -> DatabaseBackend:
    """
    Creates a simple database with predefined data for testing purposes.

    Returns:
        DatabaseBackend: An instance of the created database.
    """
    empty_db = DatabaseBackend(TEST_SETTINGS_PATH)
    empty_db.deleteExistingDatabase()
    empty_db.createAndUpdateDatabase()
    empty_db.dropContents()

    with empty_db.getSession() as session:
        mt1 = MachineType(type_id=1, type_name="LASER")
        empty_db.getMachineTypeRepository(session).create(mt1)

        mt2 = MachineType(type_id=2, type_name="3D PRINTER")
        empty_db.getMachineTypeRepository(session).create(mt2)

        mt3 = MachineType(type_id=3, type_name="DRILL")
        empty_db.getMachineTypeRepository(session).create(mt3)

        r1 = Role(role_name="admin", authorize_all=True, reserved=True, maintenance=True)
        empty_db.getRoleRepository(session).create(r1)

        r3 = Role(role_name="staff", authorize_all=False, reserved=False, maintenance=True)
        empty_db.getRoleRepository(session).create(r3)

        r2 = Role(role_name="fab users", authorize_all=False, reserved=False, maintenance=False)
        empty_db.getRoleRepository(session).create(r2)

        u1 = User(name="Mario", surname="Rossi", role_id=r1.role_id, email="marco.rossi@fablab.org", card_UUID="1234")
        u1.set_password("password1")
        empty_db.getUserRepository(session).create(u1)

        u2 = User(
            name="Andrea", surname="Bianchi", role_id=r2.role_id, email="andrea.bianchi@fablab.org", card_UUID="5678"
        )
        u2.set_password("password2")
        empty_db.getUserRepository(session).create(u2)

        for i in range(1, 10):
            temp_user = User(
                name="User" + str(i),
                surname="Surname" + str(i),
                role_id=r2.role_id,
                card_UUID=(str(i) * 8)[:8],
                disabled=random.choice([True, False]),
            )
            temp_user.set_password("")
            temp_user.email = f"{temp_user.name}.{temp_user.surname}@fablab.org"
            empty_db.getUserRepository(session).create(temp_user)

        m1 = Machine(machine_name="LASER 1", machine_type_id=mt1.type_id)
        empty_db.getMachineRepository(session).create(m1)

        m2 = Machine(machine_name="PRINTER 1", machine_type_id=mt2.type_id)
        empty_db.getMachineRepository(session).create(m2)

        temp_machines = []
        for i in range(1, 10):
            temp_machine = Machine(machine_name="Machine" + str(i), machine_type_id=mt3.type_id)
            temp_machines.append(temp_machine)
            empty_db.getMachineRepository(session).create(temp_machine)

        maint1 = Maintenance(
            hours_between=10,
            description="replace engine",
            machine_id=m1.machine_id,
            lcd_message="sostituire motore",
            instructions_url="https://www.fablabbergamo.it/",
        )
        empty_db.getMaintenanceRepository(session).create(maint1)

        maint2 = Maintenance(
            hours_between=10,
            description="replace brushes",
            machine_id=m2.machine_id,
            lcd_message="pulire lente",
            instructions_url="https://www.fablabbergamo.it/",
        )
        empty_db.getMaintenanceRepository(session).create(maint2)

        for i in range(1, 10):
            temp_maint = Maintenance(
                hours_between=random.choice(range(1, 30)),
                description="Maintenance" + str(i),
                lcd_message="Message" + str(i),
                instructions_url="https://www.fablabbergamo.it/",
                machine_id=random.choice(temp_machines).machine_id,
            )
            empty_db.getMaintenanceRepository(session).create(temp_maint)

        timestamp = time() - 1000
        inter = Intervention(
            maintenance_id=maint1.maintenance_id, user_id=u1.user_id, machine_id=m1.machine_id, timestamp=timestamp
        )
        empty_db.getInterventionRepository(session).create(inter)

        inter2 = Intervention(
            maintenance_id=maint2.maintenance_id, user_id=u2.user_id, machine_id=m2.machine_id, timestamp=timestamp
        )
        empty_db.getInterventionRepository(session).create(inter2)

        session.commit()
    # Make a copy in current folder to ease testing with UI/archival into tests/databases
    empty_db.copy("test-simple.sqldb")
    return empty_db
