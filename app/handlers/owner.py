"""Owner-only identity, audit, database and backup commands."""
import asyncio
import time
from html import escape
from io import BytesIO

from aiogram import Router
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import BufferedInputFile, Message

from app.security.owner import is_owner
from app.backup_crypto import decrypt_backup, encrypt_backup
from app.handlers.typography import premium_text
from app.storage import (
    create_database_backup, get_audit_events, get_database_status,
    verify_database_backup,
)
from app.ai_chat import DEFAULT_NIM_CHAT_MODEL, NimChatClient
from app.ai_guard import DEFAULT_NIM_MODEL, NimSafetyClient


def create_owner_router(
    owner_id: int | None,
    chat_api_key: str = "",
    guardian_api_key: str = "",
    safety_model: str = DEFAULT_NIM_MODEL,
    chat_model: str = DEFAULT_NIM_CHAT_MODEL,
) -> Router:
    """Create owner command handlers bound to the configured owner ID."""
    router = Router(name="owner")

    def authorized_private_owner(message: Message) -> bool:
        return (
            message.chat.type == ChatType.PRIVATE
            and is_owner(message.from_user.id if message.from_user else None, owner_id)
        )

    @router.message(Command("aitest"))
    async def ai_test_command(message: Message) -> None:
        if not authorized_private_owner(message):
            await message.answer(premium_text("🔒 <b>Owner-only</b> · Use /aitest in my private chat."))
            return
        if not chat_api_key or not guardian_api_key:
            await message.answer(premium_text(
                "❌ <b>AI engine keys missing</b>\n\n"
                "Configure NVIDIA_NIM_CHAT_API_KEY and NVIDIA_NIM_GUARDIAN_API_KEY in Railway Variables."
            ))
            return

        status = await message.answer(premium_text(
            "🧪 <b>Guardian AI engine diagnostics</b>\n\nTesting independent chat and Guardian credentials…"
        ))
        chat_result = await asyncio.to_thread(
            NimChatClient(chat_api_key, chat_model).generate,
            "Reply with exactly: Guardian chat test passed.",
        )
        safety_started = time.monotonic()
        safety_result = await asyncio.to_thread(
            NimSafetyClient(guardian_api_key, safety_model, timeout=20.0).classify,
            "Hello everyone, hope you are having a good day!",
        )
        safety_latency = int((time.monotonic() - safety_started) * 1000)
        chat_ok = bool(chat_result.text and chat_result.error is None)
        safety_ok = bool(safety_result is not None and not safety_result["unsafe"])
        def line(label: str, ok: bool, latency: int, error: str | None = None) -> str:
            detail = f" · {latency} ms"
            if error:
                detail += f" · {escape(error)}"
            return f"{'✅' if ok else '❌'} <b>{label}:</b> {'PASS' if ok else 'FAIL'}{detail}"
        preview = escape((chat_result.text or "")[:220])
        report = (
            "🧪 <b>Guardian AI engine diagnostics</b>\n\n"
            + line("Chat engine", chat_ok, chat_result.latency_ms, chat_result.error) + "\n"
            + f"<code>{escape(chat_model)}</code>\n\n"
            + line("Guardian engine", safety_ok, safety_latency, None if safety_ok else "classification_failed") + "\n"
            + f"<code>{escape(safety_model)}</code>\n\n"
            + (f"<b>Chat sample:</b> {preview}\n\n" if preview else "")
            + ("Both independent engines responded correctly." if chat_ok and safety_ok else
               "At least one engine needs attention. Feature flags were not changed.")
        )
        await status.edit_text(premium_text(report[:3900]))

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

    @router.message(Command("backupverify"))
    async def backup_verify_command(message: Message) -> None:
        if message.chat.type != ChatType.PRIVATE:
            await message.answer(premium_text("🔒 Use /backupverify in my private chat."))
            return
        user_id = message.from_user.id if message.from_user else None
        if not is_owner(user_id, owner_id):
            await message.answer(premium_text("🔒 <b>Owner Access Only</b>"))
            return

        document = message.reply_to_message.document if message.reply_to_message else None
        if document is None:
            await message.answer(premium_text(
                "🔐 <b>Backup Recovery Check</b>\n\n"
                "Forward or upload your encrypted <code>.awb</code> backup here, then reply to that file with /backupverify. "
                "The file will be decrypted and restored only into an isolated temporary database. The live database will not be changed."
            ))
            return
        if document.file_size is not None and document.file_size > 20 * 1024 * 1024:
            await message.answer(premium_text("❌ Backup file exceeds Telegram's 20 MB download limit."))
            return
        filename = (document.file_name or "").lower()
        if not filename.endswith(".awb"):
            await message.answer(premium_text("❌ Expected an encrypted .awb backup file."))
            return

        try:
            telegram_file = await message.bot.get_file(document.file_id)
            if not telegram_file.file_path:
                raise ValueError("Telegram did not provide a download path")
            buffer = BytesIO()
            await message.bot.download_file(telegram_file.file_path, destination=buffer)
            plaintext = decrypt_backup(buffer.getvalue())
            result = verify_database_backup(plaintext)
            await message.answer(premium_text(
                "✅ <b>Backup Recovery Verification: PASS</b>\n\n"
                "🔐 AES-256-GCM authentication: passed\n"
                f"🗄️ SQLite integrity: <code>{escape(result['integrity'])}</code>\n"
                f"📚 Tables restored: <code>{result['table_count']}</code>\n"
                "🧪 Isolated restore: successful\n"
                "🛡️ Live database: unchanged"
            ))
        except Exception:
            await message.answer(premium_text(
                "❌ <b>Backup Recovery Verification: FAILED</b>\n\n"
                "The file could not be authenticated or restored. The live database was not modified. "
                "Check that the correct backup key is configured and the file is intact."
            ))
            raise

    return router
