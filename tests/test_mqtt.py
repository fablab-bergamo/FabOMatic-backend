import os
import unittest

from src.rfid_backend_FABLAB_BG.mqtt import MQTTInterface

FIXTURE_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_SETTINGS_PATH = os.path.join(FIXTURE_DIR, "test_settings.toml")

class TestMQTT(unittest.TestCase):
    SETTINGS_PATH = os.path.join(FIXTURE_DIR, TEST_SETTINGS_PATH)

    def test_init(self):
        d = MQTTInterface(self.SETTINGS_PATH)
        self.assertIsNotNone(d)
        return d


if __name__ == "__main__":
    unittest.main()
