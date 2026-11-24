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
        self.assertFalse(settings.ai_guard_enabled)
        self.assertEqual(
            settings.nvidia_nim_model,
            "nvidia/llama-3.1-nemotron-safety-guard-8b-v3",
        )

    def test_loads_optional_owner_id(self) -> None:
        with patch.dict(
            os.environ, {"BOT_TOKEN": "123:abc", "OWNER_ID": "987654"}, clear=True
        ):
            settings = load_settings()
        self.assertEqual(settings.owner_id, 987654)

    def test_ai_guard_can_be_enabled_independently(self) -> None:
        with patch.dict(
            os.environ,
            {
                "BOT_TOKEN": "123:abc",
                "AI_GUARD_ENABLED": "true",
                "NVIDIA_NIM_GUARDIAN_API_KEY": "guardian-key",
            },
            clear=True,
        ):
            settings = load_settings()
        self.assertTrue(settings.ai_guard_enabled)
        self.assertEqual(settings.nvidia_nim_guardian_api_key, "guardian-key")

    def test_chat_environment_variables_are_ignored(self) -> None:
        with patch.dict(
            os.environ,
            {
                "BOT_TOKEN": "123:abc",
                "AI_CHAT_ENABLED": "true",
                "NVIDIA_NIM_CHAT_API_KEY": "unused",
            },
            clear=True,
        ):
            settings = load_settings()
        self.assertFalse(settings.ai_guard_enabled)
        self.assertFalse(hasattr(settings, "ai_chat_enabled"))
        self.assertFalse(hasattr(settings, "nvidia_nim_chat_api_key"))

    def test_welcome_is_not_limited_by_environment_allowlist(self) -> None:
        with patch.dict(
            os.environ,
            {"BOT_TOKEN": "123:abc", "WELCOME_CHAT_IDS": "-1001"},
            clear=True,
        ):
            settings = load_settings()
        self.assertEqual(settings.welcome_chat_ids, ())

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
