""" Test the backend module. """

# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import unittest

from FabOMatic.__main__ import Backend
from tests.common import TEST_SETTINGS_PATH


class TestBackend(unittest.TestCase):
    def test_backend(self):
        backend = Backend(TEST_SETTINGS_PATH)
        self.assertTrue(backend.connect(), "Failed to connect the first time")
        backend.disconnect()
        self.assertTrue(backend.connect(), "Failed to connect the second time")
        backend.publishStats()
