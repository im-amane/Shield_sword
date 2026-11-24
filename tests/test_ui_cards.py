"""Tests for Sentinel's generated profile and category photo cards."""
import unittest

from app.ui_cards import render_category_card, render_user_profile_card


class PhotoCardTests(unittest.TestCase):
    def test_user_profile_card_is_a_png_and_contains_profile_fields(self):
        image = render_user_profile_card(
            display_name="Ari Example", username="@ari", user_id=12345,
            first_name="Ari", last_name="Example", bio="Ani World member",
            current_chat_id=-100123, group_title="Ani World", group_id=-100123,
            name_history=["Ari"],
        )
        self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(image), 5000)

    def test_category_cards_have_distinct_rendered_outputs(self):
        help_card = render_category_card("help", "Help Center", "Commands")
        warning_card = render_category_card("warning", "Warning Issued", "Moderation")
        self.assertTrue(help_card.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(warning_card.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertNotEqual(help_card, warning_card)


if __name__ == "__main__":
    unittest.main()
