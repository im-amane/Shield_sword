"""Tests that normal group media is not blanket-deleted."""
import unittest

from app.handlers.copyright import MEDIA_TYPES, create_copyright_router


class CopyrightRouterTests(unittest.TestCase):
    def test_group_media_is_not_registered_for_blanket_deletion(self) -> None:
        router = create_copyright_router()
        self.assertEqual(router.name, "copyright")
        self.assertEqual(len(router.message.handlers), 1)  # private /channelprotect command only
        self.assertEqual(len(router.edited_message.handlers), 0)
        self.assertEqual(len(router.channel_post.handlers), 1)
        self.assertEqual(len(router.edited_channel_post.handlers), 1)
        self.assertIn("video", MEDIA_TYPES)
        self.assertIn("document", MEDIA_TYPES)
        self.assertIn("photo", MEDIA_TYPES)
        self.assertNotIn("text", MEDIA_TYPES)


if __name__ == "__main__":
    unittest.main()
