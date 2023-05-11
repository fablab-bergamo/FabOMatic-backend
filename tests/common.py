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
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.DEBUG)

    # Create a formatter for the logs
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Create a rotating file handler with a maximum size of 1 MB
    log_file = os.path.join(os.path.dirname(__file__), 'test-log.txt')
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1000000, backupCount=1, encoding='latin-1')
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger object
    logger.addHandler(file_handler)


def get_empty_db() -> DatabaseBackend:
    d = DatabaseBackend(TEST_SETTINGS_PATH)
    d.createDatabase()
    d.dropContents()
    return d


def get_simple_db() -> DatabaseBackend:
    empty_db = DatabaseBackend(TEST_SETTINGS_PATH)
    empty_db.createDatabase()
    empty_db.dropContents()

    with empty_db.getSession() as session:

        mt1 = MachineType(type_id=1, type_name="type 0")
        empty_db.getMachineTypeRepository(session).create(mt1)

        mt2 = MachineType(type_id=2, type_name="type 1")
        empty_db.getMachineTypeRepository(session).create(mt2)

        r1 = Role(role_name="admin", authorize_all=True)
        empty_db.getRoleRepository(session).create(r1)

        r2 = Role(role_name="user")
        empty_db.getRoleRepository(session).create(r2)

        u1 = User(name="Mario", surname="Rossi", role_id=r1.role_id)
        empty_db.getUserRepository(session).create(u1)

        u2 = User(name="Andrea", surname="Bianchi", role_id=r2.role_id)
        empty_db.getUserRepository(session).create(u2)

        m1 = Machine(machine_name="DRILL0", machine_type_id=mt1.type_id)
        empty_db.getMachineRepository(session).create(m1)

        m2 = Machine(machine_name="DRILL1",
                     machine_type_id=mt2.type_id)
        empty_db.getMachineRepository(session).create(m2)

        maint1 = Maintenance(hours_between=10,
                             description="replace engine",
                             machine_id=m1.machine_id)

        empty_db.getMaintenanceRepository(session).create(maint1)

        maint2 = Maintenance(hours_between=10,
                             description="replace brushes",
                             machine_id=m2.machine_id)
        empty_db.getMaintenanceRepository(session).create(maint2)

        timestamp = time() - 1000
        inter = Intervention(maintenance_id=maint1.maintenance_id,
                             user_id=u1.user_id,
                             machine_id=m1.machine_id,
                             timestamp=timestamp)
        empty_db.getInterventionRepository(session).create(inter)

        inter2 = Intervention(maintenance_id=maint2.maintenance_id,
                              user_id=u2.user_id,
                              machine_id=m2.machine_id,
                              timestamp=timestamp)
        empty_db.getInterventionRepository(session).create(inter2)

    return empty_db
