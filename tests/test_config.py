"""Test configuration management functionality."""

import os
import tempfile
import shutil
import pytest

from FabOMatic.conf import FabConfig


class TestConfigPaths:
    """Test configuration file path resolution."""

    def test_get_config_search_paths(self):
        """Test that config search paths are returned in correct order."""
        paths = FabConfig.getConfigSearchPaths()

        assert len(paths) == 4, "Should return 4 search paths"
        assert paths[0].endswith("/.config/FabOMatic/settings.toml"), "First should be user config"
        assert paths[1] == "/etc/FabOMatic/settings.toml", "Second should be system config"
        assert paths[2].endswith("/FabOMatic/settings.toml"), "Third should be home directory"
        assert "conf/settings.toml" in paths[3], "Fourth should be package directory"

    def test_get_writable_config_path(self):
        """Test that writable config path is determined correctly."""
        writable_path = FabConfig.getWritableConfigPath()

        assert writable_path is not None, "Should return a writable path"
        # Should prefer user config directory
        assert ".config/FabOMatic" in writable_path or "conf/settings.toml" in writable_path


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_complete_settings(self):
        """Test validation of complete valid settings."""
        valid_settings = {
            "database": {
                "url": "sqlite:///test.db",
                "name": "testdb"
            },
            "MQTT": {
                "broker": "localhost",
                "port": 1883,
                "client_id": "test-client",
                "topic": "machine",
                "reply_subtopic": "/reply",
                "stats_topic": "stats"
            },
            "web": {
                "secret_key": "test-secret-key",
                "default_admin_email": "admin@test.com"
            },
            "email": {
                "server": "smtp.test.com",
                "port": 587,
                "use_tls": True,
                "username": "user",
                "password": "pass",
                "sender": "noreply@test.com"
            }
        }

        is_valid, error_msg = FabConfig.validateSettings(valid_settings)
        assert is_valid, f"Valid settings should pass validation: {error_msg}"
        assert error_msg == "", "Error message should be empty for valid settings"

    def test_validate_missing_section(self):
        """Test validation fails when required section is missing."""
        invalid_settings = {
            "database": {"url": "sqlite:///test.db", "name": "testdb"},
            "MQTT": {"broker": "localhost", "port": 1883, "client_id": "test",
                     "topic": "machine", "reply_subtopic": "/reply", "stats_topic": "stats"},
            "web": {"secret_key": "secret", "default_admin_email": "test@test.com"}
            # Missing "email" section
        }

        is_valid, error_msg = FabConfig.validateSettings(invalid_settings)
        assert not is_valid, "Should fail validation with missing section"
        assert "email" in error_msg.lower(), "Error message should mention missing section"

    def test_validate_missing_field(self):
        """Test validation fails when required field is missing."""
        invalid_settings = {
            "database": {"url": "sqlite:///test.db"},  # Missing "name"
            "MQTT": {"broker": "localhost", "port": 1883, "client_id": "test",
                     "topic": "machine", "reply_subtopic": "/reply", "stats_topic": "stats"},
            "web": {"secret_key": "secret", "default_admin_email": "test@test.com"},
            "email": {"server": "smtp.test.com", "port": 587, "use_tls": True,
                     "username": "user", "password": "pass", "sender": "test@test.com"}
        }

        is_valid, error_msg = FabConfig.validateSettings(invalid_settings)
        assert not is_valid, "Should fail validation with missing field"
        assert "name" in error_msg.lower(), "Error message should mention missing field"

    def test_validate_invalid_mqtt_port(self):
        """Test validation fails with invalid MQTT port."""
        invalid_settings = {
            "database": {"url": "sqlite:///test.db", "name": "testdb"},
            "MQTT": {"broker": "localhost", "port": 99999,  # Invalid port
                     "client_id": "test", "topic": "machine",
                     "reply_subtopic": "/reply", "stats_topic": "stats"},
            "web": {"secret_key": "secret", "default_admin_email": "test@test.com"},
            "email": {"server": "smtp.test.com", "port": 587, "use_tls": True,
                     "username": "user", "password": "pass", "sender": "test@test.com"}
        }

        is_valid, error_msg = FabConfig.validateSettings(invalid_settings)
        assert not is_valid, "Should fail validation with invalid port"
        assert "port" in error_msg.lower(), "Error message should mention port issue"

    def test_validate_empty_database_url(self):
        """Test validation fails with empty database URL."""
        invalid_settings = {
            "database": {"url": "   ", "name": "testdb"},  # Empty URL
            "MQTT": {"broker": "localhost", "port": 1883, "client_id": "test",
                     "topic": "machine", "reply_subtopic": "/reply", "stats_topic": "stats"},
            "web": {"secret_key": "secret", "default_admin_email": "test@test.com"},
            "email": {"server": "smtp.test.com", "port": 587, "use_tls": True,
                     "username": "user", "password": "pass", "sender": "test@test.com"}
        }

        is_valid, error_msg = FabConfig.validateSettings(invalid_settings)
        assert not is_valid, "Should fail validation with empty database URL"
        assert "database" in error_msg.lower() or "url" in error_msg.lower()


class TestConfigSaveLoad:
    """Test saving and loading configuration."""

    def test_save_and_load_settings(self):
        """Test saving settings to a temporary file and loading them back."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config_path = os.path.join(temp_dir, "test_settings.toml")

            test_settings = {
                "database": {"url": "sqlite:///test.db", "name": "testdb"},
                "MQTT": {"broker": "localhost", "port": 1883, "client_id": "test",
                         "topic": "machine", "reply_subtopic": "/reply", "stats_topic": "stats"},
                "web": {"secret_key": "test-secret", "default_admin_email": "test@test.com"},
                "email": {"server": "smtp.test.com", "port": 587, "use_tls": True,
                         "username": "testuser", "password": "testpass", "sender": "noreply@test.com"}
            }

            # Save directly using toml for initial setup
            import toml
            with open(test_config_path, 'w') as f:
                toml.dump(test_settings, f)

            # Override the config file path for testing
            original_cache = FabConfig._active_config_file
            FabConfig._active_config_file = test_config_path

            # Load settings to verify
            loaded_settings = FabConfig.loadSettings()
            assert loaded_settings["database"]["url"] == "sqlite:///test.db"
            assert loaded_settings["MQTT"]["port"] == 1883
            assert loaded_settings["web"]["secret_key"] == "test-secret"
            assert loaded_settings["email"]["use_tls"] is True

            # Modify and save through FabConfig
            loaded_settings["database"]["url"] = "sqlite:///modified.db"
            success, error_msg = FabConfig.saveSettings(loaded_settings)
            assert success, f"Should save settings successfully: {error_msg}"

            # Load again to verify modification
            FabConfig._active_config_file = test_config_path  # Reset cache
            modified_settings = FabConfig.loadSettings()
            assert modified_settings["database"]["url"] == "sqlite:///modified.db"

            # Restore original cache
            FabConfig._active_config_file = original_cache

    def test_save_creates_backup(self):
        """Test that saving creates a backup of existing config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config_path = os.path.join(temp_dir, "test_settings.toml")
            backup_path = test_config_path + ".bak"

            initial_settings = {
                "database": {"url": "sqlite:///initial.db", "name": "initial"},
                "MQTT": {"broker": "localhost", "port": 1883, "client_id": "test",
                         "topic": "machine", "reply_subtopic": "/reply", "stats_topic": "stats"},
                "web": {"secret_key": "initial-secret", "default_admin_email": "initial@test.com"},
                "email": {"server": "smtp.test.com", "port": 587, "use_tls": True,
                         "username": "user", "password": "pass", "sender": "noreply@test.com"}
            }

            # Create initial config file
            import toml
            with open(test_config_path, 'w') as f:
                toml.dump(initial_settings, f)

            # Override cache
            original_cache = FabConfig._active_config_file
            FabConfig._active_config_file = test_config_path

            # Update settings
            updated_settings = initial_settings.copy()
            updated_settings["database"]["url"] = "sqlite:///updated.db"

            # Save updated settings (should create backup)
            success, _ = FabConfig.saveSettings(updated_settings)
            assert success, "Should save successfully"
            assert os.path.exists(backup_path), "Backup file should be created"

            # Verify backup contains original content
            backup_content = toml.load(backup_path)
            assert backup_content["database"]["url"] == "sqlite:///initial.db"

            # Verify current file has updated content
            current_content = toml.load(test_config_path)
            assert current_content["database"]["url"] == "sqlite:///updated.db"

            # Restore original cache
            FabConfig._active_config_file = original_cache

    def test_save_fails_with_invalid_settings(self):
        """Test that saving fails when settings are invalid."""
        invalid_settings = {
            "database": {"url": "sqlite:///test.db"},  # Missing "name"
            "MQTT": {"broker": "localhost", "port": 1883, "client_id": "test",
                     "topic": "machine", "reply_subtopic": "/reply", "stats_topic": "stats"},
            "web": {"secret_key": "secret", "default_admin_email": "test@test.com"},
            "email": {"server": "smtp.test.com", "port": 587, "use_tls": True,
                     "username": "user", "password": "pass", "sender": "test@test.com"}
        }

        success, error_msg = FabConfig.saveSettings(invalid_settings)
        assert not success, "Should fail to save invalid settings"
        assert error_msg != "", "Should provide error message"
