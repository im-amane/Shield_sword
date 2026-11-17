"""Unit tests for moderation helpers."""
import unittest

from app.handlers.moderation import (
    DEFAULT_MUTE_SECONDS,
    MAX_MUTE_SECONDS,
    format_duration,
    parse_duration,
    restored_permissions,
)


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
