"""Strict group media policy to reduce copyright infringement risk.

This is a community moderation control, not a legal determination of ownership.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.typography import premium_text
from app.storage import is_copyright_enabled, record_audit_event, set_copyright_enabled

MEDIA_TYPES = {
    "photo", "video", "animation", "document", "audio", "voice",
    "video_note", "sticker",
}


def create_copyright_router() -> Router:
    router = Router(name="copyright")

    async def admin_only(message: Message) -> bool:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer(premium_text("⚠️ <b>Group Only</b>\n\nCopyright settings are managed inside the protected group."))
            return False
        if not message.from_user:
            return False
        try:
            member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        except Exception:
            await message.answer(premium_text("❌ <b>Admin Check Failed</b>\n\nI could not verify your permissions."))
            return False
        if member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer(premium_text("🔒 <b>Admin Only</b>\n\nOnly group admins can change copyright settings."))
            return False
        return True

    @router.message(Command("copyright"))
    async def copyright_command(message: Message) -> None:
        if not await admin_only(message):
            return
        args = (message.text or "").split(maxsplit=1)
        option = args[1].strip().lower() if len(args) > 1 else "status"
        if option in {"on", "off"}:
            enabled = option == "on"
            set_copyright_enabled(message.chat.id, enabled)
            record_audit_event(
                message.chat.id, "copyright_on" if enabled else "copyright_off",
                message.from_user.id if message.from_user else None,
            )
        elif option not in {"status", "help"}:
            await message.answer(premium_text("📝 <b>Usage</b>\n\n/copyright on\n/copyright off\n/copyright status"))
            return

        enabled = is_copyright_enabled(message.chat.id)
        state = "𝐎𝐍 🟢" if enabled else "𝐎𝐅𝐅 🔴"
        await message.answer(premium_text(
            "©️ <b>Copyright Shield</b>\n\n"
            f"Status: {state}\n"
            "When enabled, non-admin members cannot upload photos, videos, GIFs, "
            "documents, audio, voice notes, video notes or stickers.\n\n"
            "Admins can still post approved material. Use official/legal links for anime sources. "
            "This reduces risk but cannot guarantee protection from copyright claims."
        ))

    @router.message(F.content_type.in_(MEDIA_TYPES))
    @router.edited_message(F.content_type.in_(MEDIA_TYPES))
    async def block_member_media(message: Message) -> None:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return
        if not is_copyright_enabled(message.chat.id) or not message.from_user or message.from_user.is_bot:
            return
        try:
            member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        except Exception:
            return
        if member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            return
        try:
            bot_user = await message.bot.get_me()
            bot_member = await message.bot.get_chat_member(message.chat.id, bot_user.id)
            if bot_member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
                return
            if not getattr(bot_member, "can_delete_messages", False):
                return
            await message.delete()
            record_audit_event(
                message.chat.id, "copyright_media_removed",
                message.from_user.id, message.from_user.id,
                f"content_type={message.content_type}",
            )
            await message.answer(
                premium_text(
                    "🛡️ <b>Media Upload Restricted</b>\n\n"
                    "To keep Ani World safer from copyright complaints, member media uploads are disabled. "
                    "Text discussion and approved official links are welcome. 📚"
                )
            )
        except Exception:
            # Fail closed without exposing message contents or crashing the update loop.
            return

    return router
