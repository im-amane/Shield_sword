"""Tests for the public start menu and optional links."""
import os
import unittest
from unittest.mock import patch

from app.handlers.start import _public_url, start_keyboard


class StartMenuTests(unittest.TestCase):
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
