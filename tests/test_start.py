"""Tests for the public start menu and optional links."""
import os
import unittest
from unittest.mock import patch

from app.handlers.start import (
    _public_url, group_start_keyboard, group_start_text, start_keyboard, start_text,
)


class StartMenuTests(unittest.TestCase):
    def test_private_and_group_start_messages_are_distinct(self):
        private = start_text("Ari")
        group = group_start_text("Anime Fans")
        self.assertIn("𝐖𝐞𝐥𝐜𝐨𝐦𝐞", private)
        self.assertIn("𝐀𝐫𝐢", private)
        self.assertIn("𝐒𝐞𝐧𝐭𝐢𝐧𝐞𝐥", private)
        self.assertIn("𝐒𝐞𝐧𝐭𝐢𝐧𝐞𝐥 𝐢𝐬 𝐨𝐧𝐥𝐢𝐧𝐞", group)
        self.assertIn("𝐀𝐧𝐢𝐦𝐞 𝐅𝐚𝐧𝐬", group)
        self.assertNotEqual(private, group)

    def test_group_start_keyboard_has_help_and_about(self):
        callbacks = [
            button.callback_data
            for row in group_start_keyboard().inline_keyboard
            for button in row
        ]
        self.assertEqual(callbacks, ["start:help", "start:about"])

    def test_rejects_non_https_or_malformed_links(self):
        with patch.dict(os.environ, {"MAIN_GROUP_URL": "http://example.com"}):
            self.assertIsNone(_public_url("MAIN_GROUP_URL"))
        with patch.dict(os.environ, {"MAIN_GROUP_URL": "not-a-url"}):
            self.assertIsNone(_public_url("MAIN_GROUP_URL"))

    def test_accepts_https_link(self):
        with patch.dict(os.environ, {"MAIN_GROUP_URL": "https://t.me/aniworld"}):
            self.assertEqual(_public_url("MAIN_GROUP_URL"), "https://t.me/aniworld")

    def test_start_menu_uses_configured_group_and_owner_links(self):
        env = {
            "MAIN_GROUP_URL": "https://t.me/aniworld",
            "OWNER_CONTACT_URL": "https://t.me/aniworld_owner",
        }
        with patch.dict(os.environ, env):
            keyboard = start_keyboard("ShieldBot")
        self.assertEqual(keyboard.inline_keyboard[0][0].url, env["MAIN_GROUP_URL"])
        self.assertEqual(keyboard.inline_keyboard[1][0].url, env["OWNER_CONTACT_URL"])
        self.assertEqual(keyboard.inline_keyboard[2][0].url, "https://t.me/ShieldBot?startgroup=true")

    def test_start_menu_add_group_link_is_generated_from_username(self):
        keyboard = start_keyboard("ShieldBot")
        self.assertEqual(keyboard.inline_keyboard[2][0].url, "https://t.me/ShieldBot?startgroup=true")


if __name__ == "__main__":
    unittest.main()
