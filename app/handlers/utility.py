"""Small utility commands for Telegram chats."""
from __future__ import annotations

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message

from app.storage import get_member_profile_history, record_member_profile


def _previous_names(history: list[dict]) -> list[str]:
    names = []
    for item in history[1:]:
        name = " ".join(part for part in (item["first_name"], item["last_name"]) if part).strip()
        if name and name not in names:
            names.append(name)
    return names


def create_utility_router() -> Router:
    router = Router(name="utilities")

    @router.message(Command("id"))
    async def id_command(message: Message) -> None:
        target = message.reply_to_message.from_user if message.reply_to_message else None
        raw_arg = (message.text or "").partition(" ")[2].strip().split()
        requested_id = None
        if raw_arg:
            try:
                requested_id = int(raw_arg[0])
                if requested_id <= 0:
                    raise ValueError
            except ValueError:
                await message.answer("❌ Use /id, /id USER_ID, or reply to a member with /id.")
                return

        if requested_id is not None:
            try:
                if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                    target = (await message.bot.get_chat_member(message.chat.id, requested_id)).user
                else:
                    target = await message.bot.get_chat(requested_id)
            except TelegramAPIError:
                await message.answer(
                    "⚠️ I couldn't access that profile. In a group, the user must be a member; "
                    "in private chat, they may need to start the bot first."
                )
                return
        elif target is None:
            target = message.from_user

        if target is None or not getattr(target, "id", None):
            await message.answer("⚠️ Telegram did not provide a user profile for this message.")
            return

        first_name = getattr(target, "first_name", "") or ""
        last_name = getattr(target, "last_name", "") or ""
        username = getattr(target, "username", "") or ""
        bio = ""
        try:
            full_chat = await message.bot.get_chat(target.id)
            bio = getattr(full_chat, "bio", "") or ""
            first_name = getattr(full_chat, "first_name", first_name) or first_name
            last_name = getattr(full_chat, "last_name", last_name) or last_name
            username = getattr(full_chat, "username", username) or username
        except TelegramAPIError:
            pass

        record_member_profile(
            message.chat.id, target.id, first_name, last_name, username
        )
        history = get_member_profile_history(target.id, limit=6)
        group_chat = message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)
        lines = [
            "🪪 <b>Telegram ID</b>",
            f"👤 <b>User ID:</b> <code>{target.id}</code>",
            f"💬 <b>Chat ID:</b> <code>{message.chat.id}</code>",
        ]
        if group_chat:
            lines.insert(0, f"👥 <b>Group:</b> {message.chat.title or 'Telegram group'}")
            lines.append(f"🆔 <b>Group ID:</b> <code>{message.chat.id}</code>")
        await message.answer("\\n".join(lines))

    return router
