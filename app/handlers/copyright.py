"""Automatic group media restrictions to reduce copyright infringement risk."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from app.storage import record_audit_event

MEDIA_TYPES = {
    "photo", "video", "animation", "document", "audio", "voice",
    "video_note", "sticker",
}


def create_copyright_router() -> Router:
    """Automatically remove member-posted media in every group; no setup command."""
    router = Router(name="copyright")

    async def inspect_media(message: Message) -> None:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return
        user = message.from_user
        if not user or user.is_bot:
            return

        try:
            member = await message.bot.get_chat_member(message.chat.id, user.id)
            if member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
                return

            bot_user = await message.bot.get_me()
            bot_member = await message.bot.get_chat_member(message.chat.id, bot_user.id)
            if bot_member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
                return
            if not getattr(bot_member, "can_delete_messages", False):
                return

            await message.delete()
            record_audit_event(
                message.chat.id,
                "copyright_media_removed",
                None,
                user.id,
                f"content_type={message.content_type}",
            )
        except TelegramAPIError:
            # Permission/API failures must not crash polling or expose message contents.
            return

    router.message.register(inspect_media, F.content_type.in_(MEDIA_TYPES))
    router.edited_message.register(inspect_media, F.content_type.in_(MEDIA_TYPES))
    return router
