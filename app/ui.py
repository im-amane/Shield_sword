"""Global inline UI conventions for every bot-authored reply."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import (
    EditMessageCaption, EditMessageMedia, EditMessageText,
    SendAnimation, SendAudio, SendContact, SendDice, SendDocument,
    SendGame, SendInvoice, SendLocation, SendMessage, SendPhoto,
    SendPoll, SendVenue, SendVideo, SendVoice,
)
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
)

from app.handlers.typography import premium_text

logger = logging.getLogger(__name__)

_CLOSE_BUTTON = InlineKeyboardButton(
    text="✖️ Close",
    callback_data="ui:close",
)

# Telegram methods that support inline reply_markup. Album sends are excluded
# because sendMediaGroup does not accept a reply keyboard.
_REPLY_METHODS = (
    SendMessage, SendPhoto, SendVideo, SendAnimation, SendDocument,
    SendAudio, SendVoice, SendLocation,
    SendVenue, SendContact, SendPoll, SendGame, SendInvoice,
    EditMessageText, EditMessageCaption, EditMessageMedia,
)


def with_close_button(
    markup: InlineKeyboardMarkup | None,
) -> InlineKeyboardMarkup:
    """Preserve existing inline actions and add one consistent Close action."""
    rows = [list(row) for row in markup.inline_keyboard] if markup else []
    if any(
        button.callback_data in {"ui:close", "owner_panel:close"}
        for row in rows for button in row
    ):
        return markup or InlineKeyboardMarkup(inline_keyboard=[[_CLOSE_BUTTON]])
    rows.append([_CLOSE_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def outgoing_ui_middleware(make_request, bot, method):
    """Attach a Close button to all supported outgoing bot replies and edits."""
    if isinstance(method, _REPLY_METHODS):
        markup = getattr(method, "reply_markup", None)
        if markup is None or isinstance(markup, InlineKeyboardMarkup):
            method.reply_markup = with_close_button(markup)
    return await make_request(bot, method)


def install_ui_middleware(bot) -> None:
    """Install the global outgoing UI convention on this bot session."""
    bot.session.middleware.register(outgoing_ui_middleware)


def create_ui_router() -> Router:
    router = Router(name="global_inline_ui")

    @router.callback_query(F.data == "ui:close")
    async def close_reply(callback: CallbackQuery) -> None:
        message = callback.message
        if message is None:
            await callback.answer()
            return
        # The callback belongs to this bot's own inline keyboard. Do not let a
        # forged callback delete messages authored by another account.
        if message.from_user is None or not message.from_user.is_bot:
            await callback.answer(
                premium_text("This button can only close a bot reply. 🔒"),
                show_alert=True,
            )
            return
        await callback.answer(premium_text("Closed. 👋"))
        try:
            await message.delete()
        except TelegramAPIError:
            logger.debug("Close button could not delete message_id=%s", message.message_id, exc_info=True)

    return router
