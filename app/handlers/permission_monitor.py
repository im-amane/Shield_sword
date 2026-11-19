"""Owner alerts for Guardian bot membership and admin-right changes."""
from __future__ import annotations

from html import escape

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import ChatMemberUpdated

from app.handlers.typography import premium_text
from app.storage import record_audit_event, record_security_incident, register_group


_REQUIRED_RIGHTS = (
    ("can_delete_messages", "Delete Messages"),
    ("can_restrict_members", "Ban Users / Restrict Members"),
)


def permission_snapshot(member) -> tuple[str, bool, bool]:
    """Return role and the two critical protection rights."""
    status = member.status.value if hasattr(member.status, "value") else str(member.status)
    return (
        status,
        bool(getattr(member, "can_delete_messages", False)),
        bool(getattr(member, "can_restrict_members", False)),
    )


def permission_change_summary(update: ChatMemberUpdated) -> list[str]:
    """Describe meaningful role or required-right changes between old and new state."""
    old = permission_snapshot(update.old_chat_member)
    new = permission_snapshot(update.new_chat_member)
    changes: list[str] = []
    if old[0] != new[0]:
        changes.append(f"Bot role changed: {old[0]} → {new[0]}")
    for index, (_, label) in enumerate(_REQUIRED_RIGHTS, start=1):
        if old[index] != new[index]:
            state = "granted" if new[index] else "REMOVED"
            changes.append(f"{label}: {state}")
    if not changes:
        return []
    missing = []
    if new[0] not in (ChatMemberStatus.ADMINISTRATOR.value, ChatMemberStatus.CREATOR.value):
        missing.append("Bot is no longer an administrator")
    else:
        if new[0] == ChatMemberStatus.ADMINISTRATOR.value:
            if not new[1]:
                missing.append("Delete Messages is missing")
            if not new[2]:
                missing.append("Ban Users / Restrict Members is missing")
    if missing:
        changes.append("Protection impact: " + "; ".join(missing))
    elif new[0] in (ChatMemberStatus.ADMINISTRATOR.value, ChatMemberStatus.CREATOR.value):
        changes.append("Critical protection permissions are available")
    return changes


def create_permission_monitor_router(owner_id: int | None) -> Router:
    """Notify the configured owner when Guardian's group permissions change."""
    router = Router(name="permission_monitor")

    @router.my_chat_member()
    async def bot_membership_changed(update: ChatMemberUpdated) -> None:
        if update.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
            return
        if update.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            register_group(update.chat.id, update.chat.title or "Telegram group")
        changes = permission_change_summary(update)
        if not changes:
            return
        chat_title = escape(update.chat.title or "Telegram chat")
        chat_id = update.chat.id
        record_audit_event(chat_id, "bot_permission_change", details="; ".join(changes))
        critical = any("REMOVED" in item or "no longer an administrator" in item or "missing" in item for item in changes)
        record_security_incident(
            chat_id=chat_id,
            chat_title=update.chat.title or "Telegram chat",
            kind="bot_permission_loss" if critical else "bot_permission_change",
            severity="high" if critical else "low",
            details="; ".join(changes),
        )
        if owner_id is None:
            return
        heading = "🚨 <b>Guardian Permission Alert</b>" if critical else "🛡️ <b>Guardian Permission Update</b>"
        body = (
            f"{heading}\n\n"
            f"Chat: <b>{chat_title}</b>\n"
            f"Chat ID: <code>{chat_id}</code>\n\n"
            + "\n".join(f"• {escape(item)}" for item in changes)
            + "\n\nRun /checkpermissions in the group after restoring the required rights."
        )
        try:
            await update.bot.send_message(chat_id=owner_id, text=premium_text(body))
        except Exception:
            # Do not retry indefinitely or crash the update dispatcher if owner DMs are closed.
            return

    return router
