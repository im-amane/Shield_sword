"""Owner-only identity check command."""
from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import BufferedInputFile, Message

from app.security.owner import is_owner
from app.backup_crypto import encrypt_backup
from app.handlers.typography import premium_text
from app.storage import create_database_backup, get_audit_events, get_database_status


def create_owner_router(owner_id: int | None) -> Router:
    """Create owner command handlers bound to the configured owner ID."""
    router = Router(name="owner")

    @router.message(Command("owner"))
    async def owner_command(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not is_owner(user_id, owner_id):
            await message.answer(premium_text("🔒 <b>Owner Access</b>\n\nThis area is reserved for the bot owner.\nAuthorization required. 👑"))
            return

        await message.answer(premium_text(
            "👑 <b>Welcome back, Owner!</b>\n\n"
            "Your identity is verified and owner access is ready.\n"
            "Use /panel to open your control center. ⚙️"
        ))

    @router.message(Command("audit"))
    async def audit_command(message: Message) -> None:
        if message.chat.type != ChatType.PRIVATE:
            await message.answer(premium_text("🔒 Use /audit in my private chat to keep security records private."))
            return
        user_id = message.from_user.id if message.from_user else None
        if not is_owner(user_id, owner_id):
            await message.answer(premium_text("🔒 <b>Owner Access Only</b>"))
            return
        events = get_audit_events(20)
        if not events:
            await message.answer(premium_text("📋 <b>Security Audit</b>\n\nNo events recorded yet."))
            return
        lines = ["📋 <b>Recent Security Events</b>\n"]
        for event in events:
            target = f" → <code>{event['target_id']}</code>" if event["target_id"] else ""
            actor = f"<code>{event['actor_id']}</code>" if event["actor_id"] else "System"
            details = f" · {escape(str(event['details']))}" if event["details"] else ""
            lines.append(f"• <code>{event['created_at']}</code> · {escape(str(event['action']))}\n  Actor: {actor}{target}{details}")
        await message.answer(premium_text("\n".join(lines)[:3900]))

    @router.message(Command("dbstatus"))
    async def dbstatus_command(message: Message) -> None:
        if message.chat.type != ChatType.PRIVATE:
            await message.answer(premium_text("🔒 Use /dbstatus in my private chat to keep storage details private."))
            return
        user_id = message.from_user.id if message.from_user else None
        if not is_owner(user_id, owner_id):
            await message.answer(premium_text("🔒 <b>Owner Access Only</b>"))
            return
        try:
            status = get_database_status()
            size_mb = status["size_bytes"] / (1024 * 1024)
            state = "✅ Healthy" if status["integrity"] == "ok" else "⚠️ Check required"
            await message.answer(premium_text(
                "🛡️ <b>Database Health</b>\n\n"
                f"Status: {state}\n"
                f"Integrity: <code>{escape(status['integrity'])}</code>\n"
                f"Tables: <code>{status['table_count']}</code>\n"
                f"Size: <code>{size_mb:.2f} MB</code>\n"
                f"Journal: <code>{escape(status['journal_mode'])}</code>\n"
                f"Storage: <code>{escape(status['path'])}</code>"
            ))
        except Exception:
            await message.answer(premium_text("❌ <b>Database Check Failed</b>"))
            raise

    @router.message(Command("backup"))
    async def backup_command(message: Message) -> None:
        if message.chat.type != ChatType.PRIVATE:
            await message.answer(premium_text("🔒 Use /backup in my private chat. Database files must never be posted in a group."))
            return
        user_id = message.from_user.id if message.from_user else None
        if not is_owner(user_id, owner_id):
            await message.answer(premium_text("🔒 <b>Owner Access Only</b>"))
            return
        try:
            snapshot = encrypt_backup(create_database_backup())
            await message.answer_document(
                BufferedInputFile(snapshot, filename="aniworld-security-backup.sqlite3.awb"),
                caption=premium_text("🗄️ <b>Encrypted Database Backup</b>\n\nAES-256-GCM encrypted and integrity-verified snapshot created. Store it privately. 🔐"),
            )
        except Exception:
            await message.answer(premium_text("❌ <b>Backup Failed</b>\n\nCheck the service logs and database storage."))
            raise

    return router
