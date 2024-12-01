""" Test the backend module. """

# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import unittest

from FabOMatic.__main__ import Backend


class TestBackend(unittest.TestCase):
    def test_backend(self):
        backend = Backend()
        self.assertTrue(backend.connect(), "Failed to connect the first time")
        backend.disconnect()
        self.assertTrue(backend.connect(), "Failed to connect the second time")
        backend.publishStats()
