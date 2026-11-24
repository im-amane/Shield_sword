"""Unit tests for mention-driven AI chat cooldowns."""
import unittest

from app.ai_engine import GuardianAIEngine
from app.ai_chat import CHAT_SYSTEM_PROMPT
from app.handlers.ai_chat import AiChatLimiter, _TRIGGER


class AiChatLimiterTests(unittest.TestCase):
    def test_chat_prompt_matches_real_capabilities_and_limits(self):
        self.assertIn("do not automatically answer every group message", CHAT_SYSTEM_PROMPT)
        self.assertIn("not blanket-deleted", CHAT_SYSTEM_PROMPT)
        self.assertIn("do not have a verified copyright ownership", CHAT_SYSTEM_PROMPT)
        self.assertIn("do not have persistent conversational memory", CHAT_SYSTEM_PROMPT)
        self.assertIn("Never invent commands", CHAT_SYSTEM_PROMPT)

    def test_only_explicit_guardian_mentions_match(self):
        self.assertTrue(_TRIGGER.search("Hey Guardian, are you there?"))
        self.assertTrue(_TRIGGER.search("hello @Break_mebot"))
        self.assertIsNone(_TRIGGER.search("hello everyone"))

    def test_user_group_and_global_cooldowns(self):
        limiter = AiChatLimiter()
        self.assertTrue(limiter.allow(-100, 1, now=10.0))
        self.assertFalse(limiter.allow(-100, 1, now=20.0))
        self.assertFalse(limiter.allow(-100, 2, now=11.0))
        self.assertTrue(limiter.allow(-100, 2, now=15.0))
        self.assertTrue(limiter.allow(-200, 3, now=17.0))

    def test_engine_requires_two_nonempty_credentials(self):
        with self.assertRaises(ValueError):
            GuardianAIEngine.create("", "guardian-key", "chat-model", "safety-model")
        with self.assertRaises(ValueError):
            GuardianAIEngine.create("chat-key", "", "chat-model", "safety-model")

    def test_engine_keeps_credentials_and_models_separate(self):
        engine = GuardianAIEngine.create(
            "chat-secret", "guardian-secret", "chat-model", "safety-model"
        )
        self.assertEqual(engine.chat._api_key, "chat-secret")
        self.assertEqual(engine.guardian._api_key, "guardian-secret")
        self.assertEqual(engine.chat.model, "chat-model")
        self.assertEqual(engine.guardian.model, "safety-model")


if __name__ == "__main__":
    unittest.main()
