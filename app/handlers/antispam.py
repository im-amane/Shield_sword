"""Basic anti-spam and flood protection for group chats."""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatPermissions, Message

from app.security.owner import is_owner
from app.handlers.typography import premium_text
from app.storage import record_audit_event, record_security_incident, register_group

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 8
MAX_MESSAGES_IN_WINDOW = 6
DUPLICATE_WINDOW_SECONDS = 20
MAX_IDENTICAL_MESSAGES = 3
MUTE_SECONDS = 60
STATE_TTL_SECONDS = 120

_SEND_PERMISSION_FIELDS = (
    "can_send_messages",
    "can_send_audios",
    "can_send_documents",
    "can_send_photos",
    "can_send_videos",
    "can_send_video_notes",
    "can_send_voice_notes",
    "can_send_polls",
    "can_send_other_messages",
    "can_add_web_page_previews",
)

_message_times: dict[tuple[int, int], deque[float]] = defaultdict(deque)
_duplicate_times: dict[tuple[int, int, str], deque[float]] = defaultdict(deque)
_last_action: dict[tuple[int, int], float] = {}
_last_state_cleanup = 0.0


def _muted_permissions() -> ChatPermissions:
    """Disable member-generated send permissions during a short flood mute."""
    return ChatPermissions(**{field: False for field in _SEND_PERMISSION_FIELDS})


def _is_privileged_member(member: object) -> bool:
    """Handle both aiogram enum statuses and raw Telegram status strings."""
    status = getattr(member, "status", None)
    return getattr(status, "value", status) in {"creator", "administrator"}


def _message_fingerprint(message: Message) -> str:
    """Create a lightweight fingerprint from text or caption."""
    value = message.text or message.caption or ""
    return " ".join(value.casefold().split())[:500]


def _is_flooding(chat_id: int, user_id: int, fingerprint: str, now: float) -> bool:
    """Track message rate and repeated content for one member."""
    key = (chat_id, user_id)
    times = _message_times[key]
    while times and now - times[0] > WINDOW_SECONDS:
        times.popleft()
    times.append(now)

    duplicate_key = (chat_id, user_id, fingerprint)
    duplicates = _duplicate_times[duplicate_key]
    while duplicates and now - duplicates[0] > DUPLICATE_WINDOW_SECONDS:
        duplicates.popleft()
    duplicates.append(now)

    global _last_state_cleanup
    if now - _last_state_cleanup >= 30:
        _last_state_cleanup = now
        for stale_key, stale_times in list(_message_times.items()):
            if not stale_times or now - stale_times[-1] > STATE_TTL_SECONDS:
                _message_times.pop(stale_key, None)
        for stale_key, stale_times in list(_duplicate_times.items()):
            if not stale_times or now - stale_times[-1] > STATE_TTL_SECONDS:
                _duplicate_times.pop(stale_key, None)
        for stale_key, last_action in list(_last_action.items()):
            if now - last_action > STATE_TTL_SECONDS:
                _last_action.pop(stale_key, None)

    return (
        len(times) > MAX_MESSAGES_IN_WINDOW
        or (bool(fingerprint) and len(duplicates) >= MAX_IDENTICAL_MESSAGES)
    )


def create_antispam_router(owner_id: int | None = None) -> Router:
    """Create a group-only anti-spam router; admins and owner are exempt."""
    router = Router(name="anti_spam")

    @router.message(
        F.chat.type.in_({"group", "supergroup"})
        & ((F.text == None) | ~F.text.startswith("/"))
    )
    async def inspect_message(message: Message) -> None:
        register_group(message.chat.id, message.chat.title or "Telegram group")
        user = message.from_user
        if user is None or user.is_bot or is_owner(user.id, owner_id):
            raise SkipHandler

        try:
            member = await message.bot.get_chat_member(message.chat.id, user.id)
            if _is_privileged_member(member):
                raise SkipHandler
        except SkipHandler:
            raise
        except TelegramAPIError:
            logger.exception(
                "Anti-spam could not check member status chat_id=%s user_id=%s",
                message.chat.id,
                user.id,
            )
            raise SkipHandler

        now = time.monotonic()
        key = (message.chat.id, user.id)
        if now - _last_action.get(key, 0.0) < MUTE_SECONDS:
            try:
                await message.delete()
            except TelegramAPIError:
                logger.debug("Could not delete message during anti-spam cooldown")
            return

        if not _is_flooding(
            message.chat.id,
            user.id,
            _message_fingerprint(message),
            now,
        ):
            # Let anti-link, bad-word and media-policy handlers inspect normal messages.
            raise SkipHandler

        logger.warning(
            "Anti-spam flood threshold reached chat_id=%s user_id=%s",
            message.chat.id,
            user.id,
        )
        try:
            await message.delete()
        except TelegramAPIError:
            logger.exception(
                "Could not delete spam message chat_id=%s user_id=%s",
                message.chat.id,
                user.id,
            )

        try:
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=user.id,
                permissions=_muted_permissions(),
                until_date=int(time.time()) + MUTE_SECONDS,
            )
            _last_action[key] = now
            record_audit_event(message.chat.id, "anti_spam_mute", None, user.id, f"duration={MUTE_SECONDS}s")
            record_security_incident(
                message.chat.id, message.chat.title or "Telegram group",
                "anti_spam", "medium", user.id, user.username, user.full_name,
                f"Flood threshold triggered; timeout={MUTE_SECONDS}s",
            )
            logger.warning(
                "Anti-spam muted user_id=%s chat_id=%s duration=%ss",
                user.id,
                message.chat.id,
                MUTE_SECONDS,
            )
            await message.answer(premium_text(
                f"⚠️ <b>Easy there!</b>\n\nYou’re sending messages a little too fast. "
                f"Please slow down and let everyone enjoy the conversation. 💬\n\n"
                f"🛡️ <b>Ani World Anti-Spam</b> · Timeout: {MUTE_SECONDS}s"
            ))
        except TelegramAPIError:
            logger.exception(
                "Anti-spam restriction failed chat_id=%s user_id=%s",
                message.chat.id,
                user.id,
            )
            try:
                await message.answer(premium_text(
                    "⚠️ <b>Spam detected</b>\n\n"
                    "Your messages were removed, but Telegram rejected the temporary mute. "
                    "An administrator has been alerted."
                ))
            except TelegramAPIError:
                logger.exception(
                    "Could not report anti-spam restriction failure chat_id=%s",
                    message.chat.id,
                )

    return router
