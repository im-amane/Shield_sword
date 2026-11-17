"""Admin warning system with automatic timeout after three warnings."""
from __future__ import annotations

from collections import defaultdict
from html import escape
from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

from app.handlers.typography import premium_text

WARN_LIMIT = 3
AUTO_MUTE_SECONDS = 10 * 60

# In-memory for now; counts reset when the process restarts.
_warning_counts: dict[tuple[int, int], int] = defaultdict(int)


def add_warning(chat_id: int, user_id: int) -> int:
    key = (chat_id, user_id)
    _warning_counts[key] += 1
    return _warning_counts[key]


def get_warnings(chat_id: int, user_id: int) -> int:
    return _warning_counts.get((chat_id, user_id), 0)


def reset_warnings(chat_id: int, user_id: int) -> None:
    _warning_counts.pop((chat_id, user_id), None)


def create_warning_router() -> Router:
    router = Router(name="warnings")

    async def check_admin(message: Message, *, needs_restrict: bool = False) -> bool:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer(premium_text("⚠️ <b>Group Only</b>\n\nThis command works inside a group."))
            return False
        if not message.from_user:
            return False
        try:
            actor = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
            me = await message.bot.get_me()
            bot_member = await message.bot.get_chat_member(message.chat.id, me.id)
        except Exception:
            await message.answer(premium_text("❌ <b>Permission Check Failed</b>\n\nPlease try again."))
            return False
        if actor.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer(premium_text("🔒 <b>Admin Only</b>\n\nOnly group admins can use this command."))
            return False
        if actor.status == ChatMemberStatus.ADMINISTRATOR and needs_restrict and not getattr(actor, "can_restrict_members", False):
            await message.answer(premium_text("🔒 <b>Missing Admin Right</b>\n\nYou need Ban Users permission."))
            return False
        if bot_member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer(premium_text("⚙️ <b>Bot Permission Needed</b>\n\nPromote Ani World as an admin first."))
            return False
        if needs_restrict and not getattr(bot_member, "can_restrict_members", False):
            await message.answer(premium_text("⚙️ <b>Missing Permission</b>\n\nI need Ban Users permission."))
            return False
        return True

    async def target_from_reply(message: Message):
        target_message = message.reply_to_message
        target = target_message.from_user if target_message else None
        if target is None:
            await message.answer(premium_text("↩️ <b>Reply Required</b>\n\nReply to a member's message first."))
            return None
        if target.is_bot:
            await message.answer(premium_text("🤖 Bots cannot receive warnings here."))
            return None
        try:
            member = await message.bot.get_chat_member(message.chat.id, target.id)
        except Exception:
            await message.answer(premium_text("❌ <b>Member Lookup Failed</b>\n\nI could not verify this member."))
            return None
        if member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer(premium_text("🛡️ <b>Protected Member</b>\n\nAdmins cannot be warned by this command."))
            return None
        return target

    @router.message(Command("warn"))
    async def warn_command(message: Message) -> None:
        if not await check_admin(message):
            return
        target = await target_from_reply(message)
        if target is None:
            return
        count = add_warning(message.chat.id, target.id)
        if count < WARN_LIMIT:
            await message.answer(premium_text(
                f"⚠️ <b>Warning Issued</b>\n\n"
                f"👤 {escape(target.full_name)}\n"
                f"📊 Warnings: {count}/{WARN_LIMIT}\n\n"
                f"One more warning will trigger a 10-minute mute."
            ))
            return
        if not await check_admin(message, needs_restrict=True):
            # Do not consume the threshold if the bot cannot enforce it.
            reset_warnings(message.chat.id, target.id)
            add_warning(message.chat.id, target.id)
            return
        try:
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now(timezone.utc) + timedelta(seconds=AUTO_MUTE_SECONDS),
            )
        except Exception:
            await message.answer(premium_text("❌ <b>Auto-Mute Failed</b>\n\nCheck my Ban Users permission and try again."))
            return
        reset_warnings(message.chat.id, target.id)
        await message.answer(premium_text(
            f"🔇 <b>Warning Limit Reached</b>\n\n"
            f"👤 {escape(target.full_name)}\n"
            f"⚠️ {WARN_LIMIT} warnings received.\n"
            f"⏳ Automatically muted for 10 minutes.\n\n"
            f"Warnings have been reset."
        ))

    @router.message(Command("warnings"))
    async def warnings_command(message: Message) -> None:
        if not await check_admin(message):
            return
        target = await target_from_reply(message)
        if target is None:
            return
        count = get_warnings(message.chat.id, target.id)
        await message.answer(premium_text(
            f"📋 <b>Warning Record</b>\n\n"
            f"👤 {escape(target.full_name)}\n"
            f"⚠️ Warnings: {count}/{WARN_LIMIT}"
        ))

    @router.message(Command("resetwarn"))
    async def resetwarn_command(message: Message) -> None:
        if not await check_admin(message):
            return
        target = await target_from_reply(message)
        if target is None:
            return
        reset_warnings(message.chat.id, target.id)
        await message.answer(premium_text(
            f"✅ <b>Warnings Cleared</b>\n\n"
            f"👤 {escape(target.full_name)}\n"
            f"The warning record has been reset."
        ))

    return router
