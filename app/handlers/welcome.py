"""Welcome new members in explicitly configured community groups."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message, User
from aiogram.utils.html import quote

logger = logging.getLogger(__name__)


def render_welcome_message(chat_title: str, members: list[User]) -> str:
    """Build a safe HTML welcome message for one or more newly joined members."""
    safe_chat_title = quote(chat_title or "Ani World 剣")
    mentions = [
        f'<a href="tg://user?id={member.id}">{quote(member.full_name)}</a>'
        for member in members
    ]
    joined_names = ", ".join(mentions)
    count = len(members)
    noun = "member" if count == 1 else "members"
    return (
        f"⚔️ Welcome to <b>{safe_chat_title}</b>!\n\n"
        f"Welcome {joined_names}! You are our new {noun}. 🎉\n"
        "Please read the community rules with /rules and keep the chat friendly."
    )


def create_welcome_router(allowed_chat_ids: tuple[int, ...]) -> Router:
    """Create a router that welcomes members only in the configured allowlist."""
    router = Router(name="welcome")

    @router.message(F.new_chat_members)
    async def welcome_new_members(message: Message) -> None:
        if message.chat.id not in allowed_chat_ids:
            logger.debug("Ignoring join event in unconfigured chat_id=%s", message.chat.id)
            return

        members = [
            member
            for member in (message.new_chat_members or [])
            if not member.is_bot
        ]
        if not members:
            return

        text = render_welcome_message(message.chat.title or "", members)
        await message.answer(text)
        logger.info(
            "Welcomed %s member(s) in chat_id=%s",
            len(members),
            message.chat.id,
        )

    return router
