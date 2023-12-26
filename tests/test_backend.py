""" Test the backend module. """
# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import unittest

from rfid_backend_FABLAB_BG.main import Backend


class TestBackend(unittest.TestCase):
    def test_backend(self):
        backend = Backend()
        self.assertTrue(backend.connect(), "Failed to connect")
        backend.disconnect()
        self.assertTrue(backend.connect(), "Failed to connect")
        backend.publishStats()
        backend.createDatabase()
