"""Unified per-group security status command."""
from __future__ import annotations

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.typography import premium_text
from app.storage import is_copyright_enabled, is_feature_enabled


def security_status_text(chat_id: int, title: str) -> str:
    """Build a concise status report from the group's persisted settings."""
    antilink = is_feature_enabled("antilink", chat_id)
    badwords = is_feature_enabled("badwords", chat_id)
    copyright_filter = is_copyright_enabled(chat_id)
    state = lambda enabled: "🟢 ON" if enabled else "⚪ OFF"
    return premium_text(
        "🛡️ <b>Ani World · Security Status</b>\n\n"
        f"🏠 <b>Group:</b> {title}\n\n"
        f"🔗 Anti-link: <b>{state(antilink)}</b>\n"
        f"🤬 Bad-word filter: <b>{state(badwords)}</b>\n"
        f"©️ Media upload policy: <b>{state(copyright_filter)}</b>\n"
        "🧩 New-member CAPTCHA: <b>🟢 ON</b>\n"
        "🌊 Anti-spam: <b>🟢 ON</b>\n"
        "🚨 Raid detection: <b>🟢 ON</b>\n\n"
        "<i>Raid mode activates at 500 human joins in 10 minutes. "
        "Use /checkpermissions to verify the bot's Telegram admin rights.</i>"
    )


def create_security_status_router() -> Router:
    router = Router(name="security_status")

    @router.message(Command("security"))
    async def security_command(message: Message) -> None:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer(premium_text("🛡️ Run /security inside a group to view its protection settings."))
            return
        if not message.from_user:
            return
        try:
            actor = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        except TelegramAPIError:
            await message.answer(premium_text("⚠️ I couldn't verify your admin status. Try again shortly."))
            return
        if actor.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer(premium_text("🔒 <b>Admin Only</b>\n\nOnly group admins can view security settings."))
            return
        await message.answer(security_status_text(message.chat.id, message.chat.title or "Telegram group"))

    return router
