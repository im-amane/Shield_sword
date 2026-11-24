"""Admin warning system with automatic timeout after three warnings."""
from __future__ import annotations

from html import escape
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.types import (CallbackQuery, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Message)

from app.handlers.typography import premium_text
from app.storage import record_audit_event

WARN_LIMIT = 3
AUTO_MUTE_SECONDS = 10 * 60

from app.storage import add_warning, get_warnings, reset_warnings, remove_one_warning


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
            await message.answer(premium_text("⚙️ <b>Bot Permission Needed</b>\n\nPromote Sentinel as an administrator first."))
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
        record_audit_event(message.chat.id, "warn", message.from_user.id if message.from_user else None, target.id, f"count={count}")
        if count < WARN_LIMIT:
            markup = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="➖ Unwarn",
                    callback_data=f"warnings:unwarn:{message.chat.id}:{target.id}",
                ),
                InlineKeyboardButton(text="✖️ Close", callback_data="ui:close"),
            ]])
            await message.answer(premium_text(
                f"⚠️ <b>Warning Issued</b>\n\n"
                f"👤 {escape(target.full_name)}\n"
                f"📊 Warnings: {count}/{WARN_LIMIT}\n\n"
                f"One more warning will trigger a 10-minute mute."
            ), reply_markup=markup)
            return
        if not await check_admin(message, needs_restrict=True):
            # Keep the threshold reached so an admin can retry after fixing permissions.
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
        record_audit_event(message.chat.id, "auto_mute", message.from_user.id if message.from_user else None, target.id, "warnings threshold reached")
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
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="➖ Unwarn",
                callback_data=f"warnings:unwarn:{message.chat.id}:{target.id}",
            )
        ]]) if count > 0 else None
        await message.answer(premium_text(
            f"📋 <b>Warning Record</b>\n\n"
            f"👤 {escape(target.full_name)}\n"
            f"⚠️ Warnings: {count}/{WARN_LIMIT}"
        ), reply_markup=markup)

    @router.message(Command("unwarn"))
    async def unwarn_command(message: Message) -> None:
        if not await check_admin(message):
            return
        target = await target_from_reply(message)
        if target is None:
            return
        remaining = remove_one_warning(message.chat.id, target.id)
        record_audit_event(
            message.chat.id, "unwarn",
            message.from_user.id if message.from_user else None,
            target.id, f"remaining={remaining}",
        )
        await message.answer(premium_text(
            f"➖ <b>One Warning Removed</b>\n\n"
            f"👤 {escape(target.full_name)}\n"
            f"⚠️ Remaining warnings: {remaining}/{WARN_LIMIT}"
        ))

    @router.callback_query(F.data.startswith("warnings:unwarn:"))
    async def unwarn_button(callback: CallbackQuery) -> None:
        message = callback.message
        if message is None or message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.answer(premium_text("Use this button in its original group. 🔒"), show_alert=True)
            return
        try:
            _, _, raw_chat_id, raw_user_id = (callback.data or "").split(":")
            chat_id, target_id = int(raw_chat_id), int(raw_user_id)
        except (ValueError, TypeError):
            await callback.answer(premium_text("Invalid warning action. 🔒"), show_alert=True)
            return
        if message.chat.id != chat_id or callback.from_user is None:
            await callback.answer(premium_text("This warning action is not valid here. 🔒"), show_alert=True)
            return
        try:
            actor = await callback.bot.get_chat_member(chat_id, callback.from_user.id)
            target_member = await callback.bot.get_chat_member(chat_id, target_id)
        except Exception:
            await callback.answer(premium_text("Could not verify group permissions. Try again."), show_alert=True)
            return
        if actor.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await callback.answer(premium_text("Only group admins can remove warnings. 🔒"), show_alert=True)
            return
        if target_member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await callback.answer(premium_text("Admins are protected from warning actions. 🔒"), show_alert=True)
            return
        remaining = remove_one_warning(chat_id, target_id)
        record_audit_event(chat_id, "unwarn", callback.from_user.id, target_id, f"remaining={remaining}")
        buttons = []
        if remaining:
            buttons.append(InlineKeyboardButton(
                text="➖ Unwarn",
                callback_data=f"warnings:unwarn:{chat_id}:{target_id}",
            ))
        buttons.append(InlineKeyboardButton(text="✖️ Close", callback_data="ui:close"))
        markup = InlineKeyboardMarkup(inline_keyboard=[buttons])
        await message.edit_text(
            premium_text(
                "📋 <b>Warning Record Updated</b>\n\n"
                f"👤 User ID: <code>{target_id}</code>\n"
                f"⚠️ Remaining warnings: {remaining}/{WARN_LIMIT}"
            ),
            reply_markup=markup,
        )
        await callback.answer(premium_text("One warning removed. ✅"))

    @router.message(Command("resetwarn"))
    async def resetwarn_command(message: Message) -> None:
        if not await check_admin(message):
            return
        target = await target_from_reply(message)
        if target is None:
            return
        reset_warnings(message.chat.id, target.id)
        record_audit_event(message.chat.id, "reset_warnings", message.from_user.id if message.from_user else None, target.id)
        await message.answer(premium_text(
            f"✅ <b>Warnings Cleared</b>\n\n"
            f"👤 {escape(target.full_name)}\n"
            f"The warning record has been reset."
        ))

    return router
