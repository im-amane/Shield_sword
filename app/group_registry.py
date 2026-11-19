"""Observe group messages so the owner panel can discover communities."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from app.storage import register_group


class GroupRegistryMiddleware(BaseMiddleware):
    """Register each group whose message updates are visible to the bot.

    This runs before router filters, so commands and service messages count too.
    Telegram privacy mode still limits which ordinary messages the bot receives.
    """

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        chat = getattr(event, "chat", None)
        if chat is not None and chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            register_group(chat.id, chat.title or "Telegram group")
        return await handler(event, data)
