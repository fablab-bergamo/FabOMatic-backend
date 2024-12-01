""" Test with more data. """

# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import unittest

from FabOMatic.__main__ import Backend
from tests.common import add_test_data, get_simple_db


class TestData(unittest.TestCase):
    def test_data(self):
        db = get_simple_db()
        add_test_data(db, 2000)
