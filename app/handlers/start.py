"""Basic bot health and start command."""
from __future__ import annotations

import os
from html import escape
from urllib.parse import urlsplit
from pathlib import Path

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from app.handlers.typography import premium_text

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    BufferedInputFile,
)

router = Router(name="start")

_WELCOME_IMAGE = Path(__file__).resolve().parents[2] / "assets" / "sentinel_anime.jpg"


async def send_welcome_photo(message: Message, caption: str, keyboard: InlineKeyboardMarkup) -> None:
    """Send the actual anime artwork and welcome copy as one Telegram photo message."""
    image_bytes = _WELCOME_IMAGE.read_bytes()
    await message.answer_photo(
        BufferedInputFile(image_bytes, filename="sentinel-anime-guardian.jpg"),
        caption=caption,
        reply_markup=keyboard,
    )



def start_text(first_name: str) -> str:
    """Private welcome for an individual user."""
    safe_name = escape(first_name, quote=True)
    return premium_text((
        f"Welcome, {safe_name}. 👋\n\n"
        "🛡️ <b>Sentinel · Ani World 剣</b>\n"
        "<i>Autonomous Community Security & Management</i>\n\n"
        "I am Sentinel, the security and management system built for Ani World communities. "
        "I work quietly in the background to help keep groups and channels safer.\n\n"
        "╭─ <b>SECURITY SYSTEMS</b>\n"
        "│ 🧩 New-member verification\n"
        "│ 🚫 Anti-spam and link protection\n"
        "│ 🧠 AI safety checks for text and captions\n"
        "│ ⚔️ Raid and unusual-join monitoring\n"
        "│ ⚖️ Moderation and security audit logs\n"
        "│ 🔐 Owner reports and encrypted backups\n"
        "╰──────────────────\n\n"
        "Ordinary photos, videos, GIFs, documents and other normal media are not blanket-deleted. "
        "AI Guard checks text and captions; it does not verify visual copyright ownership.\n\n"
        "<i>Protection with control. Moderation with context.</i>\n\n"
        "Choose a section below to explore Sentinel."
    ))


def group_start_text(chat_title: str) -> str:
    """A separate introduction intended for a group or supergroup."""
    safe_title = escape(chat_title or "this community", quote=True)
    return premium_text((
        f"🛡️ <b>Sentinel is online in {safe_title}</b>\n"
        "<i>Ani World 剣 · Community Security & Management</i>\n\n"
        "This group is connected to Sentinel's automated protection system. "
        "I monitor suspicious activity and apply the configured safety rules.\n\n"
        "╭─ <b>ACTIVE PROTECTION</b>\n"
        "│ 🧩 New-member verification\n"
        "│ 🚫 Anti-spam and link filtering\n"
        "│ 🧠 AI safety checks for text and captions\n"
        "│ ⚔️ Raid and join-surge monitoring\n"
        "│ ⚖️ Moderation and incident logging\n"
        "╰──────────────────\n\n"
        "Admins: use /security to review protection status and /checkpermissions "
        "to verify Sentinel's Telegram permissions. Use /help for the command guide.\n\n"
        "<i>Normal photos, videos and other media are not blanket-deleted.</i>"
    ))


def group_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 Help Center", callback_data="start:help"),
            InlineKeyboardButton(text="🛡️ About Sentinel", callback_data="start:about"),
        ],
        [InlineKeyboardButton(text="✖️ Cancel", callback_data="ui:cancel")],
    ])


def _public_url(name: str) -> str | None:
    """Accept only absolute HTTPS links from optional deployment configuration."""
    value = os.getenv(name, "").strip()
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return value


def start_keyboard(bot_username: str | None = None) -> InlineKeyboardMarkup:
    main_url = _public_url("MAIN_GROUP_URL")
    owner_url = _public_url("OWNER_CONTACT_URL")
    add_url = (
        f"https://t.me/{bot_username}?startgroup=true"
        if bot_username and bot_username.replace("_", "").isalnum()
        else None
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Community",
                    url=main_url,
                ) if main_url else InlineKeyboardButton(
                    text="🏠 Community", callback_data="start:group"
                ),
                InlineKeyboardButton(text="📚 Help Center", callback_data="start:help"),
            ],
            [
                InlineKeyboardButton(
                    text="👑 Owner", url=owner_url
                ) if owner_url else InlineKeyboardButton(
                    text="👑 Owner", callback_data="start:owner"
                ),
                InlineKeyboardButton(text="🛡️ About Sentinel", callback_data="start:about"),
            ],
            [
                InlineKeyboardButton(
                    text="➕ Add Sentinel to Group", url=add_url
                ) if add_url else InlineKeyboardButton(
                    text="➕ Add Sentinel to Group", callback_data="start:addgroup"
                ),
            ],
            [InlineKeyboardButton(text="✖️ Cancel", callback_data="ui:cancel")],
        ]
    )


def help_text() -> str:
    return premium_text(
        "📚 <b>Sentinel · Help Center</b> ✨\n\n"
        "Sentinel ke group security, moderation aur owner controls yahan milenge.\n\n"
        "🛡️ Automated protection · 🧠 AI safety checks\n"
        "👮 Moderation · 👑 Owner control center\n\n"
        "AI Guard checks group messages and channel posts containing text or captions when enabled. Normal media is not blanket-deleted.\n\n"
        "<i>Har section mein command usage aur required permissions di gayi hain.</i>"
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
        [
            InlineKeyboardButton(text="⬅️ Main Menu", callback_data="help:menu"),
            InlineKeyboardButton(text="✖️ Cancel", callback_data="ui:cancel"),
        ],
    ])


_HELP_SECTIONS = {
    "general": (
        "👤 <b>General Commands</b>\n\n"
        "/start - Open the welcome menu\n"
        "/help - Open this help center\n"
        "/id - Show your ID and chat ID\n"
        "/id USER_ID - Look up a member profile\n"
        "/id (reply) - Show another member's profile card\n"
        "/checkpermissions - Check Sentinel's admin rights in this group\n"
        "/security - View this group's protection status"
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
        "/unwarn - Remove one warning (reply)\n"
        "/resetwarn - Clear all warnings (reply)\n\n"
        "At 3 warnings, the member is automatically muted for 10 minutes. "
        "Requires Ban Users permission."
    ),
    "antilink": (
        "🔗 <b>Anti-Link Protection</b>\n\n"
        "/antilink - Check current status\n"
        "/antilink on - Enable link protection\n"
        "/antilink off - Disable link protection\n"
        "/allowdomain example.com - Trust a domain\n"
        "/removedomain example.com - Remove a trusted domain\n\n"
        "/badwords - Check or configure the bad-words filter\n"
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
        "/backup - Send a private database backup\n"
        "/aitest - Test the NVIDIA AI Guard safety endpoint (private chat)\n\n"
        "<i>These commands are restricted to the configured bot owner.</i>"
    ),
    "permissions": (
        "⚙️ <b>Bot Permissions</b>\n\n"
        "/security - View protection status (group admins)\n"
        "/checkpermissions - Check the bot's admin rights\n\n"
        "Promote Sentinel as an administrator in your group.\n\n"
        "• <b>Delete Messages:</b> Anti-link and purge\n"
        "• <b>Ban Users:</b> Mute, ban, kick, warnings and verification\n\n"
        "Some commands also require the person using them to be a group admin."
    ),
}


def help_section_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Help Center", callback_data="help:home"),
            InlineKeyboardButton(text="✖️ Cancel", callback_data="ui:cancel"),
        ],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="help:menu")],
    ])


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    bot_identity = await message.bot.get_me()
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await send_welcome_photo(
            message,
            group_start_text(message.chat.title or "this community"),
            group_start_keyboard(),
        )
        return

    first_name = message.from_user.first_name if message.from_user else "there"
    await send_welcome_photo(
        message,
        start_text(first_name),
        start_keyboard(bot_identity.username),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await send_category_card(message, "help", "Help Center", "Commands and navigation")
    await message.answer(premium_text(help_text()), reply_markup=help_keyboard())


@router.callback_query(F.data.startswith("help:"))
async def help_section_callback(callback: CallbackQuery) -> None:
    section = callback.data.split(":", 1)[1] if callback.data else ""
    if not callback.message:
        await callback.answer()
        return
    if section == "home":
        await callback.message.delete()
        await send_category_card(callback.message, "help", "Help Center", "Commands and navigation")
        await callback.message.answer(premium_text(help_text()), reply_markup=help_keyboard())
        await callback.answer()
        return
    if section == "menu":
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            text = group_start_text(callback.message.chat.title or "this community")
            keyboard = group_start_keyboard()
        else:
            identity = await callback.bot.get_me()
            text = start_text(callback.from_user.first_name or "there")
            keyboard = start_keyboard(identity.username)
        await callback.message.delete()
        await send_welcome_photo(callback.message, text, keyboard)
        await callback.answer("Main menu")
        return
    content = _HELP_SECTIONS.get(section)
    if content is None:
        await callback.answer(premium_text("That help section is unavailable. Please reopen /help."), show_alert=True)
        return
    await callback.message.delete()
    await send_category_card(callback.message, "help", "Help · " + section.title(), "Command reference")
    await callback.message.answer(
        premium_text(content),
        reply_markup=help_section_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("start:"))
async def start_menu_callback(callback: CallbackQuery) -> None:
    action = callback.data.split(":", 1)[1] if callback.data else ""

    if action == "help" and callback.message:
        await callback.message.delete()
        await send_category_card(callback.message, "help", "Help Center", "Commands and navigation")
        await callback.message.answer(help_text(), reply_markup=help_keyboard())
        await callback.answer()
        return

    if action == "about":
        await callback.answer(
            premium_text(
                "🛡️ Sentinel🛡️剣 · Ani World\n\n"
                "Automated group and channel security: verification, anti-spam, AI safety checks for text/captions, raid monitoring and moderation. Normal media stays allowed."
            ),
            show_alert=True,
        )
        return

    missing_links = {
        "group": ("MAIN_GROUP_URL", "Main Group link is not configured yet. 🔗"),
        "owner": ("OWNER_CONTACT_URL", "Owner contact link is not configured yet. 👤"),
        "addgroup": ("", "Open /start in private chat to access the add-to-group link. ➕"),
    }
    if action in missing_links:
        variable, message_text = missing_links[action]
        if variable and _public_url(variable):
            await callback.answer("Open the configured link from the menu. 🔗")
        else:
            await callback.answer(premium_text(message_text), show_alert=True)
        return

    await callback.answer(premium_text("This menu action is unavailable. Please reopen /start."), show_alert=True)


@router.callback_query(F.data == "ui:cancel")
async def cancel_inline_menu(callback: CallbackQuery) -> None:
    """Dismiss the current inline menu without deleting the surrounding message."""
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Menu cancelled.")
