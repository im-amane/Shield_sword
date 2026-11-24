"""Tests for plain-text Telegram ID lookup."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.enums import ChatType
from app.handlers.utility import create_utility_router


class UtilityIdTests(unittest.IsolatedAsyncioTestCase):
    async def test_id_command_returns_user_chat_and_group_ids_as_text(self):
        router = create_utility_router()
        handler = router.message.handlers[0].callback
        member = SimpleNamespace(
            id=12345, first_name="Ari", last_name="Example", username="ari",
            full_name="Ari Example", is_bot=False,
        )
        message = SimpleNamespace(
            text="/id", reply_to_message=None, from_user=member,
            chat=SimpleNamespace(id=-100987, title="Ani World", type=ChatType.SUPERGROUP),
            bot=SimpleNamespace(get_chat=AsyncMock(return_value=SimpleNamespace(
                bio="Community member", first_name="Ari", last_name="Example", username="ari"
            ))),
            answer=AsyncMock(),
        )
        with patch("app.handlers.utility.record_member_profile") as record:
            await handler(message)
        record.assert_called_once_with(-100987, 12345, "Ari", "Example", "ari")
        message.answer.assert_awaited_once()
        text = message.answer.await_args.args[0]
        self.assertIn("User ID:", text)
        self.assertIn("12345", text)
        self.assertIn("Chat ID:", text)
        self.assertIn("-100987", text)
        self.assertIn("Group ID:", text)


if __name__ == "__main__":
    unittest.main()
