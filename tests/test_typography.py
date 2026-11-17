"""Tests for premium user-facing typography."""
import unittest

from app.handlers.typography import premium_text


class PremiumTypographyTests(unittest.TestCase):
    def test_styles_prose_and_preserves_commands(self) -> None:
        value = premium_text("Welcome! Use /start or /help to begin.")
        self.assertIn("𝐖𝐞𝐥𝐜𝐨𝐦𝐞", value)
        self.assertIn("/start", value)
        self.assertIn("/help", value)

    def test_preserves_html_and_code_content(self) -> None:
        value = premium_text("<b>Welcome</b> <code>/panel</code>")
        self.assertIn("<b>", value)
        self.assertIn("</b>", value)
        self.assertIn("<code>/panel</code>", value)
        self.assertIn("𝐖𝐞𝐥𝐜𝐨𝐦𝐞", value)

    def test_preserves_entities(self) -> None:
        self.assertEqual(premium_text("A &amp; B"), "𝐀 &amp; 𝐁")


if __name__ == "__main__":
    unittest.main()
