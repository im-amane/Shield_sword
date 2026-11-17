"""Tests for owner dashboard rendering and controls."""
import unittest

from app.handlers.panel import dashboard_keyboard, dashboard_text


class DashboardTests(unittest.TestCase):
    def test_dashboard_includes_runtime_identity(self) -> None:
        text = dashboard_text("ani_world_bot", 112233, 987654321)
        self.assertIn("@ani_world_bot", text)
        self.assertIn("<code>112233</code>", text)
        self.assertIn("<code>987654321</code>", text)
        self.assertIn("Online", text)

    def test_dashboard_handles_missing_username(self) -> None:
        text = dashboard_text(None, 112233, 987654321)
        self.assertIn("𝐍𝐨𝐭 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞", text)

    def test_keyboard_exposes_only_refresh_and_close(self) -> None:
        keyboard = dashboard_keyboard()
        callbacks = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        ]
        self.assertEqual(callbacks, ["owner_panel:refresh", "owner_panel:close"])


if __name__ == "__main__":
    unittest.main()
