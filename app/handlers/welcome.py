"""Welcome new human members, detect raids, and start their verification."""
from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, User

from app.handlers.raid_protection import (
    announce_raid_activation,
    record_join_activity,
)
from app.handlers.verification import start_member_verification
from app.handlers.typography import premium_text

logger = logging.getLogger(__name__)


def render_welcome_message(chat_title: str, members: list[User]) -> str:
    """Build a safe HTML welcome message for one or more newly joined members."""
    safe_chat_title = escape(chat_title or "this group", quote=True)
    mentions = [
        f'<a href="tg://user?id={member.id}">{escape(member.full_name, quote=True)}</a>'
        for member in members
    ]
    joined_names = ", ".join(mentions)
    count = len(members)
    noun = "member" if count == 1 else "members"
    return (
        f"🌸 <b>Welcome to {safe_chat_title}!</b>\n\n"
        f"Hey {joined_names}, we're happy to have you here! ❤️\n\n"
        "Make yourself comfortable, check the group rules, "
        "keep the vibes positive and enjoy your time with everyone! ✨\n\n"
        "⚔️ <b>Ani World 剣</b>"
    )


def create_welcome_router(
    _legacy_allowed_chat_ids: tuple[int, ...] | None = None,
    owner_id: int | None = None,
) -> Router:
    """Create the shared public join handler for welcome, raid detection, and verification."""
    router = Router(name="welcome")

    @router.message(F.new_chat_members)
    async def welcome_new_members(message: Message) -> None:
        members = [
            member
            for member in (message.new_chat_members or [])
            if not member.is_bot
        ]
        if not members:
            return

        await message.answer(render_welcome_message(message.chat.title or "", members))

        newly_activated, join_count, _raid_active = record_join_activity(
            message.chat.id,
            members,
        )
        if newly_activated:
            await announce_raid_activation(message, owner_id, join_count)

        # Verification already applies to every new human member, including during raid mode.
        await start_member_verification(message, members)
        logger.info(
            "Welcomed %s member(s) in chat_id=%s",
            len(members),
            message.chat.id,
        )

    return router
