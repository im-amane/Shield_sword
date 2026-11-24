"""Global inline UI conventions for every bot-authored reply."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import (
    EditMessageCaption, EditMessageMedia, EditMessageText,
    SendAnimation, SendAudio, SendContact, SendDocument,
    SendGame, SendInvoice, SendLocation, SendMessage, SendPhoto,
    SendPoll, SendVenue, SendVideo, SendVoice,
)
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
)

from app.handlers.typography import premium_text

logger = logging.getLogger(__name__)

async def outgoing_ui_middleware(make_request, bot, method):
    """Pass outgoing Telegram methods through unchanged.

    Close actions are opt-in and must be added by the screen that owns them;
    a global middleware must never alter unrelated keyboards or plain replies.
    """
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
