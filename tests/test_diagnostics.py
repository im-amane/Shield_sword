"""Tests for live group permission diagnostics."""
import unittest
from types import SimpleNamespace

from aiogram.enums import ChatMemberStatus

from app.handlers.diagnostics import format_member_status, permission_lines


class PermissionDiagnosticsTests(unittest.TestCase):
    def test_creator_has_full_rights(self):
        lines = permission_lines(SimpleNamespace(status=ChatMemberStatus.CREATOR))
        self.assertIn("✅ Group owner: full administrator rights", lines)

    def test_admin_with_required_rights_passes(self):
        member = SimpleNamespace(
            status=ChatMemberStatus.ADMINISTRATOR,
            can_delete_messages=True,
            can_restrict_members=True,
        )
        lines = permission_lines(member)
        self.assertTrue(all(line.startswith("✅") for line in lines))

    def test_missing_rights_are_reported_individually(self):
        member = SimpleNamespace(
            status=ChatMemberStatus.ADMINISTRATOR,
            can_delete_messages=True,
            can_restrict_members=False,
        )
        lines = permission_lines(member)
        self.assertTrue(lines[0].startswith("✅"))
        self.assertTrue(lines[1].startswith("❌"))

    def test_non_admin_is_reported(self):
        member = SimpleNamespace(status=ChatMemberStatus.MEMBER)
        self.assertEqual(permission_lines(member), ["❌ Bot is not an administrator"])

    def test_status_formatter_accepts_enum_and_raw_string(self):
        self.assertEqual(format_member_status(ChatMemberStatus.ADMINISTRATOR), "administrator")
        self.assertEqual(format_member_status("administrator"), "administrator")

    def test_status_formatter_escapes_untrusted_string(self):
        self.assertEqual(format_member_status("<admin>"), "&lt;admin&gt;")


if __name__ == "__main__":
    unittest.main()
