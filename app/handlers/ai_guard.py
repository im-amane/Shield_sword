"""NVIDIA NIM AI moderation for group messages and channel posts."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatPermissions, Message

from app.ai_guard import AiScanLimiter, NimSafetyClient
from app.handlers.typography import premium_text
from app.handlers.warnings import WARN_LIMIT, add_warning, reset_warnings
from app.security.owner import is_owner
from app.storage import record_audit_event, record_security_incident

logger = logging.getLogger(__name__)


def create_ai_guard_router(owner_id: int | None, api_key: str, model: str) -> Router:
    """Create AI moderation; provider failures fail open to deterministic filters."""
    router = Router(name="nvidia_nim_ai_guard")
    client = NimSafetyClient(api_key, model)
    limiter = AiScanLimiter()

    @router.message(
        F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})
        & (F.text | F.caption)
    )
    async def inspect_message(message: Message) -> None:
        user = message.from_user
        content = message.text or message.caption or ""
        if not user or user.is_bot or not content.strip():
            return
        if content.lstrip().startswith("/") or is_owner(user.id, owner_id):
            return
        if not limiter.allow(message.chat.id, user.id):
            return
        try:
            member = await message.bot.get_chat_member(message.chat.id, user.id)
        except TelegramAPIError:
            logger.warning(
                "AI Guard skipped because member status could not be verified chat_id=%s user_id=%s",
                message.chat.id, user.id,
            )
            return
        if member.status in {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}:
            return

        result = await client.classify(content)
        if not result or not result["unsafe"]:
            return
        try:
            await message.delete()
        except TelegramAPIError:
            logger.warning(
                "AI Guard flagged content but Telegram deletion failed chat_id=%s user_id=%s",
                message.chat.id, user.id,
            )
            return

        categories = escape(result.get("categories") or "community safety policy")
        count = add_warning(message.chat.id, user.id)
        record_audit_event(
            message.chat.id, "ai_guard_removed", None, user.id,
            f"categories={categories[:120]}; warning={count}",
        )
        record_security_incident(
            message.chat.id, message.chat.title or "Telegram group",
            "ai_guard", "medium", user.id, user.username, user.full_name,
            f"AI safety classification; categories={categories[:120]}; warning={count}",
        )

        if count >= WARN_LIMIT:
            try:
                await message.bot.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now(timezone.utc) + timedelta(minutes=10),
                )
            except TelegramAPIError:
                logger.exception(
                    "AI Guard warning escalation mute failed chat_id=%s user_id=%s",
                    message.chat.id, user.id,
                )
            else:
                reset_warnings(message.chat.id, user.id)
                await message.answer(premium_text(
                    f"🔇 <b>AI Safety · Member Muted</b>\n\n"
                    f"👤 {escape(user.full_name)}\n"
                    f"⚠️ Warning limit reached ({WARN_LIMIT}/{WARN_LIMIT}).\n"
                    "⏳ Muted for 10 minutes."
                ))
                return

        await message.answer(premium_text(
            f"🛡️ <b>AI Safety Filter</b>\n\n"
            f"👤 {escape(user.full_name)}\n"
            f"⚠️ Message removed under: <code>{categories}</code>\n"
            f"📊 Warning: {count}/{WARN_LIMIT}"
        ))

    async def inspect_channel_post(message: Message) -> None:
        """Classify channel text/captions; never blanket-delete media."""
        content = message.text or message.caption or ""
        if message.chat.type != ChatType.CHANNEL or not content.strip():
            return
        # Channel post updates generally do not expose the individual poster.
        # Therefore no member warning/mute is attempted; only unsafe post removal
        # and an attributable-to-channel audit/incident record are made.
        if not limiter.allow_channel_post(message.chat.id):
            return
        result = await client.classify(content)
        if not result or not result["unsafe"]:
            return
        try:
            await message.delete()
        except TelegramAPIError:
            logger.warning(
                "AI Guard flagged channel post but deletion failed chat_id=%s message_id=%s",
                message.chat.id, message.message_id,
            )
            return
        categories = escape(result.get("categories") or "community safety policy")
        record_audit_event(
            message.chat.id, "ai_guard_channel_post_removed", None, None,
            f"message_id={message.message_id}; categories={categories[:120]}",
        )
        record_security_incident(
            message.chat.id, message.chat.title or "Telegram channel",
            "ai_guard_channel_post", "medium", details=(
                f"AI safety classification; message_id={message.message_id}; "
                f"categories={categories[:120]}"
            ),
        )
        logger.warning(
            "AI Guard removed unsafe channel post chat_id=%s message_id=%s categories=%s",
            message.chat.id, message.message_id, categories[:120],
        )

    router.channel_post.register(inspect_channel_post, F.text | F.caption)
    router.edited_channel_post.register(inspect_channel_post, F.text | F.caption)
    return router
