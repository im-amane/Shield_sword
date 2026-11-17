"""Tests for welcome message formatting and group allowlisting."""
import unittest
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import User

from app.handlers.welcome import create_welcome_router, render_welcome_message


class WelcomeMessageTests(unittest.TestCase):
    def test_renders_member_mention_and_rules_instruction(self) -> None:
        member = User(id=12345, is_bot=False, first_name="Ari")
        message = render_welcome_message("Ani World 剣", [member])
        self.assertIn("Ani World 剣", message)
        self.assertIn('tg://user?id=12345', message)
        self.assertIn("Ari", message)
        self.assertIn("/rules", message)

    def test_escapes_html_in_chat_and_member_names(self) -> None:
        member = User(id=12345, is_bot=False, first_name="<Admin>")
        message = render_welcome_message("<Group>", [member])
        self.assertIn("&lt;Group&gt;", message)
        self.assertIn("&lt;Admin&gt;", message)
        self.assertNotIn("<Group>", message)

    def test_handles_multiple_members(self) -> None:
        members = [
            User(id=1, is_bot=False, first_name="One"),
            User(id=2, is_bot=False, first_name="Two"),
        ]
        message = render_welcome_message("Ani World", members)
        self.assertIn("One", message)
        self.assertIn("Two", message)
        self.assertIn("new members", message)


class WelcomeRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_router_is_created_with_allowlist(self) -> None:
        router = create_welcome_router((-100123,))
        self.assertEqual(router.name, "welcome")
        self.assertEqual(len(router.message.handlers), 1)

    async def test_unconfigured_chat_is_not_processed(self) -> None:
        router = create_welcome_router((-100123,))
        handler = router.message.handlers[0].callback
        message = MagicMock()
        message.chat.id = -100999
        message.new_chat_members = [
            User(id=12345, is_bot=False, first_name="Test")
        ]
        message.answer = AsyncMock()

        await handler(message)

        message.answer.assert_not_awaited()

    async def test_configured_chat_gets_welcome(self) -> None:
        router = create_welcome_router((-100123,))
        handler = router.message.handlers[0].callback
        message = MagicMock()
        message.chat.id = -100123
        message.chat.title = "Ani World"
        message.new_chat_members = [
            User(id=12345, is_bot=False, first_name="Test")
        ]
        message.answer = AsyncMock()

        await handler(message)

        message.answer.assert_awaited_once()
        self.assertIn("/rules", message.answer.await_args.args[0])

    async def test_bot_accounts_are_not_welcomed(self) -> None:
        router = create_welcome_router((-100123,))
        handler = router.message.handlers[0].callback
        message = MagicMock()
        message.chat.id = -100123
        message.chat.title = "Ani World"
        message.new_chat_members = [
            User(id=12345, is_bot=True, first_name="Helper")
        ]
        message.answer = AsyncMock()

        await handler(message)

        message.answer.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
