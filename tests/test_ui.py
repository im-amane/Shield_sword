"""Tests for the global inline Close button convention."""
import unittest

from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.ui import outgoing_ui_middleware, with_close_button


class GlobalInlineUITests(unittest.IsolatedAsyncioTestCase):
    async def test_adds_close_button_to_plain_replies(self):
        method = SendMessage(chat_id=123, text="Hello")
        seen = {}

        async def make_request(bot, outgoing):
            seen["method"] = outgoing
            return "sent"

        result = await outgoing_ui_middleware(make_request, object(), method)
        self.assertEqual(result, "sent")
        self.assertEqual(
            seen["method"].reply_markup.inline_keyboard[-1][0].callback_data,
            "ui:close",
        )
        self.assertEqual(
            seen["method"].reply_markup.inline_keyboard[-1][0].text,
            "✖️ Close",
        )

    async def test_preserves_existing_buttons_and_appends_close(self):
        original = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Open", callback_data="open:item")
        ]])
        method = EditMessageText(
            chat_id=123, message_id=5, text="Updated", reply_markup=original
        )

        async def make_request(bot, outgoing):
            return outgoing.reply_markup

        result = await outgoing_ui_middleware(make_request, object(), method)
        self.assertEqual(result.inline_keyboard[0][0].callback_data, "open:item")
        self.assertEqual(result.inline_keyboard[-1][0].callback_data, "ui:close")

    def test_does_not_duplicate_existing_close_action(self):
        original = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Close", callback_data="ui:close")
        ]])
        updated = with_close_button(original)
        self.assertEqual(len(updated.inline_keyboard), 1)

    def test_keeps_legacy_owner_panel_close_without_duplicate(self):
        original = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Close", callback_data="owner_panel:close")
        ]])
        updated = with_close_button(original)
        self.assertEqual(len(updated.inline_keyboard), 1)


if __name__ == "__main__":
    unittest.main()
