"""Group and opt-in channel media protection."""
from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.typography import premium_text
from app.storage import (
    is_channel_media_enabled,
    is_copyright_enabled,
    record_audit_event,
    record_security_incident,
    set_channel_media_enabled,
)

MEDIA_TYPES = {
    "photo", "video", "animation", "document", "audio", "voice",
    "video_note", "sticker",
}


def create_copyright_router() -> Router:
    """Protect group media by default and channels only after explicit opt-in."""
    router = Router(name="copyright")

    @router.message(Command("channelprotect"))
    async def channel_protection_command(message: Message) -> None:
        if message.chat.type != ChatType.PRIVATE or not message.from_user:
            await message.answer(premium_text(
                "🔒 <b>Private Setup Required</b>\\n\\n"
                "Manage channel protection in my private chat with "
                "<code>/channelprotect @channel on</code>."
            ))
            return

        args = (message.text or "").split()
        if len(args) not in (2, 3):
            await message.answer(premium_text(
                "🛡️ <b>Channel Media Protection</b>\\n\\n"
                "<code>/channelprotect @channel on</code>\\n"
                "<code>/channelprotect @channel off</code>\\n"
                "<code>/channelprotect @channel status</code>\\n\\n"
                "Add me to the channel as an administrator with Delete Messages permission first."
            ))
            return

        channel_ref = args[1]
        action = args[2].casefold() if len(args) == 3 else "status"
        if action not in {"on", "off", "status"}:
            await message.answer(premium_text(
                "⚠️ Use <code>on</code>, <code>off</code> or <code>status</code>."
            ))
            return

        try:
            lookup = int(channel_ref) if channel_ref.lstrip("-").isdigit() else channel_ref
            channel = await message.bot.get_chat(lookup)
            if channel.type != ChatType.CHANNEL:
                await message.answer(premium_text("⚠️ That ID or username is not a Telegram channel."))
                return

            bot_user = await message.bot.get_me()
            bot_member = await message.bot.get_chat_member(channel.id, bot_user.id)
            if (
                bot_member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)
                or not getattr(bot_member, "can_delete_messages", False)
            ):
                await message.answer(premium_text(
                    "⚙️ <b>Bot Permission Needed</b>\\n\\n"
                    "Promote me in that channel and enable <b>Delete Messages</b>."
                ))
                return

            actor = await message.bot.get_chat_member(channel.id, message.from_user.id)
            if actor.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
                await message.answer(premium_text(
                    "🔒 <b>Channel Admin Only</b>\\n\\n"
                    "Only an administrator of that channel can change its protection."
                ))
                return
        except TelegramAPIError:
            await message.answer(premium_text(
                "⚠️ <b>Channel Check Failed</b>\\n\\n"
                "I could not verify the channel and its administrator permissions. "
                "Check the channel username/ID and my admin access."
            ))
            return

        if action in {"on", "off"}:
            enabled = action == "on"
            set_channel_media_enabled(channel.id, enabled)
            record_audit_event(
                channel.id, "channel_media_protection_enabled" if enabled
                else "channel_media_protection_disabled",
                message.from_user.id, None, "configured from private chat",
            )

        state = is_channel_media_enabled(channel.id)
        warning = (
            "\\n\\n⚠️ When ON, every media post is removed, including posts made by channel admins. "
            "Telegram does not reliably expose the individual poster in channel-post updates."
            if state else ""
        )
        await message.answer(premium_text(
            f"🛡️ <b>Channel Protection · {escape(channel.title or 'Channel')}</b>\\n\\n"
            f"Status: <b>{'ON' if state else 'OFF'}</b>"
            f"{warning}\\n\\n"
            "Use <code>/channelprotect @channel on</code> or "
            "<code>/channelprotect @channel off</code> to change it."
        ))

    async def inspect_media(message: Message) -> None:
        # Group media is deliberately never blanket-deleted. Group safety is
        # enforced by the dedicated anti-link, bad-word and anti-spam handlers,
        # which inspect captions as well as text. This channel-only path remains
        # explicit opt-in because Telegram channel updates do not reliably
        # identify the individual poster.
        if message.chat.type != ChatType.CHANNEL or not is_channel_media_enabled(message.chat.id):
            return
        try:
            bot_user = await message.bot.get_me()
            bot_member = await message.bot.get_chat_member(message.chat.id, bot_user.id)
            if (
                bot_member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)
                or not getattr(bot_member, "can_delete_messages", False)
            ):
                return
            await message.delete()
            record_audit_event(
                message.chat.id, "channel_media_removed", None, None,
                f"content_type={message.content_type}",
            )
            record_security_incident(
                message.chat.id, message.chat.title or "Telegram channel",
                "channel_media_policy", "low", details=f"Removed channel media; type={message.content_type}",
            )
        except TelegramAPIError:
            # Permission/API failures must not crash polling or expose message contents.
            return

    router.channel_post.register(inspect_media, F.content_type.in_(MEDIA_TYPES))
    router.edited_channel_post.register(inspect_media, F.content_type.in_(MEDIA_TYPES))
    return router
