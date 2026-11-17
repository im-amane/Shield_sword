"""Tests for the owner dashboard and security intelligence navigation."""
import unittest

from app.handlers.panel import dashboard_keyboard, dashboard_text, section_keyboard


class DashboardTests(unittest.TestCase):
    def test_dashboard_includes_runtime_identity_and_security_stats(self) -> None:
        text = dashboard_text("ani_world_bot", 112233, 987654321)
        self.assertIn("@ani_world_bot", text)
        self.assertIn("<code>112233</code>", text)
        self.assertIn("<code>987654321</code>", text)
        self.assertIn("𝐎𝐧𝐥𝐢𝐧𝐞", text)
        self.assertIn("𝐂𝐨𝐦𝐦𝐮𝐧𝐢𝐭𝐲 𝐨𝐯𝐞𝐫𝐯𝐢𝐞𝐰", text)

    def test_dashboard_handles_missing_username(self) -> None:
        text = dashboard_text(None, 112233, 987654321)
        self.assertIn("𝐍𝐨𝐭 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞", text)

    def test_dashboard_has_owner_sections(self) -> None:
        callbacks = [
            button.callback_data
            for row in dashboard_keyboard().inline_keyboard
            for button in row
        ]
        self.assertEqual(
            callbacks,
            ["owner_panel:security", "owner_panel:groups",
             "owner_panel:activity", "owner_panel:database",
             "owner_panel:refresh", "owner_panel:close"],
        )

    def test_section_keyboard_returns_to_dashboard(self) -> None:
        callbacks = [
            button.callback_data
            for row in section_keyboard("activity").inline_keyboard
            for button in row
        ]
        self.assertEqual(callbacks, ["owner_panel:home", "owner_panel:refresh_activity", "owner_panel:close"])


if __name__ == "__main__":
    unittest.main()
