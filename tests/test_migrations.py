""" Test the database backend. """

# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import unittest
import os

# Import Module
import shutil

from FabOMatic.database.DatabaseBackend import DatabaseBackend, getDatabaseUrl
from tests.common import TEST_SETTINGS_PATH, get_empty_test_db, configure_logger


class TestMigrations(unittest.TestCase):
    def test_migrations(self):
        src_dir = os.path.join(os.path.dirname(__file__), "databases")
        for file in os.listdir(src_dir):
            source = os.path.abspath(os.path.join(src_dir, file))
            dest = getDatabaseUrl(TEST_SETTINGS_PATH)
            if dest.startswith("sqlite:///"):
                # Remove the prefix to get the file path
                dest = dest[len("sqlite:///") :]

            self.assertTrue(os.path.exists(source))
            # Overwrite any existing database with the previous version
            shutil.copyfile(source, dest)

            # Now check that the upgrade works
            self.performUpgrade(file)

    def performUpgrade(self, file: str):
        backend = DatabaseBackend(TEST_SETTINGS_PATH)
        print("Testing upgrade for file : ", file)
        try:
            backend.createAndUpdateDatabase()
            with backend.getSession() as session:
                user_repo = backend.getUserRepository(session)
                self.assertGreaterEqual(len(user_repo.get_all()), 1)
                role_repo = backend.getRoleRepository(session)
                self.assertGreaterEqual(len(role_repo.get_all()), 3)
                machine_repo = backend.getMachineRepository(session)
                self.assertGreaterEqual(len(machine_repo.get_all()), 1)
                type_repo = backend.getMachineTypeRepository(session)
                self.assertGreaterEqual(len(type_repo.get_all()), 1)
                maint_repo = backend.getMaintenanceRepository(session)
                self.assertGreaterEqual(len(maint_repo.get_all()), 0)
                inter_repo = backend.getInterventionRepository(session)
                self.assertGreaterEqual(len(inter_repo.get_all()), 0)

        except Exception as e:
            self.fail(f"Failed to upgrade the database {file} : {e}")
