"""Tests for owner-manageable raid mode controls."""
import unittest

from app.handlers.raid_protection import (
    RAID_JOIN_THRESHOLD,
    RAID_MODE_SECONDS,
    disable_raid_mode,
    raid_status,
    record_join_activity,
    reset_raid_state,
)
from aiogram.types import User


class RaidControlsTests(unittest.TestCase):
    def setUp(self):
        reset_raid_state()

    def test_status_reports_active_mode_and_remaining_time(self):
        members = [User(id=i + 1, is_bot=False, first_name="Member") for i in range(RAID_JOIN_THRESHOLD)]
        record_join_activity(-2001, members, now=1000.0)
        active, count, remaining = raid_status(-2001, now=1010.0)
        self.assertTrue(active)
        self.assertEqual(count, RAID_JOIN_THRESHOLD)
        self.assertEqual(remaining, RAID_MODE_SECONDS - 10)

    def test_owner_disable_helper_turns_mode_off(self):
        members = [User(id=i + 1, is_bot=False, first_name="Member") for i in range(RAID_JOIN_THRESHOLD)]
        record_join_activity(-2002, members, now=1000.0)
        self.assertTrue(disable_raid_mode(-2002))
        self.assertFalse(raid_status(-2002, now=1001.0)[0])

    def test_disabling_inactive_mode_returns_false(self):
        self.assertFalse(disable_raid_mode(-2003))


if __name__ == "__main__":
    unittest.main()
