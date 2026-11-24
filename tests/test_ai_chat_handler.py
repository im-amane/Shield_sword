"""End-to-end handler tests for mention-driven Guardian AI Chat."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from aiogram.dispatcher.event.bases import SkipHandler

from app.handlers.ai_chat import create_ai_chat_router
from app.nvidia_nim import NimResponse


class GuardianAIChatHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = SimpleNamespace(
            guardian=SimpleNamespace(classify=AsyncMock()),
            chat=SimpleNamespace(generate=Mock(return_value=NimResponse("Hello!", 120))),
        )
        self.engine.guardian.classify.side_effect = [
            {"unsafe": False, "categories": ""},
            {"unsafe": False, "categories": ""},
        ]
        self.create_engine = patch(
            "app.handlers.ai_chat.GuardianAIEngine.create",
            return_value=self.engine,
        )
        self.create_engine.start()
        self.addCleanup(self.create_engine.stop)
        self.router = create_ai_chat_router("chat-key", "guardian-key", "chat-model", "safety-model")
        self.handler = self.router.message.handlers[0].callback
        self.message = SimpleNamespace(
            from_user=SimpleNamespace(id=123, is_bot=False),
            chat=SimpleNamespace(id=-100123),
            text="Guardian, hello!",
            caption=None,
            reply_to_message=None,
            bot=SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(id=999))),
            answer=AsyncMock(),
        )

    async def test_unmentioned_group_message_is_ignored(self):
        self.message.text = "hello everyone"
        with self.assertRaises(SkipHandler):
            await self.handler(self.message)
        self.engine.guardian.classify.assert_not_awaited()
        self.engine.chat.generate.assert_not_called()

    async def test_command_is_ignored_even_if_it_contains_guardian_keyword(self):
        self.message.text = "/guardian help"
        with self.assertRaises(SkipHandler):
            await self.handler(self.message)
        self.engine.guardian.classify.assert_not_awaited()

    async def test_unsafe_input_never_reaches_chat_model(self):
        self.engine.guardian.classify.side_effect = [{"unsafe": True, "categories": "Threat"}]
        await self.handler(self.message)
        self.engine.chat.generate.assert_not_called()
        self.message.answer.assert_not_awaited()

    async def test_unavailable_input_safety_engine_fails_closed(self):
        self.engine.guardian.classify.side_effect = [None]
        await self.handler(self.message)
        self.engine.chat.generate.assert_not_called()
        self.message.answer.assert_not_awaited()

    async def test_safe_input_and_output_deliver_html_escaped_reply(self):
        self.engine.chat.generate.return_value = NimResponse("<b>Hi</b> & welcome", 120)
        await self.handler(self.message)
        self.assertEqual(self.engine.guardian.classify.await_count, 2)
        self.engine.chat.generate.assert_called_once()
        sent_text = self.message.answer.await_args.args[0]
        self.assertIn("&lt;", sent_text)
        self.assertIn("&amp;", sent_text)
        self.assertNotIn("<b>Hi</b>", sent_text)

    async def test_unsafe_generated_output_is_withheld(self):
        self.engine.guardian.classify.side_effect = [
            {"unsafe": False, "categories": ""},
            {"unsafe": True, "categories": "Harassment"},
        ]
        await self.handler(self.message)
        self.engine.chat.generate.assert_called_once()
        self.message.answer.assert_not_awaited()

    async def test_unavailable_output_safety_engine_fails_closed(self):
        self.engine.guardian.classify.side_effect = [
            {"unsafe": False, "categories": ""},
            None,
        ]
        await self.handler(self.message)
        self.engine.chat.generate.assert_called_once()
        self.message.answer.assert_not_awaited()

    async def test_chat_provider_error_does_not_post_reply(self):
        self.engine.chat.generate.return_value = NimResponse(None, 100, "http_429")
        await self.handler(self.message)
        self.assertEqual(self.engine.guardian.classify.await_count, 1)
        self.message.answer.assert_not_awaited()

    async def test_reply_to_guardian_activates_without_keyword(self):
        self.message.text = "Are you there?"
        self.message.reply_to_message = SimpleNamespace(
            from_user=SimpleNamespace(id=999)
        )
        await self.handler(self.message)
        self.message.bot.get_me.assert_awaited_once()
        self.engine.chat.generate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
