"""Automatic group raid detection based on rapid human-member joins."""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, User

logger = logging.getLogger(__name__)

# 500 human accounts joining within 10 minutes activates a 30-minute raid mode.
RAID_JOIN_THRESHOLD = 500
RAID_WINDOW_SECONDS = 10 * 60
RAID_MODE_SECONDS = 30 * 60
_join_events: dict[int, deque[float]] = defaultdict(deque)
_raid_until: dict[int, float] = {}


def record_join_activity(
    chat_id: int,
    members: list[User],
    now: float | None = None,
) -> tuple[bool, int, bool]:
    """Record a join batch; return (newly_activated, count_in_window, is_active)."""
    timestamp = time.monotonic() if now is None else now
    events = _join_events[chat_id]
    while events and timestamp - events[0] > RAID_WINDOW_SECONDS:
        events.popleft()

    human_count = sum(1 for member in members if not member.is_bot)
    events.extend([timestamp] * human_count)

    # Remove expired state and stale chat counters to keep memory bounded.
    active_until = _raid_until.get(chat_id, 0.0)
    if active_until <= timestamp:
        _raid_until.pop(chat_id, None)
        active_until = 0.0

    for stale_chat_id, stale_events in list(_join_events.items()):
        while stale_events and timestamp - stale_events[0] > RAID_WINDOW_SECONDS:
            stale_events.popleft()
        if not stale_events and stale_chat_id != chat_id:
            _join_events.pop(stale_chat_id, None)

    count = len(events)
    newly_activated = count >= RAID_JOIN_THRESHOLD and active_until <= timestamp
    if newly_activated:
        _raid_until[chat_id] = timestamp + RAID_MODE_SECONDS
        logger.warning(
            "Raid mode activated chat_id=%s joins=%s window_seconds=%s duration_seconds=%s",
            chat_id,
            count,
            RAID_WINDOW_SECONDS,
            RAID_MODE_SECONDS,
        )

    return newly_activated, count, newly_activated or active_until > timestamp


def is_raid_mode_active(chat_id: int, now: float | None = None) -> bool:
    """Return whether raid mode is currently active for a chat."""
    timestamp = time.monotonic() if now is None else now
    until = _raid_until.get(chat_id, 0.0)
    if until <= timestamp:
        _raid_until.pop(chat_id, None)
        return False
    return True


def reset_raid_state() -> None:
    """Clear in-memory raid state; intended for isolated tests."""
    _join_events.clear()
    _raid_until.clear()


def disable_raid_mode(chat_id: int) -> bool:
    """Disable raid mode for one chat; return whether it was active."""
    return _raid_until.pop(chat_id, None) is not None


def raid_status(chat_id: int, now: float | None = None) -> tuple[bool, int, int]:
    """Return (active, joins_in_window, seconds_remaining) for one chat."""
    timestamp = time.monotonic() if now is None else now
    events = _join_events.get(chat_id, deque())
    while events and timestamp - events[0] > RAID_WINDOW_SECONDS:
        events.popleft()
    if not events:
        _join_events.pop(chat_id, None)
    until = _raid_until.get(chat_id, 0.0)
    if until <= timestamp:
        _raid_until.pop(chat_id, None)
        return False, len(events), 0
    return True, len(events), max(0, int(until - timestamp))


def create_raid_router(owner_id: int | None = None) -> Router:
    """Create owner-only raid status and emergency disable commands."""
    from aiogram.filters import Command
    from aiogram.types import Message

    from app.security.owner import is_owner

    router = Router(name="raid_protection")

    @router.message(Command("raidstatus"))
    async def raid_status_command(message: Message) -> None:
        if not message.from_user or not is_owner(message.from_user.id, owner_id):
            await message.answer("🔒 <b>Owner Access Only</b>\n\nRaid controls are reserved for the bot owner. 👑")
            return
        active, count, remaining = raid_status(message.chat.id)
        state = "🚨 ACTIVE" if active else "🟢 INACTIVE"
        await message.answer(
            "🛡️ <b>Raid Shield Status</b>\n\n"
            f"Current mode: <b>{state}</b>\n"
            f"Recent human joins: <b>{count}/{RAID_JOIN_THRESHOLD}</b>\n"
            f"Time remaining: <b>{remaining // 60}m {remaining % 60}s</b>\n\n"
            "<i>Your community security overview.</i>"
        )

    @router.message(Command("raidoff"))
    async def raid_off_command(message: Message) -> None:
        if not message.from_user or not is_owner(message.from_user.id, owner_id):
            await message.answer("🔒 <b>Owner Access Only</b>\n\nThis control is reserved for the bot owner. 👑")
            return
        if disable_raid_mode(message.chat.id):
            await message.answer("🟢 <b>All Clear!</b>\n\nRaid Shield has been disabled by the owner.\nYour community is back to normal mode. 💚")
        else:
            await message.answer("😌 <b>All Clear!</b>\n\nRaid Shield is already inactive. Your group is in normal mode. 💚")

    return router


async def announce_raid_activation(
    message: Message,
    owner_id: int | None,
    join_count: int,
) -> None:
    """Notify the group and owner when the rapid-join threshold is crossed."""
    chat_title = message.chat.title or "Telegram group"
    group_notice = (
        "🚨 <b>RAID ALERT · SHIELD ACTIVATED</b>\n\n"
        f"<b>{RAID_JOIN_THRESHOLD}</b> human members joined within "
        f"<b>{RAID_WINDOW_SECONDS // 60} minutes</b>.\n\n"
        "🛡️ New members must complete verification before chatting.\n"
        "✅ Existing members are not restricted.\n\n"
        "<i>Ani World is keeping watch.</i>"
    )
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
            "🚨 <b>Group Security Alert</b>\n\n"
            f"Group: {chat_title}\n"
            f"Chat ID: <code>{message.chat.id}</code>\n"
            f"Recent human joins: <b>{join_count}</b> in "
            f"{RAID_WINDOW_SECONDS // 60} minutes\n"
            f"Raid mode is active for {RAID_MODE_SECONDS // 60} minutes. "
            "New members continue to face verification.",
        )
    except TelegramAPIError:
        logger.exception("Could not send raid alert to owner_id=%s", owner_id)
