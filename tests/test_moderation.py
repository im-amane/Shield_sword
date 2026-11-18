"""Unit tests for moderation helpers."""
import unittest
from unittest.mock import AsyncMock

from app.handlers.moderation import (
    DEFAULT_MUTE_SECONDS,
    MAX_MUTE_SECONDS,
    format_duration,
    perform_kick,
    parse_duration,
    restored_permissions,
)


class KickOperationTests(unittest.IsolatedAsyncioTestCase):
    async def test_kick_unbans_after_successful_ban(self) -> None:
        bot = type("BotStub", (), {})()
        bot.ban_chat_member = AsyncMock()
        bot.unban_chat_member = AsyncMock()

        result = await perform_kick(bot, -100, 42)

        self.assertTrue(result)
        bot.ban_chat_member.assert_awaited_once_with(chat_id=-100, user_id=42)
        bot.unban_chat_member.assert_awaited_once_with(
            chat_id=-100, user_id=42, only_if_banned=True
        )

    async def test_partial_kick_is_reported_when_unban_fails(self) -> None:
        bot = type("BotStub", (), {})()
        bot.ban_chat_member = AsyncMock()
        bot.unban_chat_member = AsyncMock(side_effect=RuntimeError("Telegram unavailable"))

        result = await perform_kick(bot, -100, 42)

        self.assertFalse(result)
        bot.ban_chat_member.assert_awaited_once()
        bot.unban_chat_member.assert_awaited_once()


class ModerationHelperTests(unittest.TestCase):
    def test_default_mute_duration(self) -> None:
        self.assertEqual(parse_duration(None), DEFAULT_MUTE_SECONDS)

    def test_parse_supported_duration_units(self) -> None:
        self.assertEqual(parse_duration("30s"), 30)
        self.assertEqual(parse_duration("10m"), 600)
        self.assertEqual(parse_duration("2h"), 7200)
        self.assertEqual(parse_duration("1d"), 86400)

    def test_duration_limits_are_enforced(self) -> None:
        with self.assertRaises(ValueError):
            parse_duration("10s")
        with self.assertRaises(ValueError):
            parse_duration(f"{MAX_MUTE_SECONDS // 86400 + 1}d")
        with self.assertRaises(ValueError):
            parse_duration("tomorrow")

    def test_unmute_restores_group_default_permissions(self) -> None:
        from aiogram.types import ChatPermissions

        defaults = ChatPermissions(can_send_messages=True, can_send_photos=False)
        restored = restored_permissions(defaults)
        self.assertTrue(restored.can_send_messages)
        self.assertFalse(restored.can_send_photos)

    def test_unmute_fallback_is_explicit_when_group_has_no_defaults(self) -> None:
        restored = restored_permissions(None)
        self.assertTrue(restored.can_send_messages)
        self.assertTrue(restored.can_send_photos)

    def test_format_duration(self) -> None:
        self.assertEqual(format_duration(600), "10 minutes")
        self.assertEqual(format_duration(3600), "1 hour")


if __name__ == "__main__":
    unittest.main()
