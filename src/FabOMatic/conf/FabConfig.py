""" Configuration TOML functions
"""

import os
import toml
from pathlib import Path
import logging
import shutil

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_CONFIG_FILE = os.path.join(MODULE_DIR, "conf", "settings.toml")
EXAMPLE_CONFIG_FILE = os.path.join(MODULE_DIR, "conf", "settings.example.toml")
TEST_SETTINGS_PATH = os.path.join(MODULE_DIR, "..", "..", "tests", "test_settings.toml")

useTestSettings = False
firstRun = True
_active_config_file = None  # Cache for the active config file path


def getConfigSearchPaths() -> list:
    """Return list of config file paths in priority order.

    Returns:
        list: List of paths to search for settings.toml, first found wins
    """
    paths = []

    # User-specific config directory (XDG-compliant)
    user_config = os.path.join(os.path.expanduser("~"), ".config", "FabOMatic", "settings.toml")
    paths.append(user_config)

    # System-wide config (requires root)
    if os.name != "nt":  # Not Windows
        paths.append("/etc/FabOMatic/settings.toml")

    # Alternative user location
    paths.append(os.path.join(os.path.expanduser("~"), "FabOMatic", "settings.toml"))

    # Original package location (backward compatibility)
    paths.append(PACKAGE_CONFIG_FILE)

    return paths


def getConfigFilePath() -> str:
    """Find and return the path to the active config file.

    Returns:
        str: Path to the first existing config file, or None if none exist
    """
    global _active_config_file

    # Return cached path if available
    if _active_config_file and os.path.exists(_active_config_file):
        return _active_config_file

    # Search for existing config file
    for path in getConfigSearchPaths():
        if os.path.exists(path):
            _active_config_file = path
            return path

    return None


def getWritableConfigPath() -> str:
    """Get the path where config file should be written.

    Returns:
        str: Path where config should be saved (user directory preferred)
    """
    # Try user config directory first (most portable for pip installs)
    user_config_dir = os.path.join(os.path.expanduser("~"), ".config", "FabOMatic")
    user_config_path = os.path.join(user_config_dir, "settings.toml")

    # Create directory if it doesn't exist
    try:
        os.makedirs(user_config_dir, exist_ok=True)
        # Test if writable
        test_file = os.path.join(user_config_dir, ".test_write")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        return user_config_path
    except (OSError, PermissionError):
        logging.warning("Cannot write to user config directory: %s", user_config_dir)

    # Fall back to package location
    return PACKAGE_CONFIG_FILE


def checkConfigFile() -> bool:
    """Check if config file exists, create from example if needed.

    Returns:
        bool: True if config file exists or was created successfully
    """
    global _active_config_file

    if useTestSettings:
        test_file = Path(TEST_SETTINGS_PATH)
        if not test_file.exists():
            logging.error("Missing TEST CONF FILE (%s)- try reinstalling", TEST_SETTINGS_PATH)
            return False
        return True

    # Check if config file already exists
    existing_config = getConfigFilePath()
    if existing_config:
        return True

    # No config found, create from example
    example_conf_file = Path(EXAMPLE_CONFIG_FILE)
    if not example_conf_file.exists():
        logging.error("Missing EXAMPLE CONF FILE (%s)- try reinstalling", EXAMPLE_CONFIG_FILE)
        return False

    # Get writable location and create config
    target_path = getWritableConfigPath()
    target_dir = os.path.dirname(target_path)

    try:
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy(EXAMPLE_CONFIG_FILE, target_path)
        _active_config_file = target_path
        logging.warning("Created default config file at: %s", target_path)
        return True
    except (OSError, PermissionError) as e:
        logging.error("Failed to create config file at %s: %s", target_path, e)
        return False


def loadSettings() -> dict:
    """Load settings from config file.

    Returns:
        dict: Configuration dictionary loaded from TOML file
    """
    global firstRun, useTestSettings

    checkConfigFile()

    if useTestSettings:
        if firstRun:
            logging.info("Using TEST settings file: %s", TEST_SETTINGS_PATH)
            firstRun = False
        return toml.load(TEST_SETTINGS_PATH)

    config_path = getConfigFilePath()
    if not config_path:
        raise FileNotFoundError("No configuration file found. Check installation.")

    if firstRun:
        logging.info("Using settings file: %s", config_path)
        firstRun = False

    return toml.load(config_path)


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


def validateSettings(settings: dict) -> tuple[bool, str]:
    """Validate settings before saving.

    Args:
        settings (dict): Configuration dictionary to validate

    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    required_sections = ["database", "MQTT", "web", "email"]
    required_fields = {
        "database": ["url", "name"],
        "MQTT": ["broker", "port", "client_id", "topic", "reply_subtopic", "stats_topic"],
        "web": ["secret_key", "default_admin_email"],
        "email": ["server", "port", "use_tls", "username", "password"]
    }

    # Check required sections exist
    for section in required_sections:
        if section not in settings:
            return False, f"Missing required section: {section}"

        # Check required fields in each section
        for field in required_fields[section]:
            if field not in settings[section]:
                return False, f"Missing required field: {section}.{field}"

    # Validate specific field types and values
    try:
        # MQTT port must be valid
        mqtt_port = settings["MQTT"]["port"]
        if not isinstance(mqtt_port, int) or mqtt_port < 1 or mqtt_port > 65535:
            return False, "MQTT port must be between 1 and 65535"

        # Email port must be valid
        email_port = settings["email"]["port"]
        if not isinstance(email_port, int) or email_port < 1 or email_port > 65535:
            return False, "Email port must be between 1 and 65535"

        # use_tls must be boolean
        if not isinstance(settings["email"]["use_tls"], bool):
            return False, "Email use_tls must be true or false"

        # Database URL must not be empty
        if not settings["database"]["url"].strip():
            return False, "Database URL cannot be empty"

        # Secret key must not be empty
        if not settings["web"]["secret_key"].strip():
            return False, "Web secret key cannot be empty"

    except (KeyError, TypeError, ValueError) as e:
        return False, f"Validation error: {str(e)}"

    return True, ""


def saveSettings(settings: dict) -> tuple[bool, str]:
    """Save settings to config file.

    Args:
        settings (dict): Configuration dictionary to save

    Returns:
        tuple[bool, str]: (success, error_message)
    """
    if useTestSettings:
        logging.warning("Cannot save settings in test mode")
        return False, "Cannot save settings in test mode"

    # Validate settings first
    is_valid, error_msg = validateSettings(settings)
    if not is_valid:
        logging.error("Settings validation failed: %s", error_msg)
        return False, error_msg

    config_path = getConfigFilePath()
    if not config_path:
        # No existing config, use writable path
        config_path = getWritableConfigPath()

    try:
        # Create backup of existing config
        if os.path.exists(config_path):
            backup_path = config_path + ".bak"
            shutil.copy(config_path, backup_path)
            logging.info("Created backup at: %s", backup_path)

        # Write new config
        with open(config_path, 'w') as f:
            toml.dump(settings, f)

        logging.info("Settings saved to: %s", config_path)
        return True, ""

    except (OSError, PermissionError, IOError) as e:
        error_msg = f"Failed to save settings: {str(e)}"
        logging.error("Failed to save settings to %s: %s", config_path, e)
        return False, error_msg


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
