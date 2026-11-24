"""Welcome new human members, detect raids, and start their verification."""
from __future__ import annotations

import logging
import time
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
from app.handlers.card_helpers import send_category_card
from app.storage import (
    get_raid_join_count, has_recent_security_incident, record_security_incident,
    register_group, record_member_join,
)

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
    return premium_text(
        f"🌸 <b>Welcome to {safe_chat_title}!</b>\n\n"
        f"Hello {joined_names}! Welcome to the community. ❤️\n\n"
        "Please take a moment to read the group rules, respect other members "
        "and keep conversations safe and on-topic.\n\n"
        "🛡️ <b>Sentinel is protecting this community.</b>\n"
        "New members must complete the verification challenge before chatting. "
        "Spam, harmful links and unsafe text may be moderated automatically.\n\n"
        "<i>Normal photos, videos and other media are not blanket-deleted.</i>\n"
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
        joined_members = list(message.new_chat_members or [])
        if not joined_members:
            return

        chat_title = message.chat.title or "Telegram group"
        register_group(message.chat.id, chat_title)
        members = [member for member in joined_members if not member.is_bot]
        for bot_member in (member for member in joined_members if member.is_bot):
            record_security_incident(
                message.chat.id, chat_title, "bot_join", "medium",
                bot_member.id, bot_member.username, bot_member.full_name,
                "Bot account joined; review whether it is trusted.",
            )
        if not members:
            return
        for member in members:
            record_member_join(
                message.chat.id, chat_title, member.id,
                member.username, member.full_name,
            )
        await send_category_card(message, "welcome", "New Member Welcome", "Verification and community rules")
        await message.answer(render_welcome_message(chat_title, members))

        newly_activated, join_count, _raid_active = record_join_activity(
            message.chat.id,
            members,
        )
        if newly_activated:
            await announce_raid_activation(message, owner_id, join_count)

        # Early warning only: a short join burst alerts the owner but does not
        # automatically restrict members or switch the group into lockdown.
        surge_count = get_raid_join_count(message.chat.id, time.time(), 60)
        if surge_count >= 25 and not has_recent_security_incident(
            message.chat.id, "join_surge", 600
        ):
            record_security_incident(
                message.chat.id, chat_title, "join_surge", "high",
                details=f"{surge_count} human joins within 60 seconds; monitoring alert only",
            )
            if owner_id is not None:
                try:
                    await message.bot.send_message(
                        owner_id,
                        premium_text(
                            "⚠️ <b>Unusual Join Surge</b>\n\n"
                            f"Group: {escape(chat_title)}\n"
                            f"Chat ID: <code>{message.chat.id}</code>\n"
                            f"Human joins in the last minute: <b>{surge_count}</b>\n\n"
                            "This is an early-warning alert only. No members were automatically banned."
                        ),
                    )
                except TelegramAPIError:
                    logger.exception("Could not deliver join-surge alert to owner.")

        # Verification already applies to every new human member, including during raid mode.
        await start_member_verification(message, members)
        logger.info(
            "Welcomed %s member(s) in chat_id=%s",
            len(members),
            message.chat.id,
        )

    return router
