""" Test the database backend. """

# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import unittest

from FabOMatic.database.DatabaseBackend import DatabaseBackend
from FabOMatic.database.models import User, Role
from tests.common import TEST_SETTINGS_PATH, get_empty_test_db, configure_logger


class TestAuth(unittest.TestCase):
    def test_connection(self):
        _ = DatabaseBackend(TEST_SETTINGS_PATH)

    def test_user_auth(self):
        empty_db = get_empty_test_db()
        with empty_db.getSession() as session:
            empty_db.getRoleRepository(session).create(Role(role_id=1, role_name="admin"))

            test_users = [
                ("Alessandro", "Rossi", "pass1"),
                ("Lorenzo", "Bianchi", "pass2"),
                ("Diego", "Verdi", "pass3"),
                ("Tommaso", "Colombo", "pass4"),
                ("Riccardo", "Fumagalli", "pass5"),
            ]

            user_repo = empty_db.getUserRepository(session)
            # add roles
            for n, s, p in test_users:
                usr = User(name=n, surname=s, role_id=1)
                usr.set_password(p)
                usr.email = f"{n}.{s}@fablabbg.org"

                user_repo.create(usr)
                reloaded = user_repo.get_by_id(usr.user_id)
                self.assertEqual(reloaded.name, n)
                self.assertEqual(reloaded.surname, s)
                self.assertEqual(reloaded.role_id, 1)
                self.assertTrue(reloaded.check_password(p), "Password not set correctly")
                self.assertFalse(reloaded.check_password("wrong_password"), "Password not verified correctly")
                self.assertEqual(reloaded.email, usr.email)
                self.assertGreater(len(reloaded.serialize()), 0)

                # Token verification

                key = b"192b9b237822dd23"
                wrong_key = b"192b9b237822dd24"
                salt = b"fablab-bg"

                token = reloaded.get_reset_token(key, salt)
                self.assertEqual(
                    reloaded.user_id,
                    User.verify_reset_token(token, key, salt, 1),
                    f"Token not verified correctly for user {reloaded}",
                )
                self.assertIsNone(
                    User.verify_reset_token(token, wrong_key, salt, 1),
                    f"Token not verified correctly for user {reloaded}",
                )
                self.assertIsNone(
                    User.verify_reset_token(token, wrong_key, salt, -1),
                    f"Token expiration not verified correctly for user {reloaded}",
                )

                token = "PROVA"
                self.assertIsNone(User.verify_reset_token(token, key, salt), "Token not verified correctly")


if __name__ == "__main__":
    configure_logger()
    unittest.main()
