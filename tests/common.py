import logging
import os
from logging.handlers import RotatingFileHandler
from time import time

from rfid_backend_FABLAB_BG.database.DatabaseBackend import DatabaseBackend
from rfid_backend_FABLAB_BG.database.models import *

FIXTURE_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_SETTINGS_PATH = os.path.join(FIXTURE_DIR, "test_settings.toml")


def configure_logger():
    # Create a logger object
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    # Create a formatter for the logs
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Create a rotating file handler with a maximum size of 1 MB
    log_file = os.path.join(os.path.dirname(__file__), "test-log.txt")
    file_handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=1, encoding="latin-1")
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger object
    logger.addHandler(file_handler)


def get_empty_db() -> DatabaseBackend:
    d = DatabaseBackend(TEST_SETTINGS_PATH)
    d.createDatabase()
    d.dropContents()
    return d


def seed_db() -> DatabaseBackend:
    empty_db = DatabaseBackend(TEST_SETTINGS_PATH)
    empty_db.createDatabase()
    empty_db.dropContents()

    with empty_db.getSession() as session:
        mt1 = MachineType(type_id=1, type_name="Default type")
        empty_db.getMachineTypeRepository(session).create(mt1)

        r1 = Role(role_name="admins", authorize_all=True, reserved=True, maintenance=True)
        empty_db.getRoleRepository(session).create(r1)

        r3 = Role(role_name="Fab Staff", authorize_all=False, reserved=False, maintenance=True)
        empty_db.getRoleRepository(session).create(r3)

        r2 = Role(role_name="Fab Users", authorize_all=False, reserved=False, maintenance=False)
        empty_db.getRoleRepository(session).create(r2)

        u1 = User(name="admin", surname="admin", role_id=r1.role_id, card_UUID="12345678")
        empty_db.getUserRepository(session).create(u1)

        m1 = Machine(machine_name="Sample machine", machine_type_id=mt1.type_id)
        empty_db.getMachineRepository(session).create(m1)

        maint1 = Maintenance(
            hours_between=10, description="sample maintenance - clean machine", machine_id=m1.machine_id
        )
        empty_db.getMaintenanceRepository(session).create(maint1)

    return empty_db


def get_simple_db() -> DatabaseBackend:
    empty_db = DatabaseBackend(TEST_SETTINGS_PATH)
    empty_db.createDatabase()
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

        u1 = User(name="Mario", surname="Rossi", role_id=r1.role_id)
        empty_db.getUserRepository(session).create(u1)

        u2 = User(name="Andrea", surname="Bianchi", role_id=r2.role_id)
        empty_db.getUserRepository(session).create(u2)

        m1 = Machine(machine_name="LASER 1", machine_type_id=mt1.type_id)
        empty_db.getMachineRepository(session).create(m1)

        m2 = Machine(machine_name="PRINTER 1", machine_type_id=mt2.type_id)
        empty_db.getMachineRepository(session).create(m2)

        maint1 = Maintenance(hours_between=10, description="replace engine", machine_id=m1.machine_id)

        empty_db.getMaintenanceRepository(session).create(maint1)

        maint2 = Maintenance(hours_between=10, description="replace brushes", machine_id=m2.machine_id)
        empty_db.getMaintenanceRepository(session).create(maint2)

        timestamp = time() - 1000
        inter = Intervention(
            maintenance_id=maint1.maintenance_id, user_id=u1.user_id, machine_id=m1.machine_id, timestamp=timestamp
        )
        empty_db.getInterventionRepository(session).create(inter)

        inter2 = Intervention(
            maintenance_id=maint2.maintenance_id, user_id=u2.user_id, machine_id=m2.machine_id, timestamp=timestamp
        )
        empty_db.getInterventionRepository(session).create(inter2)

    return empty_db
