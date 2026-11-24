"""Observe group messages so the owner panel can discover communities."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from app.storage import record_member_profile, register_group


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
            member = getattr(event, "from_user", None)
            if member is not None and not getattr(member, "is_bot", False):
                record_member_profile(
                    chat.id, member.id, member.first_name or "",
                    member.last_name or "", member.username or "",
                )
        return await handler(event, data)
