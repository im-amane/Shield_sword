"""Basic bot health and start command."""
from __future__ import annotations

import asyncio
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from app.handlers.typography import premium_text

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

router = Router(name="start")


def start_text(first_name: str) -> str:
    safe_name = escape(first_name)
    return premium_text((
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
    ))


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌐 Main Group", callback_data="start:group"),
                InlineKeyboardButton(text="📚 Help", callback_data="start:help"),
            ],
            [
                InlineKeyboardButton(text="👤 Owner", callback_data="start:owner"),
                InlineKeyboardButton(text="✨ About Me", callback_data="start:about"),
            ],
            [
                InlineKeyboardButton(text="➕ Add Me to Your Group", callback_data="start:addgroup"),
            ],
        ]
    )


def help_text() -> str:
    return premium_text(
        "📚 <b>Ani World · Help Center</b> ✨\n\n"
        "Commands ko categories mein divide kiya gaya hai. Neeche kisi section par tap karo.\n\n"
        "🛡️ Group protection · 👮 Moderation\n"
        "👤 General · 👑 Owner tools\n\n"
        "<i>Har section mein command ka use aur zaroori permissions di gayi hain.</i>"
    )


def help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 General", callback_data="help:general"),
            InlineKeyboardButton(text="🛡️ Moderation", callback_data="help:moderation"),
        ],
        [
            InlineKeyboardButton(text="⚠️ Warnings", callback_data="help:warnings"),
            InlineKeyboardButton(text="🔗 Anti-Link", callback_data="help:antilink"),
        ],
        [
            InlineKeyboardButton(text="👑 Owner", callback_data="help:owner"),
            InlineKeyboardButton(text="⚙️ Permissions", callback_data="help:permissions"),
        ],
    ])


_HELP_SECTIONS = {
    "general": (
        "👤 <b>General Commands</b>\n\n"
        "/start - Open the welcome menu\n"
        "/help - Open this help center\n"
        "/id - Show your ID and chat ID\n"
        "/id (reply) - Show another member's ID"
    ),
    "moderation": (
        "🛡️ <b>Group Moderation</b>\n\n"
        "/mute [10m] - Mute a member (reply)\n"
        "/unmute - Unmute a member (reply)\n"
        "/ban - Ban a member (reply)\n"
        "/unban USER_ID - Remove a ban\n"
        "/kick - Remove a member (reply)\n"
        "/purge - Delete messages from replied message onward\n\n"
        "<i>Requires admin rights and the bot's Ban Users / Delete Messages permissions.</i>"
    ),
    "warnings": (
        "⚠️ <b>Warning System</b>\n\n"
        "/warn - Give a warning (reply)\n"
        "/warnings - Check a member's warnings (reply)\n"
        "/resetwarn - Clear a member's warnings (reply)\n\n"
        "At 3 warnings, the member is automatically muted for 10 minutes. "
        "Requires Ban Users permission."
    ),
    "antilink": (
        "🔗 <b>Anti-Link Protection</b>\n\n"
        "/antilink - Check current status\n"
        "/antilink on - Enable link protection\n"
        "/antilink off - Disable link protection\n"
        "/allowdomain example.com - Trust a domain\n"
        "/removedomain example.com - Remove a trusted domain\n\n"        "/badwords - Check or configure the bad-words filter\n"
        "/badwords on|off - Toggle the filter\n"
        "/addword phrase - Add a blocked word or phrase\n"
        "/removeword phrase - Remove a blocked word or phrase\n\n"
        "Group admins are exempt. Telegram invite links cannot be allowlisted. "
        "Requires Delete Messages permission."
    ),
    "owner": (
        "👑 <b>Owner Commands</b>\n\n"
        "/owner - Verify owner access\n"
        "/panel - Open the owner control center\n"
        "/raidstatus - Check raid shield status\n"
        "/raidoff - Disable active raid mode\n"
        "/audit - View recent security events\n"
        "/backup - Send a private database backup\n\n"
        "<i>These commands are restricted to the configured bot owner.</i>"
    ),
    "permissions": (
        "⚙️ <b>Bot Permissions</b>\n\n"
        "Promote Ani World as an administrator in your group.\n\n"
        "• <b>Delete Messages:</b> Anti-link and purge\n"
        "• <b>Ban Users:</b> Mute, ban, kick, warnings and verification\n\n"
        "Some commands also require the person using them to be a group admin."
    ),
}


def help_section_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ All Help Sections", callback_data="help:home")
    ]])


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
    sent = await message.answer(premium_text(frames[0]))
    for frame in frames[1:]:
        await asyncio.sleep(0.55)
        await sent.edit_text(premium_text(frame))

    first_name = message.from_user.first_name if message.from_user else "there"
    await sent.edit_text(
        start_text(first_name),
        reply_markup=start_keyboard(),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(premium_text(help_text()), reply_markup=help_keyboard())


@router.callback_query(F.data.startswith("help:"))
async def help_section_callback(callback: CallbackQuery) -> None:
    section = callback.data.split(":", 1)[1] if callback.data else ""
    if not callback.message:
        await callback.answer()
        return
    if section == "home":
        await callback.message.edit_text(premium_text(help_text()), reply_markup=help_keyboard())
        await callback.answer()
        return
    content = _HELP_SECTIONS.get(section)
    if content is None:
        await callback.answer(premium_text("Unknown help section. 😅"), show_alert=True)
        return
    await callback.message.edit_text(
        premium_text(content),
        reply_markup=help_section_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("start:"))
async def start_menu_callback(callback: CallbackQuery) -> None:
    action = callback.data.split(":", 1)[1] if callback.data else ""

    if action == "help" and callback.message:
        await callback.message.edit_text(help_text(), reply_markup=help_keyboard())
        await callback.answer()
        return

    placeholders = {
        "group": premium_text("Main Group ka link baad mein add karenge. 🔗"),
        "owner": premium_text("Owner ka contact baad mein add karenge. 👤"),
        "addgroup": premium_text("Add-to-group link baad mein add karenge. ➕"),
    }
    if action in placeholders:
        await callback.answer(placeholders[action], show_alert=True)
        return

    await callback.answer(premium_text("Unknown menu action. 😅"), show_alert=True)
