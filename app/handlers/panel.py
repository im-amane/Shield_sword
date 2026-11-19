"""Owner-only operational dashboard and defensive intelligence views."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile, CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, Message,
)

from app.security.owner import is_owner
from app.backup_crypto import backup_key_status, encrypt_backup
from app.handlers.typography import premium_text
from app.storage import (
    create_database_backup, get_audit_events, get_database_status,
    get_known_groups, get_owner_security_summary, get_recent_member_joins,
    get_recent_security_incidents, get_last_automatic_backup_at,
    get_last_daily_report_at,
)


def dashboard_text(bot_username: str | None, bot_id: int, owner_id: int) -> str:
    username = f"@{bot_username}" if bot_username else "Not available"
    stats = get_owner_security_summary()
    return premium_text(
        "🛡️ <b>ANI WORLD · GUARDIAN HQ</b> 👑\n"
        "<i>Your community. Our watch.</i>\n\n"
        "╭─ <b>GUARDIAN STATUS</b>\n"
        "│ 🟢 <b>Online and protecting</b>\n"
        f"│ 🤖 {escape(username)}\n"
        f"│ 🆔 <code>{bot_id}</code>\n"
        f"│ 👑 Owner: <code>{owner_id or 'Not configured'}</code>\n"
        "╰────────────────\n\n"
        "🏠 <b>COMMUNITY AT A GLANCE</b>\n"
        f"👥 Groups under watch: <b>{stats['groups']}</b>\n"
        f"🤝 Members welcomed (24h): <b>{stats['joins_24h']}</b>\n"
        f"🚨 Security incidents (24h): <b>{stats['incidents_24h']}</b>\n"
        f"⚔️ Active lockdowns: <b>{stats['active_raids']}</b>\n\n"
        "<i>Select a control below.</i>"
    )


def dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛡️ Protection", callback_data="owner_panel:security"),
            InlineKeyboardButton(text="🏠 Communities", callback_data="owner_panel:groups"),
        ],
        [
            InlineKeyboardButton(text="🤝 Member Watch", callback_data="owner_panel:activity"),
            InlineKeyboardButton(text="📜 Security History", callback_data="owner_panel:audit"),
        ],
        [
            InlineKeyboardButton(text="💾 System Health", callback_data="owner_panel:database"),
            InlineKeyboardButton(text="📦 Secure Backup", callback_data="owner_panel:backup"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Configuration", callback_data="owner_panel:configuration"),
            InlineKeyboardButton(text="🤖 Automations", callback_data="owner_panel:automation"),
        ],
        [
            InlineKeyboardButton(text="📚 Command Index", callback_data="owner_panel:commands"),
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
    if section == "audit":
        events = get_audit_events(15)
        lines = ["📜 <b>Owner Audit Log</b>\n\n"]
        if not events:
            lines.append("No audit events recorded yet.")
        for event in events:
            actor = f"<code>{event['actor_id']}</code>" if event["actor_id"] else "System"
            target = f" → <code>{event['target_id']}</code>" if event["target_id"] else ""
            detail = f" · {escape(str(event['details']))}" if event["details"] else ""
            lines.append(
                f"• <code>{escape(event['created_at'])}</code> · "
                f"<b>{escape(event['action'])}</b>\n"
                f"  Group: <code>{event['chat_id']}</code> · Actor: {actor}{target}{detail}\n"
            )
        return premium_text("".join(lines)[:3900])
    if section == "database":
        db = get_database_status()
        last_backup = get_last_automatic_backup_at()
        last_report = get_last_daily_report_at()
        backup_label = (
            datetime.fromtimestamp(last_backup, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if last_backup is not None else "Not delivered yet"
        )
        report_label = (
            datetime.fromtimestamp(last_report, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if last_report is not None else "Not delivered yet"
        )
        status = "✅ Healthy" if db["integrity"] == "ok" else "⚠️ Needs attention"
        return premium_text(
            "💾 <b>Database & Backup</b>\n\n"
            f"Status: {status}\n"
            f"Integrity: <code>{escape(db['integrity'])}</code>\n"
            f"Tables: <b>{db['table_count']}</b>\n"
            f"Size: <b>{db['size_bytes'] / (1024 * 1024):.2f} MB</b>\n"
            f"Journal: <code>{escape(db['journal_mode'])}</code>\n"
            f"Last automatic backup: <code>{backup_label}</code>\n"
            f"Last daily report: <code>{report_label}</code>\n\n"
            "Commands: <code>/dbstatus</code> · <code>/backup</code>\n"
            "Automatic verified backup runs every 7 days; the daily security report runs every 24 hours."
        )
    if section == "configuration":
        key = backup_key_status()
        key_state = "✅ Configured" if key["configured"] else "❌ Missing or invalid"
        fingerprint = escape(str(key["fingerprint"]))
        required = ("BOT_TOKEN", "OWNER_ID", "DATABASE_PATH")
        optional = ("MAIN_GROUP_URL", "OWNER_CONTACT_URL")
        def state(name: str) -> str:
            return "✅ Set" if os.getenv(name, "").strip() else "⚠️ Not set"
        lines = [
            "⚙️ <b>Secure Configuration</b>\n\n",
            "<b>Secret status</b>\n",
            f"• Telegram bot token: {state('BOT_TOKEN')} (never displayed)\n",
            f"• Owner ID: {state('OWNER_ID')}\n",
            f"• Backup encryption: {key_state}\n",
            f"• Key fingerprint: <code>{fingerprint}</code>\n\n",
            "<b>Runtime settings</b>\n",
        ]
        lines.extend(f"• <code>{name}</code>: {state(name)}\n" for name in required + optional)
        lines.append(
            "\n🔐 Secret values are never sent to Telegram. The fingerprint helps identify the active backup key. "
            "Keep an offline recovery copy. Rotate keys through your hosting provider, then retain the old key for old backups."
        )
        return premium_text("".join(lines))
    if section == "automation":
        last_backup = get_last_automatic_backup_at()
        last_report = get_last_daily_report_at()
        backup_label = datetime.fromtimestamp(last_backup, timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if last_backup else "Pending first delivery"
        report_label = datetime.fromtimestamp(last_report, timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if last_report else "Pending first delivery"
        return premium_text(
            "🤖 <b>Automation Monitor</b>\n\n"
            "• CAPTCHA expiry worker: <b>Running with bot process</b>\n"
            "• Weekly encrypted backup: <b>Every 7 days</b>\n"
            f"  Last success: <code>{backup_label}</code>\n"
            "• Daily security report: <b>Every 24 hours</b>\n"
            f"  Last success: <code>{report_label}</code>\n"
            "• Raid protection: <b>Automatic detection</b>\n"
            "• Permission watchdog: <b>Event-driven</b>\n\n"
            "A timestamp confirms the last successful delivery, not merely that a task was scheduled."
        )
    if section == "commands":
        return premium_text(
            "📚 <b>Guardian Command Index</b>\n\n"
            "<b>Owner & diagnostics</b>\n"
            "/start · /help · /owner · /panel · /audit · /dbstatus · /backup · /security · /checkpermissions · /id\n\n"
            "<b>Moderation</b>\n"
            "/mute · /unmute · /ban · /unban · /kick · /purge · /warn · /warnings · /resetwarn\n\n"
            "<b>Protection settings</b>\n"
            "/antilink · /allowdomain · /removedomain · /badwords · /addword · /removeword\n"
            "/raidstatus · /raidoff · /channelprotect\n\n"
            "Only commands actually registered in this build are listed here. Group permissions and command scope still apply."
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


def can_access_panel_callback(
    user_id: int | None, owner_id: int | None, chat_type: str
) -> bool:
    """Allow owner-panel callbacks only from the configured owner in private chat."""
    return chat_type == "private" and is_owner(user_id, owner_id)


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
        if message.chat.type != "private":
            await message.answer(premium_text("🔒 Open the owner panel in my private chat so security details stay private."))
            return
        if not authorized(user_id):
            await message.answer(premium_text("🔒 <b>Private Area</b>\n\nThe owner dashboard is only available to the bot owner. 👑"))
            return
        await render_home(message)

    @router.callback_query(F.data.startswith("owner_panel:"))
    async def panel_callback(callback: CallbackQuery) -> None:
        if not callback.message:
            await callback.answer()
            return
        user_id = callback.from_user.id if callback.from_user else None
        if not can_access_panel_callback(user_id, owner_id, callback.message.chat.type):
            await callback.answer(
                premium_text("Access denied. Open the owner panel in private chat. 🔒"),
                show_alert=True,
            )
            return
        action = (callback.data or "").split(":", 1)[1]
        if action == "close":
            await callback.message.delete()
            await callback.answer(premium_text("Panel closed. 👋"))
            return
        try:
            if action == "home" or action == "refresh":
                me = await callback.bot.get_me()
                await callback.message.edit_text(
                    dashboard_text(me.username, me.id, owner_id or 0),
                    reply_markup=dashboard_keyboard(),
                )
            elif action in {"security", "groups", "activity", "audit", "database", "configuration", "automation", "commands"}:
                await callback.message.edit_text(
                    section_text(action), reply_markup=section_keyboard(action)
                )
            elif action.startswith("refresh_"):
                current = action.removeprefix("refresh_")
                if current not in {"security", "groups", "activity", "audit", "database", "configuration", "automation", "commands"}:
                    current = "security"
                await callback.message.edit_text(
                    section_text(current), reply_markup=section_keyboard(current)
                )
            elif action == "backup":
                snapshot = encrypt_backup(create_database_backup())
                await callback.bot.send_document(
                    chat_id=owner_id,
                    document=BufferedInputFile(
                        snapshot, filename="aniworld-security-backup.sqlite3.awb"
                    ),
                    caption=premium_text(
                        "📦 <b>Encrypted Backup Complete</b>\n\n"
                        "AES-256-GCM encrypted database snapshot attached. Keep it private. 🔐"
                    ),
                )
            else:
                await callback.answer(premium_text("Unknown dashboard action. 😅"), show_alert=True)
                return
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise
        await callback.answer(premium_text("Updated. ✨"))

    return router
