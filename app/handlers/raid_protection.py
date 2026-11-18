"""Automatic group raid detection based on rapid human-member joins."""
from __future__ import annotations

import logging
import time
from html import escape

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, User

from app.handlers.typography import premium_text
from app.storage import (
    clear_raid_data,
    clear_raid_expiry,
    get_raid_expiry,
    get_raid_join_count,
    record_raid_joins,
    set_raid_expiry,
    record_security_incident,
    record_audit_event,
)

logger = logging.getLogger(__name__)

# 500 human accounts joining within 10 minutes activates a 30-minute raid mode.
RAID_JOIN_THRESHOLD = 500
RAID_WINDOW_SECONDS = 10 * 60
RAID_MODE_SECONDS = 30 * 60


def record_join_activity(
    chat_id: int,
    members: list[User],
    now: float | None = None,
) -> tuple[bool, int, bool]:
    """Persist join activity and return (newly_activated, count, is_active)."""
    timestamp = time.time() if now is None else now
    human_count = sum(1 for member in members if not member.is_bot)
    count = record_raid_joins(
        chat_id, human_count, timestamp, RAID_WINDOW_SECONDS
    )
    active_until = get_raid_expiry(chat_id)
    if active_until <= timestamp:
        clear_raid_expiry(chat_id)
        active_until = 0.0

    newly_activated = count >= RAID_JOIN_THRESHOLD and active_until <= timestamp
    if newly_activated:
        active_until = timestamp + RAID_MODE_SECONDS
        set_raid_expiry(chat_id, active_until)
        record_security_incident(
            chat_id, "Telegram group", "raid_detected", "critical",
            details=f"{count} human joins within {RAID_WINDOW_SECONDS}s",
        )
        record_audit_event(
            chat_id, "raid_detected", None, None,
            f"{count} human joins within {RAID_WINDOW_SECONDS}s",
        )
        logger.warning(
            "Raid mode activated chat_id=%s joins=%s window_seconds=%s duration_seconds=%s",
            chat_id, count, RAID_WINDOW_SECONDS, RAID_MODE_SECONDS,
        )
    return newly_activated, count, newly_activated or active_until > timestamp


def is_raid_mode_active(chat_id: int, now: float | None = None) -> bool:
    """Return whether raid mode is currently active for a chat."""
    timestamp = time.time() if now is None else now
    until = get_raid_expiry(chat_id)
    if until <= timestamp:
        clear_raid_expiry(chat_id)
        return False
    return True


def reset_raid_state() -> None:
    """Clear persisted raid state; intended for isolated tests."""
    clear_raid_data()


def disable_raid_mode(chat_id: int) -> bool:
    """Disable raid mode for one chat; return whether it was active."""
    return clear_raid_expiry(chat_id)


def raid_status(chat_id: int, now: float | None = None) -> tuple[bool, int, int]:
    """Return (active, joins_in_window, seconds_remaining) for one chat."""
    timestamp = time.time() if now is None else now
    count = get_raid_join_count(chat_id, timestamp, RAID_WINDOW_SECONDS)
    until = get_raid_expiry(chat_id)
    if until <= timestamp:
        clear_raid_expiry(chat_id)
        return False, count, 0
    return True, count, max(0, int(until - timestamp))


def create_raid_router(owner_id: int | None = None) -> Router:
    """Create owner-only raid status and emergency disable commands."""
    from aiogram.filters import Command
    from aiogram.types import Message

    from app.security.owner import is_owner

    router = Router(name="raid_protection")

    @router.message(Command("raidstatus"))
    async def raid_status_command(message: Message) -> None:
        if not message.from_user or not is_owner(message.from_user.id, owner_id):
            await message.answer(premium_text("🔒 <b>Owner Access Only</b>\n\nRaid controls are reserved for the bot owner. 👑"))
            return
        active, count, remaining = raid_status(message.chat.id)
        state = "🚨 ACTIVE" if active else "🟢 INACTIVE"
        await message.answer(premium_text(
            "🛡️ <b>Raid Shield Status</b>\n\n"
            f"Current mode: <b>{state}</b>\n"
            f"Recent human joins: <b>{count}/{RAID_JOIN_THRESHOLD}</b>\n"
            f"Time remaining: <b>{remaining // 60}m {remaining % 60}s</b>\n\n"
            "<i>Your community security overview.</i>"
        ))

    @router.message(Command("raidoff"))
    async def raid_off_command(message: Message) -> None:
        if not message.from_user or not is_owner(message.from_user.id, owner_id):
            await message.answer(premium_text("🔒 <b>Owner Access Only</b>\n\nThis control is reserved for the bot owner. 👑"))
            return
        if disable_raid_mode(message.chat.id):
            await message.answer(premium_text("🟢 <b>All Clear!</b>\n\nRaid Shield has been disabled by the owner.\nYour community is back to normal mode. 💚"))
        else:
            await message.answer(premium_text("😌 <b>All Clear!</b>\n\nRaid Shield is already inactive. Your group is in normal mode. 💚"))

    return router


async def announce_raid_activation(
    message: Message,
    owner_id: int | None,
    join_count: int,
) -> None:
    """Notify the group and owner when the rapid-join threshold is crossed."""
    chat_title = message.chat.title or "Telegram group"
    group_notice = premium_text((
        "🚨 <b>RAID ALERT · SHIELD ACTIVATED</b>\n\n"
        f"<b>{RAID_JOIN_THRESHOLD}</b> human members joined within "
        f"<b>{RAID_WINDOW_SECONDS // 60} minutes</b>.\n\n"
        "🛡️ New members must complete verification before chatting.\n"
        "✅ Existing members are not restricted.\n\n"
        "<i>Ani World is keeping watch.</i>"
    ))
    try:
        await message.answer(group_notice)
    except TelegramAPIError:
        logger.exception("Could not announce raid mode in chat_id=%s", message.chat.id)

    if owner_id is None:
        logger.warning("Raid detected but OWNER_ID is not configured; chat_id=%s", message.chat.id)
        return

    try:
        await message.bot.send_message(
            owner_id,
            premium_text(
                "🚨 <b>Group Security Alert</b>\n\n"
                f"Group: {escape(chat_title)}\n"
                f"Chat ID: <code>{message.chat.id}</code>\n"
                f"Recent human joins: <b>{join_count}</b> in "
                f"{RAID_WINDOW_SECONDS // 60} minutes\n"
                f"Raid mode is active for {RAID_MODE_SECONDS // 60} minutes. "
                "New members continue to face verification."
            ),
        )
    except TelegramAPIError:
        logger.exception("Could not send raid alert to owner_id=%s", owner_id)
