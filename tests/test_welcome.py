"""Tests for public welcome message formatting and handling."""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import User

from app.handlers.welcome import create_welcome_router, render_welcome_message


class WelcomeMessageTests(unittest.TestCase):
    def test_renders_member_mention_and_group_title(self) -> None:
        member = User(id=12345, is_bot=False, first_name="Ari")
        message = render_welcome_message("Anime Fans", [member])
        self.assertIn("𝐀𝐧𝐢𝐦𝐞 𝐅𝐚𝐧𝐬", message)
        self.assertIn('tg://user?id=12345', message)
        self.assertIn("𝐀𝐫𝐢", message)
        self.assertIn("𝐠𝐫𝐨𝐮𝐩 𝐫𝐮𝐥𝐞𝐬", message)

    def test_escapes_html_in_group_and_member_names(self) -> None:
        member = User(id=12345, is_bot=False, first_name="<Admin>")
        message = render_welcome_message("<Group>", [member])
        self.assertIn("&lt;𝐆𝐫𝐨𝐮𝐩&gt;", message)
        self.assertIn("&lt;𝐀𝐝𝐦𝐢𝐧&gt;", message)
        self.assertNotIn("<Group>", message)

    def test_handles_multiple_members(self) -> None:
        members = [
            User(id=1, is_bot=False, first_name="One"),
            User(id=2, is_bot=False, first_name="Two"),
        ]
        message = render_welcome_message("Anime Fans", members)
        self.assertIn("𝐎𝐧𝐞", message)
        self.assertIn("𝐓𝐰𝐨", message)
        self.assertIn("𝐧𝐞𝐰 𝐦𝐞𝐦𝐛𝐞𝐫𝐬", message)

    def test_handles_missing_group_title(self) -> None:
        member = User(id=12345, is_bot=False, first_name="Ari")
        message = render_welcome_message("", [member])
        self.assertIn("𝐭𝐡𝐢𝐬 𝐠𝐫𝐨𝐮𝐩", message)


class WelcomeRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_router_registers_join_handler(self) -> None:
        router = create_welcome_router()
        self.assertEqual(router.name, "welcome")
        self.assertEqual(len(router.message.handlers), 2)
        # The first handler processes joins; the second registers ordinary group activity.

    async def test_any_group_gets_welcome_without_allowlist(self) -> None:
        router = create_welcome_router()
        handler = router.message.handlers[0].callback
        message = MagicMock()
        message.chat.id = -100999
        message.chat.title = "Unlisted Community"
        message.new_chat_members = [
            User(id=12345, is_bot=False, first_name="Test")
        ]
        message.answer = AsyncMock()

        with patch(
            "app.handlers.welcome.start_member_verification",
            new_callable=AsyncMock,
        ) as start_verification:
            await handler(message)

        message.answer.assert_awaited_once()
        self.assertIn("𝐔𝐧𝐥𝐢𝐬𝐭𝐞𝐝 𝐂𝐨𝐦𝐦𝐮𝐧𝐢𝐭𝐲", message.answer.await_args.args[0])
        start_verification.assert_awaited_once_with(message, message.new_chat_members)

    async def test_bot_accounts_are_not_welcomed(self) -> None:
        router = create_welcome_router()
        handler = router.message.handlers[0].callback
        message = MagicMock()
        message.chat.id = -100123
        message.chat.title = "Anime Fans"
        message.new_chat_members = [
            User(id=12345, is_bot=True, first_name="Helper")
        ]
        message.answer = AsyncMock()

        await handler(message)

        message.answer.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
