"""Tests for environment configuration validation."""
import os
import unittest
from unittest.mock import patch

from app.config import ConfigurationError, load_settings


class LoadSettingsTests(unittest.TestCase):
    def test_loads_required_token(self) -> None:
        with patch.dict(os.environ, {"BOT_TOKEN": "123:abc"}, clear=True):
            settings = load_settings()
        self.assertEqual(settings.bot_token, "123:abc")
        self.assertIsNone(settings.owner_id)
        self.assertEqual(settings.welcome_chat_ids, ())

    def test_loads_optional_owner_id(self) -> None:
        with patch.dict(
            os.environ, {"BOT_TOKEN": "123:abc", "OWNER_ID": "987654"}, clear=True
        ):
            settings = load_settings()
        self.assertEqual(settings.owner_id, 987654)

    def test_parses_and_deduplicates_welcome_chat_ids(self) -> None:
        with patch.dict(
            os.environ,
            {"BOT_TOKEN": "123:abc", "WELCOME_CHAT_IDS": "-1001, -1002,-1001"},
            clear=True,
        ):
            settings = load_settings()
        self.assertEqual(settings.welcome_chat_ids, (-1001, -1002))

    def test_rejects_non_numeric_welcome_chat_id(self) -> None:
        with patch.dict(
            os.environ,
            {"BOT_TOKEN": "123:abc", "WELCOME_CHAT_IDS": "-1001,group"},
            clear=True,
        ):
            with self.assertRaises(ConfigurationError):
                load_settings()

    def test_rejects_positive_welcome_chat_id(self) -> None:
        with patch.dict(
            os.environ,
            {"BOT_TOKEN": "123:abc", "WELCOME_CHAT_IDS": "12345"},
            clear=True,
        ):
            with self.assertRaises(ConfigurationError):
                load_settings()

    def test_rejects_empty_welcome_chat_id_entry(self) -> None:
        with patch.dict(
            os.environ,
            {"BOT_TOKEN": "123:abc", "WELCOME_CHAT_IDS": "-1001,"},
            clear=True,
        ):
            with self.assertRaises(ConfigurationError):
                load_settings()

    def test_missing_token_is_rejected(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                load_settings()

    def test_non_numeric_owner_id_is_rejected(self) -> None:
        with patch.dict(
            os.environ, {"BOT_TOKEN": "123:abc", "OWNER_ID": "owner"}, clear=True
        ):
            with self.assertRaises(ConfigurationError):
                load_settings()

    def test_non_positive_owner_id_is_rejected(self) -> None:
        with patch.dict(
            os.environ, {"BOT_TOKEN": "123:abc", "OWNER_ID": "0"}, clear=True
        ):
            with self.assertRaises(ConfigurationError):
                load_settings()


if __name__ == "__main__":
    unittest.main()
