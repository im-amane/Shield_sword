"""Tests for permission monitoring summaries."""
import unittest
from types import SimpleNamespace
from aiogram.enums import ChatMemberStatus
from app.handlers.permission_monitor import permission_change_summary

def member(status, delete=False, restrict=False):
    return SimpleNamespace(status=status, can_delete_messages=delete, can_restrict_members=restrict)

def update(old, new):
    return SimpleNamespace(old_chat_member=old, new_chat_member=new)

class PermissionMonitorTests(unittest.TestCase):
    def test_no_change_produces_no_alert(self):
        state = member(ChatMemberStatus.ADMINISTRATOR, True, True)
        self.assertEqual(permission_change_summary(update(state, state)), [])

    def test_delete_permission_loss_is_critical(self):
        changes = permission_change_summary(update(member(ChatMemberStatus.ADMINISTRATOR, True, True), member(ChatMemberStatus.ADMINISTRATOR, False, True)))
        self.assertTrue(any("Delete Messages: REMOVED" in item for item in changes))
        self.assertTrue(any("Protection impact" in item for item in changes))

    def test_bot_removed_from_group_is_detected(self):
        changes = permission_change_summary(update(member(ChatMemberStatus.ADMINISTRATOR, True, True), member(ChatMemberStatus.LEFT)))
        self.assertTrue(any("no longer an administrator" in item for item in changes))

    def test_permission_grant_is_reported(self):
        changes = permission_change_summary(update(member(ChatMemberStatus.ADMINISTRATOR), member(ChatMemberStatus.ADMINISTRATOR, True, True)))
        self.assertTrue(any("Delete Messages: granted" in item for item in changes))
        self.assertTrue(any("critical protection permissions are available" in item.lower() for item in changes))

if __name__ == "__main__":
    unittest.main()
