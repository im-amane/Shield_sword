""""Basic bot health and start command."""
from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

router = Router(name="start")


def start_text() -> str:
    return (
        "⚔️ <b>Ani World 剣</b>\\n\\n"
        "Welcome! 👋 Main tumhare group ko safe aur spam-free rakhne ke liye ready hoon. 🛡️\\n"
        "Verification, anti-spam aur raid protection. Sab kuch ek hi jagah! ✨"
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
        "📚 <b>Help Center</b>\\n\\n"
        "• New members verification (CAPTCHA)\\n"
        "• Anti-spam and repeated-message protection\\n"
        "• Raid Shield for sudden join floods\\n\\n"
        "Bot ko group mein admin permissions dena zaroori hai. "
        "Setup ke liye group admins se contact karo. 💬"
    )


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    # Telegram text reveal/loading animation before the actual welcome message.
    frames = [
        "╭──────────────╮\\n"
        "   ⚔️ <b>ANI WORLD</b>\\n"
        "   ▫️▫️▫️▫️▫️  0%\\n"
        "╰──────────────╯\\n"
        "<i>Starting up...</i>",
        "╭──────────────╮\\n"
        "   ⚔️ <b>ANI WORLD</b>\\n"
        "   🟩▫️▫️▫️▫️  20%\\n"
        "╰──────────────╯\\n"
        "<i>Loading modules...</i>",
        "╭──────────────╮\\n"
        "   ⚔️ <b>ANI WORLD</b>\\n"
        "   🟩🟩🟩▫️▫️  60%\\n"
        "╰──────────────╯\\n"
        "<i>Activating protection...</i>",
        "╭──────────────╮\\n"
        "   ⚔️ <b>ANI WORLD</b>\\n"
        "   🟩🟩🟩🟩🟩  100%\\n"
        "╰──────────────╯\\n"
        "<i>Ready! ✨</i>",
    ]
    sent = await message.answer(frames[0])
    for frame in frames[1:]:
        await asyncio.sleep(0.55)
        await sent.edit_text(frame)

    await sent.edit_text(
        start_text(),
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
"