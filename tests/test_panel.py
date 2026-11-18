"""Tests for the owner dashboard and security intelligence navigation."""
import os
import unittest
from unittest.mock import patch

from app.handlers.panel import dashboard_keyboard, dashboard_text, section_keyboard, section_text
from app.handlers.typography import premium_text


class DashboardTests(unittest.TestCase):
    def test_dashboard_includes_runtime_identity_and_security_stats(self) -> None:
        text = dashboard_text("ani_world_bot", 112233, 987654321)
        self.assertIn("@ani_world_bot", text)
        self.assertIn("<code>112233</code>", text)
        self.assertIn("𝐎𝐧𝐥𝐢𝐧𝐞", text)
        self.assertIn("𝐂𝐎𝐌𝐌𝐔𝐍𝐈𝐓𝐘 𝐀𝐓 𝐀 𝐆𝐋𝐀𝐍𝐂𝐄", text)

    def test_dashboard_handles_missing_username(self) -> None:
        text = dashboard_text(None, 112233, 987654321)
        self.assertIn("𝐍𝐨𝐭 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞", text)

    def test_dashboard_has_full_owner_navigation(self) -> None:
        callbacks = [
            button.callback_data
            for row in dashboard_keyboard().inline_keyboard
            for button in row
        ]
        self.assertEqual(
            callbacks,
            ["owner_panel:security", "owner_panel:groups",
             "owner_panel:activity", "owner_panel:audit",
             "owner_panel:database", "owner_panel:backup",
             "owner_panel:configuration", "owner_panel:automation",
             "owner_panel:commands", "owner_panel:refresh", "owner_panel:close"],
        )

    def test_database_health_section_shows_backup_and_report_timestamps(self) -> None:
        with patch("app.handlers.panel.get_database_status", return_value={
            "integrity": "ok", "table_count": 12, "size_bytes": 1024,
            "journal_mode": "wal",
        }), patch("app.handlers.panel.get_last_automatic_backup_at", return_value=1_700_000_000), patch(
            "app.handlers.panel.get_last_daily_report_at", return_value=None
        ):
            text = section_text("database")
        self.assertIn(premium_text("Last automatic backup"), text)
        self.assertIn(premium_text("Last daily report"), text)
        self.assertIn("Not delivered yet", text)

    def test_configuration_never_displays_secret_values(self) -> None:
        secret = "DO_NOT_DISPLAY_THIS_SECRET"
        with patch.dict(os.environ, {
            "BOT_TOKEN": secret,
            "OWNER_ID": "12345",
            "DATABASE_PATH": "/data/db.sqlite3",
            "BACKUP_ENCRYPTION_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        }, clear=True):
            text = section_text("configuration")
        self.assertNotIn(secret, text)
        self.assertNotIn("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", text)
        self.assertIn("Key fingerprint", text)
        self.assertIn("Configured", text)

    def test_configuration_reports_missing_encryption_key_without_crashing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            text = section_text("configuration")
        self.assertIn("Missing or invalid", text)

    def test_command_index_and_automation_sections_exist(self) -> None:
        self.assertIn("channelprotect", section_text("commands"))
        self.assertIn("Weekly encrypted backup", section_text("automation"))

    def test_section_keyboard_returns_to_dashboard(self) -> None:
        callbacks = [
            button.callback_data
            for row in section_keyboard("activity").inline_keyboard
            for button in row
        ]
        self.assertEqual(callbacks, ["owner_panel:home", "owner_panel:refresh_activity", "owner_panel:close"])


if __name__ == "__main__":
    unittest.main()
