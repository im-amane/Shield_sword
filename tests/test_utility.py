"""Tests for Telegram user profile card lookup."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.enums import ChatType
from app.handlers.utility import create_utility_router


class UtilityProfileCardTests(unittest.IsolatedAsyncioTestCase):
    async def test_id_command_builds_profile_card_with_group_context(self):
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
            answer=AsyncMock(), answer_photo=AsyncMock(),
        )
        with patch("app.handlers.utility.record_member_profile") as record, \
             patch("app.handlers.utility.get_member_profile_history", return_value=[
                 {"first_name":"Ari","last_name":"Example","username":"ari"}
             ]), patch("app.handlers.utility._profile_photo", new=AsyncMock(return_value=None)), \
             patch("app.handlers.utility.render_user_profile_card", return_value=b"png-data") as render:
            await handler(message)
        record.assert_called_once_with(-100987, 12345, "Ari", "Example", "ari")
        render.assert_called_once()
        args = render.call_args.kwargs
        self.assertEqual(args["user_id"], 12345)
        self.assertEqual(args["current_chat_id"], -100987)
        self.assertEqual(args["group_id"], -100987)
        message.answer_photo.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
