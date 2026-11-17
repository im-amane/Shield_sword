"""Basic bot health and start command."""
from __future__ import annotations

import asyncio
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

router = Router(name="start")


def start_text(first_name: str) -> str:
    safe_name = escape(first_name)
    return (
        f"Hey {safe_name}! 👋✨\n\n"
        "Welcome to <b>𝗔𝗡𝗜 𝗪𝗢𝗥𝗟𝗗 剣</b>\n\n"
        "I'm your friendly group companion, here to "
        "keep your community safe, clean and secure. 🛡️\n\n"
        "I can help you with:\n"
        "» Protecting your group from spam.\n"
        "» Verifying new members.\n"
        "» Keeping raid attacks under control.\n"
        "» Making group management easier.\n\n"
        "And there's more coming soon! 🚀\n\n"
        "Need help getting started?\n"
        "Just explore the buttons below. 💫\n\n"
        "Have a wonderful time! ❤️"
    )


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌐 Main Group", callback_data="start:group"),
                InlineKeyboardButton(text="📚 Help", callback_data="start:help"),
            ],
            [
                InlineKeyboardButton(text="👤 Owner", callback_data="start:owner"),
                InlineKeyboardButton(text="➕ Add Me to Your Group", callback_data="start:addgroup"),
            ],
        ]
    )


def help_text() -> str:
    return (
        "📚 <b>Help Center</b>\n\n"
        "• New members verification (CAPTCHA)\n"
        "• Anti-spam and repeated-message protection\n"
        "• Raid Shield for sudden join floods\n\n"
        "Bot ko group mein admin permissions dena zaroori hai. "
        "Setup ke liye group admins se contact karo. 💬"
    )


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    # Telegram text reveal/loading animation before the actual welcome message.
    frames = [
        "╭──────────────╮\n"
        "   ⚔️ <b>ANI WORLD</b>\n"
        "   ▫️▫️▫️▫️▫️  0%\n"
        "╰──────────────╯\n"
        "<i>Starting up...</i>",
        "╭──────────────╮\n"
        "   ⚔️ <b>ANI WORLD</b>\n"
        "   🟩▫️▫️▫️▫️  20%\n"
        "╰──────────────╯\n"
        "<i>Loading modules...</i>",
        "╭──────────────╮\n"
        "   ⚔️ <b>ANI WORLD</b>\n"
        "   🟩🟩🟩▫️▫️  60%\n"
        "╰──────────────╯\n"
        "<i>Activating protection...</i>",
        "╭──────────────╮\n"
        "   ⚔️ <b>ANI WORLD</b>\n"
        "   🟩🟩🟩🟩🟩  100%\n"
        "╰──────────────╯\n"
        "<i>Ready! ✨</i>",
    ]
    sent = await message.answer(frames[0])
    for frame in frames[1:]:
        await asyncio.sleep(0.55)
        await sent.edit_text(frame)

    first_name = message.from_user.first_name if message.from_user else "there"
    await sent.edit_text(
        start_text(first_name),
        reply_markup=start_keyboard(),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(help_text())


@router.callback_query(F.data.startswith("start:"))
async def start_menu_callback(callback: CallbackQuery) -> None:
    action = callback.data.split(":", 1)[1] if callback.data else ""

    if action == "help" and callback.message:
        await callback.message.edit_text(help_text())
        await callback.answer()
        return

    placeholders = {
        "group": "Main Group ka link baad mein add karenge. 🔗",
        "owner": "Owner ka contact baad mein add karenge. 👤",
        "addgroup": "Add-to-group link baad mein add karenge. ➕",
    }
    if action in placeholders:
        await callback.answer(placeholders[action], show_alert=True)
        return

    await callback.answer("Unknown menu action.", show_alert=True)
