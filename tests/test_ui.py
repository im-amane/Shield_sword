"""Tests that global UI middleware never injects unrelated buttons."""
import unittest

from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.ui import outgoing_ui_middleware


class GlobalInlineUITests(unittest.IsolatedAsyncioTestCase):
    async def test_plain_replies_remain_without_inline_keyboard(self):
        method = SendMessage(chat_id=123, text="Hello")

        async def make_request(bot, outgoing):
            return outgoing

        result = await outgoing_ui_middleware(make_request, object(), method)
        self.assertIsNone(result.reply_markup)

    async def test_existing_keyboard_is_preserved_exactly(self):
        original = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Back", callback_data="back")
        ]])
        method = EditMessageText(
            chat_id=123, message_id=5, text="Updated", reply_markup=original
        )

        async def make_request(bot, outgoing):
            return outgoing.reply_markup

        result = await outgoing_ui_middleware(make_request, object(), method)
        self.assertEqual(result, original)
        self.assertEqual(len(result.inline_keyboard), 1)
        self.assertEqual(result.inline_keyboard[0][0].callback_data, "back")

    async def test_explicit_close_button_is_not_modified(self):
        original = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Close", callback_data="ui:close")
        ]])
        method = SendMessage(chat_id=123, text="Closable", reply_markup=original)

        async def make_request(bot, outgoing):
            return outgoing.reply_markup

        result = await outgoing_ui_middleware(make_request, object(), method)
        self.assertEqual(result, original)


if __name__ == "__main__":
    unittest.main()
