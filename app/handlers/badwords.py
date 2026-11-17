"""Configurable bad-word protection for Telegram groups."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import BaseFilter, Command
from aiogram.types import ChatPermissions, Message

from app.handlers.typography import premium_text
from app.handlers.warnings import WARN_LIMIT, add_warning, reset_warnings
from app.storage import add_badword, get_badwords, is_feature_enabled, remove_badword, set_feature_enabled


def normalize_word(value: str) -> str:
    """Normalize a word or phrase while rejecting empty/control-character input."""
    word = " ".join(value.casefold().split())
    if not word:
        raise ValueError("Enter a word or phrase.")
    if len(word) > 64:
        raise ValueError("A word or phrase can be at most 64 characters.")
    if any(ord(char) < 32 for char in word):
        raise ValueError("Control characters are not allowed.")
    return word


def contains_bad_word(text: str, words: set[str]) -> bool:
    """Match configured terms as whole words/phrases, ignoring letter case."""
    folded = text.casefold()
    for word in words:
        pattern = r"(?<!\w)" + r"\s+".join(re.escape(part) for part in word.split()) + r"(?!\w)"
        if re.search(pattern, folded, flags=re.UNICODE):
            return True
    return False


class BadWordMatchFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return False
        if not is_feature_enabled('badwords', message.chat.id) or not message.from_user or message.from_user.is_bot:
            return False
        if message.text and message.text.startswith("/"):
            return False
        value = message.text or message.caption or ""
        return bool(value and contains_bad_word(value, get_badwords(message.chat.id)))


def create_badwords_router() -> Router:
    router = Router(name="bad_words")

    async def require_admin(message: Message) -> bool:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("This command only works in groups.")
            return False
        if not message.from_user:
            return False
        try:
            actor = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
            me = await message.bot.get_me()
            bot_member = await message.bot.get_chat_member(message.chat.id, me.id)
        except TelegramAPIError:
            await message.answer("Permission check failed. Please try again.")
            return False
        if actor.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer("Only group admins can manage the bad-words filter.")
            return False
        if actor.status == ChatMemberStatus.ADMINISTRATOR and not getattr(actor, "can_delete_messages", False):
            await message.answer("You need Delete Messages permission to manage this filter.")
            return False
        if bot_member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR) or not getattr(bot_member, "can_delete_messages", False):
            await message.answer("Promote Ani World with Delete Messages permission.")
            return False
        return True

    @router.message(Command("badwords"))
    async def badwords_command(message: Message) -> None:
        if not await require_admin(message):
            return
        args = (message.text or "").split(maxsplit=1)
        action = args[1].strip().casefold() if len(args) > 1 else "status"
        chat_id = message.chat.id
        if action == "on":
            set_feature_enabled('badwords', chat_id, True)
            response = "✅ <b>Bad-Words Filter Enabled</b>"
        elif action == "off":
            set_feature_enabled('badwords', chat_id, False)
            response = "⏸️ <b>Bad-Words Filter Disabled</b>"
        elif action == "status":
            state = "ON" if is_feature_enabled("badwords", chat_id) else "OFF"
            words = sorted(get_badwords(chat_id))
            listed = ", ".join(f"<code>{escape(word)}</code>" for word in words) if words else "No words added yet."
            response = (
                f"🛡️ <b>Bad-Words Filter: {state}</b>\n\n"
                f"<b>Configured words:</b> {listed}\n\n"
                "<code>/badwords on</code> - enable\n"
                "<code>/badwords off</code> - disable\n"
                "<code>/addword phrase</code> - add a word or phrase\n"
                "<code>/removeword phrase</code> - remove it"
            )
        else:
            response = "Use <code>/badwords</code>, <code>/badwords on</code> or <code>/badwords off</code>."
        await message.answer(premium_text(response))

    @router.message(Command("addword"))
    async def addword_command(message: Message) -> None:
        if not await require_admin(message):
            return
        args = (message.text or "").split(maxsplit=1)
        try:
            if len(args) < 2:
                raise ValueError("Usage: /addword word or phrase")
            word = normalize_word(args[1])
        except ValueError as exc:
            await message.answer(premium_text(f"⚠️ <b>Invalid Word</b>\n\n{escape(str(exc))}"))
            return
        add_badword(message.chat.id, word)
        await message.answer(premium_text(f"✅ Added <code>{escape(word)}</code> to the bad-words list."))

    @router.message(Command("removeword"))
    async def removeword_command(message: Message) -> None:
        if not await require_admin(message):
            return
        args = (message.text or "").split(maxsplit=1)
        try:
            if len(args) < 2:
                raise ValueError("Usage: /removeword word or phrase")
            word = normalize_word(args[1])
        except ValueError as exc:
            await message.answer(premium_text(f"⚠️ <b>Invalid Word</b>\n\n{escape(str(exc))}"))
            return
        remove_badword(message.chat.id, word)
        await message.answer(premium_text(f"✅ Removed <code>{escape(word)}</code> from the bad-words list."))

    @router.message(BadWordMatchFilter())
    async def inspect_message(message: Message) -> None:
        user = message.from_user
        if not user:
            return
        try:
            member = await message.bot.get_chat_member(message.chat.id, user.id)
        except TelegramAPIError:
            return
        if member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            return

        try:
            await message.delete()
        except TelegramAPIError:
            # Never issue a warning when the offending message could not be removed.
            return

        count = add_warning(message.chat.id, user.id)
        if count >= WARN_LIMIT:
            try:
                await message.bot.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now(timezone.utc) + timedelta(minutes=10),
                )
            except TelegramAPIError:
                await message.answer(premium_text(
                    f"⚠️ <b>Inappropriate Message Removed</b>\n\n"
                    f"👤 {escape(user.full_name)}\n"
                    f"Warning {count}/{WARN_LIMIT}. I could not apply the 10-minute mute; check Ban Users permission."
                ))
                return
            reset_warnings(message.chat.id, user.id)
            await message.answer(premium_text(
                f"🔇 <b>Member Muted</b>\n\n"
                f"👤 {escape(user.full_name)}\n"
                f"⚠️ Warning limit reached ({WARN_LIMIT}/{WARN_LIMIT}).\n"
                "⏳ Muted for 10 minutes."
            ))
            return

        await message.answer(premium_text(
            f"⚠️ <b>Inappropriate Message Removed</b>\n\n"
            f"👤 {escape(user.full_name)}\n"
            f"📊 Warning: {count}/{WARN_LIMIT}\n"
            "Please keep the group respectful."
        ))

    return router
