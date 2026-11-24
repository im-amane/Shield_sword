"""Basic anti-spam and flood protection for group chats."""
from __future__ import annotations

import hashlib
import logging
import time

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatPermissions, Message

from app.security.owner import is_owner
from app.handlers.typography import premium_text
from app.storage import (
    claim_antispam_mute,
    clear_antispam_mute,
    get_antispam_mute_until,
    record_antispam_message,
    record_audit_event,
    record_security_incident,
    register_group,
)

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 8
MAX_MESSAGES_IN_WINDOW = 6
DUPLICATE_WINDOW_SECONDS = 20
MAX_IDENTICAL_MESSAGES = 3
MUTE_SECONDS = 60

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

def _muted_permissions() -> ChatPermissions:
    """Disable member-generated send permissions during a short flood mute."""
    return ChatPermissions(**{field: False for field in _SEND_PERMISSION_FIELDS})


def _is_privileged_member(member: object) -> bool:
    """Handle both aiogram enum statuses and raw Telegram status strings."""
    status = getattr(member, "status", None)
    return getattr(status, "value", status) in {"creator", "administrator"}


def _message_fingerprint(message: Message) -> str:
    """Hash normalized text so duplicate detection never persists message content."""
    value = " ".join((message.text or message.caption or "").casefold().split())[:500]
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else ""


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

        now = time.time()
        chat_id = message.chat.id
        mute_until = get_antispam_mute_until(chat_id, user.id)
        if mute_until > now:
            try:
                await message.delete()
            except TelegramAPIError:
                logger.debug("Could not delete message during anti-spam cooldown")
            return

        flooding = record_antispam_message(
            chat_id,
            user.id,
            _message_fingerprint(message),
            now,
            WINDOW_SECONDS,
            DUPLICATE_WINDOW_SECONDS,
            MAX_MESSAGES_IN_WINDOW,
            MAX_IDENTICAL_MESSAGES,
        )
        if not flooding:
            # Let anti-link, bad-word and media-policy handlers inspect normal messages.
            raise SkipHandler

        expected_mute_until = now + MUTE_SECONDS
        if not claim_antispam_mute(chat_id, user.id, now, MUTE_SECONDS):
            try:
                await message.delete()
            except TelegramAPIError:
                logger.debug("Could not delete message during concurrent anti-spam mute")
            return

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
                chat_id=chat_id,
                user_id=user.id,
                permissions=_muted_permissions(),
                until_date=int(expected_mute_until),
            )
        except TelegramAPIError:
            clear_antispam_mute(chat_id, user.id, expected_mute_until)
            logger.exception(
                "Anti-spam restriction failed chat_id=%s user_id=%s",
                chat_id,
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
                    chat_id,
                )
            return

        record_audit_event(chat_id, "anti_spam_mute", None, user.id, f"duration={MUTE_SECONDS}s")
        record_security_incident(
            chat_id, message.chat.title or "Telegram group",
            "anti_spam", "medium", user.id, user.username, user.full_name,
            f"Flood threshold triggered; timeout={MUTE_SECONDS}s",
        )
        logger.warning(
            "Anti-spam muted user_id=%s chat_id=%s duration=%ss",
            user.id,
            chat_id,
            MUTE_SECONDS,
        )
        try:
            await message.answer(premium_text(
                f"⚠️ <b>Easy there!</b>\n\nYou’re sending messages a little too fast. "
                f"Please slow down and let everyone enjoy the conversation. 💬\n\n"
                f"🛡️ <b>Ani World Anti-Spam</b> · Timeout: {MUTE_SECONDS}s"
            ))
        except TelegramAPIError:
            logger.exception("Could not send anti-spam notice chat_id=%s", chat_id)

    return router
