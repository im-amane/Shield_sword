"""Admin moderation commands for groups and supergroups."""
from __future__ import annotations

import logging
import re
from html import escape
from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

from app.handlers.typography import premium_text
from app.storage import record_audit_event

_DURATION = re.compile(r"^(\d+)(s|m|h|d)$", re.IGNORECASE)
DEFAULT_MUTE_SECONDS = 10 * 60
MAX_MUTE_SECONDS = 365 * 24 * 60 * 60
logger = logging.getLogger(__name__)


async def perform_kick(bot, chat_id: int, user_id: int) -> bool:
    """Remove a member and lift the temporary ban so they may rejoin.

    False means the ban succeeded but Telegram rejected the unban. The caller
    must report that partial outcome instead of claiming the member was kicked.
    """
    await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
    try:
        await bot.unban_chat_member(
            chat_id=chat_id, user_id=user_id, only_if_banned=True
        )
    except Exception:
        logger.exception(
            "Kick partially completed; member remains banned (chat_id=%s user_id=%s)",
            chat_id, user_id,
        )
        return False
    return True


def parse_duration(value: str | None) -> int:
    """Parse a compact duration such as 30s, 10m, 2h or 1d."""
    if value is None:
        return DEFAULT_MUTE_SECONDS
    match = _DURATION.fullmatch(value.strip())
    if not match:
        raise ValueError("Use a duration like 30s, 10m, 2h or 1d.")
    amount = int(match.group(1))
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2).lower()]
    seconds = amount * multiplier
    if seconds < 30:
        raise ValueError("Mute duration must be at least 30 seconds.")
    if seconds > MAX_MUTE_SECONDS:
        raise ValueError("Mute duration cannot exceed 365 days.")
    return seconds


def format_duration(seconds: int) -> str:
    """Render seconds as a readable duration."""
    for label, size in (("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1)):
        if seconds % size == 0:
            amount = seconds // size
            return f"{amount} {label}{'' if amount == 1 else 's'}"
    return f"{seconds} seconds"


def restored_permissions(group_permissions: ChatPermissions | None) -> ChatPermissions:
    """Restore the group's configured defaults instead of granting every permission."""
    if group_permissions is not None:
        return group_permissions
    return ChatPermissions(
        can_send_messages=True, can_send_audios=True, can_send_documents=True,
        can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
        can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
        can_add_web_page_previews=True,
    )


def create_moderation_router(owner_id: int | None = None) -> Router:
    """Create admin-only moderation commands."""
    router = Router(name="moderation")

    async def require_admin(message: Message, *, delete: bool = False) -> bool:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer(premium_text("⚠️ <b>Group Only</b>\n\nThis command works inside a group."))
            return False
        if not message.from_user:
            return False
        try:
            actor = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
            bot_user = await message.bot.get_me()
            bot_member = await message.bot.get_chat_member(message.chat.id, bot_user.id)
        except Exception:
            await message.answer(premium_text("❌ <b>Permission Check Failed</b>\n\nI could not verify group permissions. Try again."))
            return False
        if actor.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer(premium_text("🔒 <b>Admin Only</b>\n\nOnly group admins can use this command."))
            return False
        if actor.status == ChatMemberStatus.ADMINISTRATOR:
            actor_has_right = getattr(actor, "can_delete_messages", False) if delete else getattr(actor, "can_restrict_members", False)
            if not actor_has_right:
                needed = "Delete Messages" if delete else "Ban Users"
                await message.answer(premium_text(f"🔒 <b>Missing Admin Right</b>\n\nYour admin role needs the {needed} permission."))
                return False
        if bot_member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer(premium_text("⚙️ <b>Bot Permission Needed</b>\n\nPlease promote Sentinel as an administrator first."))
            return False
        if delete and not getattr(bot_member, "can_delete_messages", False):
            await message.answer(premium_text("⚙️ <b>Missing Permission</b>\n\nI need the Delete Messages permission to do that."))
            return False
        if not delete and not getattr(bot_member, "can_restrict_members", False):
            await message.answer(premium_text("⚙️ <b>Missing Permission</b>\n\nI need the Ban Users permission to do that."))
            return False
        return True

    async def replied_target(message: Message):
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.answer(premium_text("↩️ <b>Reply Required</b>\n\nReply to the member's message and try again."))
            return None
        target = message.reply_to_message.from_user
        if owner_id is not None and target.id == owner_id:
            await message.answer(premium_text("👑 <b>Protected Member</b>\n\nThe configured bot owner is exempt from moderation actions."))
            return None
        if target.is_bot:
            await message.answer(premium_text("🤖 I can't moderate another bot with this command."))
            return None
        try:
            member = await message.bot.get_chat_member(message.chat.id, target.id)
        except Exception:
            await message.answer(premium_text("❌ <b>Member Lookup Failed</b>\n\nI could not verify that member in this group."))
            return None
        if member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer(premium_text("🛡️ <b>Protected Member</b>\n\nI won't apply moderation actions to a group admin."))
            return None
        return target

    @router.message(Command("mute"))
    async def mute_command(message: Message) -> None:
        if not await require_admin(message):
            return
        target = await replied_target(message)
        if target is None:
            return
        args = (message.text or "").split(maxsplit=1)
        try:
            seconds = parse_duration(args[1] if len(args) > 1 else None)
        except ValueError as exc:
            await message.answer(premium_text(f"⚠️ <b>Invalid Duration</b>\n\n{exc}"))
            return
        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        try:
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
        except Exception:
            await message.answer(premium_text("❌ <b>Mute Failed</b>\n\nCheck my admin permissions and try again."))
            return
        record_audit_event(message.chat.id, "mute", message.from_user.id if message.from_user else None, target.id, f"duration={seconds}s")
        await message.answer(premium_text(
            f"🔇 <b>Member Muted</b>\n\n"
            f"👤 {escape(target.full_name)}\n"
            f"⏳ Duration: {format_duration(seconds)}"
        ))

    @router.message(Command("unmute"))
    async def unmute_command(message: Message) -> None:
        if not await require_admin(message):
            return
        target = await replied_target(message)
        if target is None:
            return
        try:
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target.id,
                permissions=restored_permissions(
                    (await message.bot.get_chat(message.chat.id)).permissions
                ),
            )
        except Exception:
            await message.answer(premium_text("❌ <b>Unmute Failed</b>\n\nCheck my admin permissions and try again."))
            return
        record_audit_event(message.chat.id, "unmute", message.from_user.id if message.from_user else None, target.id)
        await message.answer(premium_text(f"🔊 <b>Member Unmuted</b>\n\n👤 {escape(target.full_name)} can chat again. 💬"))

    @router.message(Command("ban"))
    async def ban_command(message: Message) -> None:
        if not await require_admin(message):
            return
        target = await replied_target(message)
        if target is None:
            return
        try:
            await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=target.id)
        except Exception:
            await message.answer(premium_text("❌ <b>Ban Failed</b>\n\nCheck my admin permissions and try again."))
            return
        record_audit_event(message.chat.id, "ban", message.from_user.id if message.from_user else None, target.id)
        await message.answer(premium_text(f"⛔ <b>Member Banned</b>\n\n👤 {escape(target.full_name)} has been removed from the group."))

    @router.message(Command("kick"))
    async def kick_command(message: Message) -> None:
        if not await require_admin(message):
            return
        target = await replied_target(message)
        if target is None:
            return
        try:
            completed = await perform_kick(message.bot, message.chat.id, target.id)
        except Exception:
            logger.exception(
                "Kick could not ban target (chat_id=%s user_id=%s)",
                message.chat.id, target.id,
            )
            await message.answer(premium_text("❌ <b>Kick Failed</b>\n\nTelegram could not remove this member. Check my admin permissions and try again."))
            return
        if not completed:
            record_audit_event(
                message.chat.id, "kick_partial_ban",
                message.from_user.id if message.from_user else None,
                target.id, "ban succeeded; unban failed",
            )
            await message.answer(premium_text(
                f"⚠️ <b>Member Removed, But Still Banned</b>\n\n"
                f"👤 {escape(target.full_name)} was removed, but Telegram rejected the unban. "
                f"Use <code>/unban {target.id}</code> after checking permissions if they should be allowed to rejoin."
            ))
            return
        record_audit_event(message.chat.id, "kick", message.from_user.id if message.from_user else None, target.id)
        await message.answer(premium_text(f"👢 <b>Member Kicked</b>\n\n👤 {escape(target.full_name)} was removed. They can rejoin using an invite link."))

    @router.message(Command("unban"))
    async def unban_command(message: Message) -> None:
        if not await require_admin(message):
            return
        args = (message.text or "").split(maxsplit=1)
        raw_id = args[1].strip() if len(args) > 1 else ""
        if not raw_id.isdigit():
            await message.answer(premium_text("📝 <b>How to use</b>\n\n/unban USER_ID"))
            return
        try:
            await message.bot.unban_chat_member(
                chat_id=message.chat.id, user_id=int(raw_id), only_if_banned=True
            )
        except Exception:
            await message.answer(premium_text("❌ <b>Unban Failed</b>\n\nCheck the user ID and my admin permissions."))
            return
        record_audit_event(message.chat.id, "unban", message.from_user.id if message.from_user else None, int(raw_id))
        await message.answer(premium_text(f"✅ <b>Ban Removed</b>\n\nUser <code>{raw_id}</code> can rejoin the group."))

    @router.message(Command("purge"))
    async def purge_command(message: Message) -> None:
        if not await require_admin(message, delete=True):
            return
        if not message.reply_to_message:
            await message.answer(premium_text("↩️ <b>Reply Required</b>\n\nReply to the first message you want deleted, then use /purge."))
            return
        start_id = message.reply_to_message.message_id
        end_id = message.message_id
        ids = list(range(start_id, end_id + 1))[:100]
        deleted = 0
        for offset in range(0, len(ids), 100):
            try:
                await message.bot.delete_messages(chat_id=message.chat.id, message_ids=ids[offset:offset + 100])
                deleted += len(ids[offset:offset + 100])
            except Exception:
                for message_id in ids[offset:offset + 100]:
                    try:
                        await message.bot.delete_message(chat_id=message.chat.id, message_id=message_id)
                        deleted += 1
                    except Exception:
                        continue
        record_audit_event(message.chat.id, "purge", message.from_user.id if message.from_user else None, details=f"deleted={deleted}")
        await message.answer(premium_text(f"🧹 <b>Cleanup Complete</b>\n\nDeleted {deleted} messages."))

    return router
