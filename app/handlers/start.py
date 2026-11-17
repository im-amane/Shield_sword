"""Basic bot health and start command."""
from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

router = Router(name="start")


def start_keyboard() -> InlineKeyboardMarkup:
    """Main menu shown under the start message."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 Help", callback_data="start:help"),
                InlineKeyboardButton(text="🛡️ Security", callback_data="start:security"),
            ],
            [
                InlineKeyboardButton(text="👑 Owner Panel", callback_data="start:panel"),
                InlineKeyboardButton(text="✖️ Close", callback_data="start:close"),
            ],
        ]
    )


def start_text() -> str:
    return (
        "⚔️ <b>Ani World 剣 Management Bot</b>\n\n"
        "Yo! 👋 Main online hoon, group ki security ka dhyaan rakh raha hoon. 🛡️\n"
        "Admins, owner controls ke liye /panel use karo. Baaki sab, chill and enjoy! ✨"
    )


def help_text() -> str:
    return (
        "📚 <b>Help Center</b>\n\n"
        "/start  • Bot ko start karo\n"
        "/help  • Help menu kholo\n"
        "/panel  • Owner control room (owner only)\n"
        "/raidstatus  • Raid shield status (owner only)\n"
        "/raidoff  • Raid shield band karo (owner only)\n\n"
        "Kisi issue ke liye group admin se contact karo. 💬"
    )


def security_text() -> str:
    return (
        "🛡️ <b>Group Security</b>\n\n"
        "• New members ke liye verification challenge\n"
        "• Spam aur repeated messages par automatic action\n"
        "• Sudden join raids par Raid Shield\n\n"
        "Bot ko required admin permissions dena zaroori hai. 🔐"
    )


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    # A short, restrained edit sequence creates a text-only typing/reveal effect.
    animation = [
        "⚔️ <b>Ani World 剣</b>\n\n<i>Initializing security systems...</i> ⚙️",
        "⚔️ <b>Ani World 剣</b>\n\n🛡️ <i>Checking group protection...</i>",
        "⚔️ <b>Ani World 剣</b>\n\n✨ <i>All set. Welcome!</i>",
    ]
    sent = await message.answer(animation[0])
    for frame in animation[1:]:
        await asyncio.sleep(0.45)
        await sent.edit_text(frame)

    await sent.edit_text(start_text(), reply_markup=start_keyboard())


@router.message(F.text == "/help")
async def help_command(message: Message) -> None:
    await message.answer(help_text(), reply_markup=start_keyboard())


@router.callback_query(F.data.startswith("start:"))
async def start_menu_callback(callback: CallbackQuery) -> None:
    action = callback.data.split(":", 1)[1] if callback.data else ""

    if action == "close":
        if callback.message:
            await callback.message.delete()
        await callback.answer("Menu closed. 👋")
        return

    if action == "panel":
        await callback.answer("Owner controls ke liye /panel use karo.", show_alert=True)
        return

    if callback.message:
        if action == "help":
            await callback.message.edit_text(help_text(), reply_markup=back_keyboard())
        elif action == "security":
            await callback.message.edit_text(security_text(), reply_markup=back_keyboard())
        elif action == "home":
            await callback.message.edit_text(start_text(), reply_markup=start_keyboard())
        else:
            await callback.answer("Unknown menu action.", show_alert=True)
            return

    await callback.answer()


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Start", callback_data="start:home")]
        ]
    )
