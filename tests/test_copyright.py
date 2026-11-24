"""Regression tests for the non-destructive media policy."""
import unittest

from app.handlers.copyright import create_copyright_router


class CopyrightRouterTests(unittest.TestCase):
    def test_no_group_or_channel_media_deletion_handlers_are_registered(self):
        router = create_copyright_router()
        self.assertEqual(router.name, "media_policy")
        self.assertEqual(len(router.message.handlers), 0)
        self.assertEqual(len(router.edited_message.handlers), 0)
        self.assertEqual(len(router.channel_post.handlers), 0)
        self.assertEqual(len(router.edited_channel_post.handlers), 0)


if __name__ == "__main__":
    unittest.main()
