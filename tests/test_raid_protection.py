"""Tests for automatic rapid-join raid detection."""
import unittest

from aiogram.types import User

from app.handlers.raid_protection import (
    RAID_JOIN_THRESHOLD,
    RAID_MODE_SECONDS,
    RAID_WINDOW_SECONDS,
    is_raid_mode_active,
    record_join_activity,
    reset_raid_state,
)


class RaidProtectionTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_raid_state()

    def test_activates_at_500_human_joins_inside_window(self) -> None:
        members = [
            User(id=index + 1, is_bot=False, first_name="Member")
            for index in range(RAID_JOIN_THRESHOLD)
        ]
        activated, count, active = record_join_activity(-1001, members, now=1000.0)
        self.assertTrue(activated)
        self.assertEqual(count, RAID_JOIN_THRESHOLD)
        self.assertTrue(active)
        self.assertTrue(is_raid_mode_active(-1001, now=1001.0))

    def test_accumulates_multiple_join_batches(self) -> None:
        first = [User(id=i + 1, is_bot=False, first_name="A") for i in range(300)]
        second = [User(id=i + 301, is_bot=False, first_name="B") for i in range(200)]
        self.assertEqual(record_join_activity(-1002, first, now=1000.0), (False, 300, False))
        activated, count, active = record_join_activity(-1002, second, now=1005.0)
        self.assertTrue(activated)
        self.assertEqual(count, 500)
        self.assertTrue(active)

    def test_does_not_count_bots(self) -> None:
        members = [
            User(id=i + 1, is_bot=True, first_name="Bot")
            for i in range(RAID_JOIN_THRESHOLD)
        ]
        activated, count, active = record_join_activity(-1003, members, now=1000.0)
        self.assertFalse(activated)
        self.assertEqual(count, 0)
        self.assertFalse(active)

    def test_joins_outside_window_do_not_accumulate(self) -> None:
        first = [User(id=i + 1, is_bot=False, first_name="A") for i in range(300)]
        second = [User(id=i + 301, is_bot=False, first_name="B") for i in range(200)]
        record_join_activity(-1004, first, now=1000.0)
        activated, count, active = record_join_activity(
            -1004, second, now=1000.0 + RAID_WINDOW_SECONDS + 1
        )
        self.assertFalse(activated)
        self.assertEqual(count, 200)
        self.assertFalse(active)

    def test_raid_mode_expires(self) -> None:
        members = [
            User(id=i + 1, is_bot=False, first_name="Member")
            for i in range(RAID_JOIN_THRESHOLD)
        ]
        record_join_activity(-1005, members, now=1000.0)
        self.assertTrue(is_raid_mode_active(-1005, now=1001.0))
        self.assertFalse(is_raid_mode_active(-1005, now=1000.0 + RAID_MODE_SECONDS + 1))


if __name__ == "__main__":
    unittest.main()
