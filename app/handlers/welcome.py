"""Welcome new human members and start their verification."""
from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.types import Message, User

from app.handlers.verification import start_member_verification

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
        f"👋 Welcome to <b>{safe_chat_title}</b>!\n\n"
        f"Welcome {joined_names}! You are our new {noun}. 🎉\n"
        "Please follow the group rules and keep the conversation friendly."
    )


def create_welcome_router(_legacy_allowed_chat_ids: tuple[int, ...] | None = None) -> Router:
    """Create the shared public join handler for welcome and verification."""
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
        await start_member_verification(message, members)
        logger.info(
            "Welcomed %s member(s) in chat_id=%s",
            len(members),
            message.chat.id,
        )

    return router
