""" Configuration TOML functions
"""

import os
import toml
from pathlib import Path
import logging
import shutil

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(MODULE_DIR, "conf", "settings.toml")
EXAMPLE_CONFIG_FILE = os.path.join(MODULE_DIR, "conf", "settings.example.toml")
TEST_SETTINGS_PATH = os.path.join(MODULE_DIR, "..", "..", "tests", "test_settings.toml")

useTestSettings = False
firstRun = True


def checkConfigFile() -> bool:
    if useTestSettings:
        test_file = Path(TEST_SETTINGS_PATH)
        if not test_file.exists:
            logging.error("Missing TEST CONF FILE (%s)- try reinstalling", TEST_SETTINGS_PATH)
            return False

    conf_file = Path(CONFIG_FILE)

    if conf_file.exists():
        return True

    # Auto-create on first run
    example_conf_file = Path(EXAMPLE_CONFIG_FILE)
    if not example_conf_file.exists:
        logging.error("Missing EXAMPLE CONF FILE (%s)- try reinstalling", EXAMPLE_CONFIG_FILE)
        return False
    shutil.copy(EXAMPLE_CONFIG_FILE, CONFIG_FILE)
    logging.warning("Created default CONFIG_FILE (%s)", CONFIG_FILE)
    return True


def loadSettings() -> dict:
    global firstRun, useTestSettings
    checkConfigFile()
    if firstRun:
        firstRun = False
        if useTestSettings:
            logging.info("Using TESTS setting file %s", TEST_SETTINGS_PATH)
        else:
            logging.info("Using setting file %s", CONFIG_FILE)

    if useTestSettings:
        return toml.load(TEST_SETTINGS_PATH)
    return toml.load(CONFIG_FILE)


def loadSubSettings(section: str) -> dict:
    conf = loadSettings()
    return conf[section]


def getSetting(section: str, setting: str) -> str:
    """Return setting from settings.toml.

    Args:
        setting (str): Setting to return
        section (str): Section of setting
        settings_path (str, optional): Path to settings.toml. Defaults to CONFIG_FILE.
    """
    settings = loadSettings()
    return settings[section][setting]


def getDatabaseUrl() -> str:
    # Get the database URL
    db_url = getSetting("database", "url")

    # Check if it's a SQLite URL
    if db_url.startswith("sqlite:///"):
        # Remove the prefix to get the file path
        file_path = db_url[len("sqlite:///") :]

        # Get the absolute path
        absolute_path = os.path.abspath(file_path)

        # Add the prefix back to get the absolute URL
        absolute_url = "sqlite:///" + absolute_path
    else:
        # If it's not a SQLite URL, just use it as is
        absolute_url = db_url
    return absolute_url
