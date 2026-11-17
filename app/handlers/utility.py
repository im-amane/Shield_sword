"""Small utility commands for Telegram chats."""
from __future__ import annotations

from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.typography import premium_text


def create_utility_router() -> Router:
    router = Router(name="utilities")

    @router.message(Command("id"))
    async def id_command(message: Message) -> None:
        lines = [f"💬 <b>Chat ID:</b> <code>{message.chat.id}</code>"]
        target = message.reply_to_message.from_user if message.reply_to_message else None
        if target:
            lines.append(
                f"👤 <b>{escape(target.full_name)}</b> ID: <code>{target.id}</code>"
            )
        elif message.from_user:
            lines.append(
                f"👤 <b>Your ID:</b> <code>{message.from_user.id}</code>"
            )
        lines.append("\nUse /id as a reply to get another member's ID.")
        await message.answer(premium_text("\n".join(lines)))

    return router
