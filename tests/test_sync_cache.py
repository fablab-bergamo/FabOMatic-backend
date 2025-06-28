"""
Unit tests for the sync cache functionality.
Tests the MQTT sync cache interface implementation.
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from FabOMatic.mqtt.mqtt_types import Parser, SyncCacheQuery, SyncCacheResponse
from FabOMatic.logic.MsgMapper import MsgMapper
from FabOMatic.database.constants import USER_LEVEL


class TestSyncCacheQuery(unittest.TestCase):
    """Test cases for SyncCacheQuery class."""

    def test_sync_cache_query_creation(self):
        """Test creating a SyncCacheQuery."""
        query = SyncCacheQuery()
        self.assertEqual(query.action, "synccache")

    def test_sync_cache_query_serialization(self):
        """Test serializing SyncCacheQuery to JSON."""
        query = SyncCacheQuery()
        json_str = query.toJSON()
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed["action"], "synccache")

    def test_sync_cache_query_deserialization(self):
        """Test deserializing SyncCacheQuery from JSON."""
        json_str = '{"action": "synccache"}'
        query = SyncCacheQuery.deserialize(json_str)
        
        self.assertIsInstance(query, SyncCacheQuery)
        self.assertEqual(query.action, "synccache")

    def test_parser_handles_sync_cache_action(self):
        """Test that Parser correctly handles synccache action."""
        json_str = '{"action": "synccache"}'
        parsed_query = Parser.parse(json_str)
        
        self.assertIsInstance(parsed_query, SyncCacheQuery)
        self.assertEqual(parsed_query.action, "synccache")


class TestSyncCacheResponse(unittest.TestCase):
    """Test cases for SyncCacheResponse class."""

    def test_sync_cache_response_creation(self):
        """Test creating a SyncCacheResponse."""
        response = SyncCacheResponse(True)
        self.assertTrue(response.request_ok)
        self.assertEqual(response.cards, [])

    def test_sync_cache_response_add_card(self):
        """Test adding cards to SyncCacheResponse."""
        response = SyncCacheResponse(True)
        response.add_card("1234ABCD", 1)
        response.add_card("5678EFGH", 2)
        
        self.assertEqual(len(response.cards), 2)
        self.assertEqual(response.cards[0], {"uid": "1234ABCD", "level": 1})
        self.assertEqual(response.cards[1], {"uid": "5678EFGH", "level": 2})

    def test_sync_cache_response_serialization(self):
        """Test serializing SyncCacheResponse to JSON."""
        response = SyncCacheResponse(True)
        response.add_card("1234ABCD", 1)
        response.add_card("5678EFGH", 2)
        
        json_str = response.serialize()
        parsed = json.loads(json_str)
        
        self.assertTrue(parsed["request_ok"])
        self.assertEqual(len(parsed["cards"]), 2)
        self.assertEqual(parsed["cards"][0]["uid"], "1234ABCD")
        self.assertEqual(parsed["cards"][0]["level"], 1)
        self.assertEqual(parsed["cards"][1]["uid"], "5678EFGH")
        self.assertEqual(parsed["cards"][1]["level"], 2)

    def test_sync_cache_response_error_case(self):
        """Test SyncCacheResponse for error cases."""
        response = SyncCacheResponse(False)
        
        json_str = response.serialize()
        parsed = json.loads(json_str)
        
        self.assertFalse(parsed["request_ok"])
        self.assertEqual(parsed["cards"], [])


class TestSyncCacheHandler(unittest.TestCase):
    """Test cases for sync cache handler in MsgMapper."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_mqtt = Mock()
        self.mock_db = Mock()
        self.msg_mapper = MsgMapper(self.mock_mqtt, self.mock_db)

    def test_get_authorized_cards_for_machine(self):
        """Test _getAuthorizedCardsForMachine method."""
        # Mock database session and repositories
        mock_session = MagicMock()
        mock_machine_repo = Mock()
        mock_user_repo = Mock()
        
        # Properly mock the context manager
        self.mock_db.getSession.return_value = mock_session
        self.mock_db.getMachineRepository.return_value = mock_machine_repo
        self.mock_db.getUserRepository.return_value = mock_user_repo
        
        # Mock machine
        mock_machine = Mock()
        mock_machine_repo.get_by_id.return_value = mock_machine
        
        # Mock users
        mock_user1 = Mock()
        mock_user1.disabled = False
        mock_user1.deleted = False
        mock_user1.card_UUID = "1234ABCD"
        # Create mock user level with name attribute
        mock_normal_level = Mock()
        mock_normal_level.name = "NORMAL"
        mock_user1.user_level.return_value = mock_normal_level
        
        mock_user2 = Mock()
        mock_user2.disabled = False
        mock_user2.deleted = False
        mock_user2.card_UUID = "5678EFGH"
        
        # Create mock user level with name attribute
        mock_admin_level = Mock()
        mock_admin_level.name = "ADMIN"
        mock_user2.user_level.return_value = mock_admin_level
        
        mock_user3 = Mock()  # Disabled user - should be skipped
        mock_user3.disabled = True
        mock_user3.deleted = False
        mock_user3.card_UUID = "9ABC0123"
        
        mock_user_repo.get_all.return_value = [mock_user1, mock_user2, mock_user3]
        mock_user_repo.IsUserAuthorizedForMachine.side_effect = lambda machine, user: user != mock_user3
        
        # Test the method
        result = self.msg_mapper._getAuthorizedCardsForMachine(1)
        
        # Verify results
        self.assertEqual(len(result), 2)
        self.assertIn({"uid": "1234ABCD", "level": 1}, result)
        self.assertIn({"uid": "5678EFGH", "level": 2}, result)

    def test_handle_sync_cache_query(self):
        """Test handleSyncCacheQuery method."""
        # Mock machine logic
        mock_machine_logic = Mock()
        mock_machine_logic.getMachineId.return_value = 1
        
        # Mock the _getAuthorizedCardsForMachine method
        test_cards = [
            {"uid": "1234ABCD", "level": 1},
            {"uid": "5678EFGH", "level": 2}
        ]
        
        with patch.object(self.msg_mapper, '_getAuthorizedCardsForMachine', return_value=test_cards):
            sync_query = SyncCacheQuery()
            result = self.msg_mapper.handleSyncCacheQuery(mock_machine_logic, sync_query)
        
        # Parse the result
        parsed_result = json.loads(result)
        
        # Verify the response
        self.assertTrue(parsed_result["request_ok"])
        self.assertEqual(len(parsed_result["cards"]), 2)
        self.assertEqual(parsed_result["cards"][0]["uid"], "1234ABCD")
        self.assertEqual(parsed_result["cards"][1]["uid"], "5678EFGH")

    def test_handle_sync_cache_query_truncation(self):
        """Test that large card lists are truncated to 200 cards."""
        # Mock machine logic
        mock_machine_logic = Mock()
        mock_machine_logic.getMachineId.return_value = 1
        
        # Create a large list of cards (250 cards)
        large_card_list = [{"uid": f"CARD{i:04d}", "level": 1} for i in range(250)]
        
        with patch.object(self.msg_mapper, '_getAuthorizedCardsForMachine', return_value=large_card_list):
            sync_query = SyncCacheQuery()
            result = self.msg_mapper.handleSyncCacheQuery(mock_machine_logic, sync_query)
        
        # Parse the result
        parsed_result = json.loads(result)
        
        # Verify truncation to 200 cards
        self.assertTrue(parsed_result["request_ok"])
        self.assertEqual(len(parsed_result["cards"]), 200)

    def test_handle_sync_cache_query_error(self):
        """Test error handling in handleSyncCacheQuery."""
        # Mock machine logic that throws an exception in _getAuthorizedCardsForMachine
        mock_machine_logic = Mock()
        mock_machine_logic.getMachineId.return_value = 1
        
        # Mock the _getAuthorizedCardsForMachine to raise an exception
        with patch.object(self.msg_mapper, '_getAuthorizedCardsForMachine', side_effect=Exception("Database error")):
            sync_query = SyncCacheQuery()
            result = self.msg_mapper.handleSyncCacheQuery(mock_machine_logic, sync_query)
        
        # Parse the result
        parsed_result = json.loads(result)
        
        # Verify error response
        self.assertFalse(parsed_result["request_ok"])
        self.assertEqual(parsed_result["cards"], [])


class TestSyncCacheIntegration(unittest.TestCase):
    """Integration tests for sync cache functionality."""

    def test_full_sync_cache_workflow(self):
        """Test the complete sync cache workflow from query to response."""
        # Create a sync cache query JSON (as would come from C++ firmware)
        query_json = '{"action": "synccache"}'
        
        # Parse the query
        parsed_query = Parser.parse(query_json)
        self.assertIsInstance(parsed_query, SyncCacheQuery)
        
        # Create a mock response with sample data
        response = SyncCacheResponse(True)
        response.add_card("1234ABCD", 1)  # Normal user
        response.add_card("5678EFGH", 2)  # Admin user
        
        # Serialize the response
        response_json = response.serialize()
        
        # Verify the response can be parsed by C++ firmware
        parsed_response = json.loads(response_json)
        self.assertTrue(parsed_response["request_ok"])
        self.assertEqual(len(parsed_response["cards"]), 2)
        
        # Verify card format matches C++ expectations
        for card in parsed_response["cards"]:
            self.assertIn("uid", card)
            self.assertIn("level", card)
            self.assertIsInstance(card["uid"], str)
            self.assertIsInstance(card["level"], int)
            self.assertIn(card["level"], [1, 2])  # Valid user levels


if __name__ == '__main__':
    unittest.main()