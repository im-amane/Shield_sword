"""Owner-only identity check command."""
from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from app.security.owner import is_owner
from app.handlers.typography import premium_text
from app.storage import create_database_backup, get_audit_events


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

    @router.message(Command("backup"))
    async def backup_command(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not is_owner(user_id, owner_id):
            await message.answer(premium_text("🔒 <b>Owner Access Only</b>"))
            return
        try:
            snapshot = create_database_backup()
            await message.answer_document(
                BufferedInputFile(snapshot, filename="aniworld-security-backup.sqlite3"),
                caption=premium_text("🗄️ <b>Database Backup</b>\n\nConsistent SQLite snapshot created. Store it somewhere private. 🔐"),
            )
        except Exception:
            await message.answer(premium_text("❌ <b>Backup Failed</b>\n\nCheck the service logs and database storage."))
            raise

    return router
