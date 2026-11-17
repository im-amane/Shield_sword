"""Owner-only operational dashboard and defensive intelligence views."""
from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)

from app.security.owner import is_owner
from app.handlers.typography import premium_text
from app.storage import (
    get_database_status, get_known_groups, get_owner_security_summary,
    get_recent_member_joins, get_recent_security_incidents,
)


def dashboard_text(bot_username: str | None, bot_id: int, owner_id: int) -> str:
    username = f"@{bot_username}" if bot_username else "Not available"
    stats = get_owner_security_summary()
    return premium_text(
        "⚙️ <b>Owner Control Center</b> 👑\n\n"
        "🟢 <b>Bot status:</b> Online\n"
        f"🤖 <b>Bot:</b> {escape(username)}\n"
        f"🆔 <b>Bot ID:</b> <code>{bot_id}</code>\n"
        f"🔐 <b>Owner ID:</b> <code>{owner_id}</code>\n\n"
        "📊 <b>Community overview</b>\n"
        f"👥 Groups monitored: <b>{stats['groups']}</b>\n"
        f"📥 Member joins (24h): <b>{stats['joins_24h']}</b>\n"
        f"🚨 Security incidents (24h): <b>{stats['incidents_24h']}</b>\n"
        f"🛡️ Active raid modes: <b>{stats['active_raids']}</b>\n\n"
        "<i>Choose a section below to inspect your shield systems.</i>"
    )


def dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛡️ Security", callback_data="owner_panel:security"),
            InlineKeyboardButton(text="👥 Groups", callback_data="owner_panel:groups"),
        ],
        [
            InlineKeyboardButton(text="🕵️ Activity", callback_data="owner_panel:activity"),
            InlineKeyboardButton(text="💾 Database", callback_data="owner_panel:database"),
        ],
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="owner_panel:refresh"),
            InlineKeyboardButton(text="✖️ Close", callback_data="owner_panel:close"),
        ],
    ])


def section_text(section: str) -> str:
    stats = get_owner_security_summary()
    if section == "security":
        incidents = get_recent_security_incidents(8)
        lines = [
            "🛡️ <b>Security Intelligence</b>\n\n",
            f"🚨 Incidents (24h): <b>{stats['incidents_24h']}</b>\n",
            f"⚔️ Raids detected (7d): <b>{stats['raids_7d']}</b>\n",
            f"🔇 Anti-spam actions (24h): <b>{stats['spam_24h']}</b>\n",
            f"🚧 Active raid modes: <b>{stats['active_raids']}</b>\n\n",
            "<b>Recent incidents</b>\n",
        ]
        if not incidents:
            lines.append("No security incidents recorded yet. ✨")
        for item in incidents:
            actor = f" · @{escape(item['username'])}" if item["username"] else ""
            target = f" · ID <code>{item['user_id']}</code>" if item["user_id"] else ""
            lines.append(
                f"• <b>{escape(item['severity'].upper())}</b> "
                f"{escape(item['kind'])} · {escape(item['chat_title'])}\n"
                f"  <code>{escape(item['created_at'])}</code>{actor}{target}\n"
                f"  {escape(item['details'])}\n"
            )
        return premium_text("".join(lines)[:3900])
    if section == "groups":
        groups = get_known_groups(20)
        lines = ["👥 <b>Monitored Groups</b>\n\n"]
        if not groups:
            lines.append("No groups have been observed yet. Add the bot to a group and allow it to see member updates.")
        for group in groups:
            lines.append(
                f"• <b>{escape(group['title'])}</b>\n"
                f"  ID: <code>{group['chat_id']}</code>\n"
                f"  Last seen: <code>{escape(group['last_seen'])}</code>\n"
            )
        return premium_text("".join(lines)[:3900])
    if section == "activity":
        joins = get_recent_member_joins(12)
        lines = ["🕵️ <b>Recent Member Activity</b>\n\n"]
        if not joins:
            lines.append("No member joins recorded yet.")
        for item in joins:
            profile = f"@{escape(item['username'])}" if item["username"] else escape(item["display_name"])
            lines.append(
                f"• {profile} · ID <code>{item['user_id']}</code>\n"
                f"  {escape(item['chat_title'])} · <code>{escape(item['joined_at'])}</code>\n"
            )
        lines.append("\n<i>Only public profile fields and join timestamps are stored. Message contents, phone numbers, IP addresses and device data are not collected.</i>")
        return premium_text("".join(lines)[:3900])
    if section == "database":
        db = get_database_status()
        status = "✅ Healthy" if db["integrity"] == "ok" else "⚠️ Needs attention"
        return premium_text(
            "💾 <b>Database & Backup</b>\n\n"
            f"Status: {status}\n"
            f"Integrity: <code>{escape(db['integrity'])}</code>\n"
            f"Tables: <b>{db['table_count']}</b>\n"
            f"Size: <b>{db['size_bytes'] / (1024 * 1024):.2f} MB</b>\n"
            f"Journal: <code>{escape(db['journal_mode'])}</code>\n\n"
            "Commands: <code>/dbstatus</code> · <code>/backup</code>\n"
            "Automatic verified backup is sent to the owner daily."
        )
    return "Unknown panel section."


def section_keyboard(section: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Dashboard", callback_data="owner_panel:home"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data=f"owner_panel:refresh_{section}"),
        ],
        [InlineKeyboardButton(text="✖️ Close", callback_data="owner_panel:close")],
    ])


def create_panel_router(owner_id: int | None) -> Router:
    router = Router(name="owner_panel")

    def authorized(user_id: int | None) -> bool:
        return is_owner(user_id, owner_id)

    async def render_home(message: Message) -> None:
        me = await message.bot.get_me()
        await message.answer(
            dashboard_text(me.username, me.id, owner_id or 0),
            reply_markup=dashboard_keyboard(),
        )

    @router.message(Command("panel"))
    async def panel_command(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not authorized(user_id):
            await message.answer(premium_text("🔒 <b>Private Area</b>\n\nThe owner dashboard is only available to the bot owner. 👑"))
            return
        await render_home(message)

    @router.callback_query(F.data.startswith("owner_panel:"))
    async def panel_callback(callback: CallbackQuery) -> None:
        if not authorized(callback.from_user.id if callback.from_user else None):
            await callback.answer(premium_text("Access denied. 🔒"), show_alert=True)
            return
        action = (callback.data or "").split(":", 1)[1]
        if action == "close":
            if callback.message:
                await callback.message.delete()
            await callback.answer(premium_text("Panel closed. Catch you later! 👋"))
            return
        if not callback.message:
            await callback.answer()
            return
        try:
            if action == "home":
                me = await callback.bot.get_me()
                await callback.message.edit_text(
                    dashboard_text(me.username, me.id, owner_id or 0),
                    reply_markup=dashboard_keyboard(),
                )
            elif action in {"security", "groups", "activity", "database"}:
                await callback.message.edit_text(
                    section_text(action), reply_markup=section_keyboard(action)
                )
            elif action == "refresh":
                me = await callback.bot.get_me()
                await callback.message.edit_text(
                    dashboard_text(me.username, me.id, owner_id or 0),
                    reply_markup=dashboard_keyboard(),
                )
            elif action == "refresh_section":
                current = "security"
                old = callback.message.text or ""
                for candidate in ("security", "groups", "activity", "database"):
                    if section_text(candidate).split("\n", 1)[0] in old:
                        current = candidate
                        break
                await callback.message.edit_text(
                    section_text(current), reply_markup=section_keyboard()
                )
            else:
                await callback.answer(premium_text("Unknown dashboard action. 😅"), show_alert=True)
                return
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise
        await callback.answer(premium_text("Updated. ✨"))

    return router
