"""Unit tests for mention-driven AI chat cooldowns."""
import unittest

from app.handlers.ai_chat import AiChatLimiter, _TRIGGER


class AiChatLimiterTests(unittest.TestCase):
    def test_only_explicit_guardian_mentions_match(self):
        self.assertTrue(_TRIGGER.search("Hey Guardian, are you there?"))
        self.assertTrue(_TRIGGER.search("hello @Break_mebot"))
        self.assertIsNone(_TRIGGER.search("hello everyone"))

    def test_user_group_and_global_cooldowns(self):
        limiter = AiChatLimiter()
        self.assertTrue(limiter.allow(-100, 1, now=10.0))
        self.assertFalse(limiter.allow(-100, 1, now=20.0))
        self.assertFalse(limiter.allow(-100, 2, now=11.0))
        self.assertTrue(limiter.allow(-100, 2, now=19.0))
        self.assertTrue(limiter.allow(-200, 3, now=22.0))


if __name__ == "__main__":
    unittest.main()
