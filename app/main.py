"""Application entry point."""
from __future__ import annotations

import asyncio
import logging
import time
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile
from datetime import datetime, timezone

from app.config import ConfigurationError, load_settings
from app.backup_crypto import encrypt_backup
from app.handlers.owner import create_owner_router
from app.handlers.moderation import create_moderation_router
from app.handlers.antispam import create_antispam_router
from app.handlers.panel import create_panel_router
from app.handlers.raid_protection import create_raid_router
from app.handlers.start import router as start_router
from app.handlers.welcome import create_welcome_router
from app.handlers.verification import (
    create_verification_router, verification_expiry_loop,
)
from app.handlers.warnings import create_warning_router
from app.handlers.antilink import create_antilink_router
from app.handlers.badwords import create_badwords_router
from app.handlers.copyright import create_copyright_router
from app.handlers.utility import create_utility_router
from app.handlers.diagnostics import create_diagnostics_router
from app.handlers.permission_monitor import create_permission_monitor_router
from app.handlers.security_status import create_security_status_router
from app.handlers.ai_guard import create_ai_guard_router
from app.ui import create_ui_router, install_ui_middleware
from app.storage import (
    create_database_backup, init_storage,
    get_last_automatic_backup_at, set_last_automatic_backup_at,
    get_last_daily_report_at, set_last_daily_report_at, get_owner_security_summary,
)
from app.handlers.typography import premium_text
from app.group_registry import GroupRegistryMiddleware
from app.rate_limit import RequestLimitMiddleware

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
BACKUP_INTERVAL_SECONDS = 7 * 24 * 60 * 60
DAILY_REPORT_INTERVAL_SECONDS = 24 * 60 * 60


async def automatic_backup_loop(bot: Bot, owner_id: int) -> None:
    """Send one verified backup per week, without repeating after process restarts."""
    logger = logging.getLogger(__name__)
    while True:
        last_success = get_last_automatic_backup_at()
        if last_success is None:
            # Preserve the initial first-run backup, but persist its success below.
            wait_seconds = 60
        else:
            wait_seconds = max(0, BACKUP_INTERVAL_SECONDS - (time.time() - last_success))
        if wait_seconds:
            await asyncio.sleep(wait_seconds)
        try:
            snapshot = encrypt_backup(create_database_backup())
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await bot.send_document(
                chat_id=owner_id,
                document=BufferedInputFile(
                    snapshot, filename=f"aniworld-security-backup-{stamp}.sqlite3.awb"
                ),
                protect_content=True,
                caption=premium_text(
                    "🛡️ <b>Automatic Weekly Database Backup</b>\\n\\n"
                    "An AES-256-GCM encrypted, integrity-verified backup is attached. The next automatic backup is scheduled in 7 days. Keep it private and safe. 🔐"
                ),
            )
            set_last_automatic_backup_at(time.time())
            logger.info("Weekly automatic database backup delivered to owner (%s bytes).", len(snapshot))
        except TelegramAPIError:
            logger.exception("Automatic database backup could not be delivered to owner; retrying in one hour.")
            await asyncio.sleep(60 * 60)
        except Exception:
            logger.exception("Automatic database backup failed; retrying in one hour.")
            await asyncio.sleep(60 * 60)


async def daily_security_report_loop(bot: Bot, owner_id: int) -> None:
    """Send a persisted daily security summary to the owner."""
    logger = logging.getLogger(__name__)
    while True:
        last_success = get_last_daily_report_at()
        if last_success is None:
            wait_seconds = 60
        else:
            wait_seconds = max(
                0, DAILY_REPORT_INTERVAL_SECONDS - (time.time() - last_success)
            )
        if wait_seconds:
            await asyncio.sleep(wait_seconds)
        try:
            stats = get_owner_security_summary()
            report = (
                "🛡️ <b>Daily Security Report</b>\\n\\n"
                f"👥 Groups monitored: <b>{stats['groups']}</b>\\n"
                f"🆕 New members (24h): <b>{stats['joins_24h']}</b>\\n"
                f"🚨 Security incidents (24h): <b>{stats['incidents_24h']}</b>\\n"
                f"⚔️ Raids detected (7d): <b>{stats['raids_7d']}</b>\\n"
                f"🔇 Anti-spam actions (24h): <b>{stats['spam_24h']}</b>\\n"
                f"🚧 Active raid modes: <b>{stats['active_raids']}</b>\\n\\n"
                "Next report: in 24 hours. 🔐"
            )
            await bot.send_message(chat_id=owner_id, text=premium_text(report))
            set_last_daily_report_at(time.time())
            logger.info("Daily security report delivered to owner.")
        except TelegramAPIError:
            logger.exception("Daily security report delivery failed; retrying in one hour.")
            await asyncio.sleep(60 * 60)
        except Exception:
            logger.exception("Daily security report failed; retrying in one hour.")
            await asyncio.sleep(60 * 60)


async def run() -> None:
    init_storage()
    settings = load_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, protect_content=False),
    )
    install_ui_middleware(bot)
    dispatcher = Dispatcher()
    # Observe every message update before router filters, including /commands.
    # This makes group discovery independent of new-member joins or anti-spam hits.
    dispatcher.message.outer_middleware(GroupRegistryMiddleware())
    request_limiter = RequestLimitMiddleware(settings.owner_id)
    dispatcher.message.outer_middleware(request_limiter)
    dispatcher.callback_query.outer_middleware(request_limiter)
    # Anti-spam runs first so media updates are checked before the media-policy
    # router consumes them. Non-spam updates raise SkipHandler and continue.
    dispatcher.include_router(create_antispam_router(settings.owner_id))
    dispatcher.include_router(create_ui_router())
    dispatcher.include_router(start_router)
    dispatcher.include_router(create_utility_router())
    dispatcher.include_router(create_diagnostics_router())
    dispatcher.include_router(create_security_status_router())
    dispatcher.include_router(create_permission_monitor_router(settings.owner_id))
    dispatcher.include_router(create_owner_router(settings.owner_id))
    dispatcher.include_router(create_panel_router(settings.owner_id))
    dispatcher.include_router(create_welcome_router(settings.welcome_chat_ids, settings.owner_id))
    dispatcher.include_router(create_verification_router())
    dispatcher.include_router(create_moderation_router(settings.owner_id))
    dispatcher.include_router(create_warning_router())
    dispatcher.include_router(create_badwords_router())
    dispatcher.include_router(create_copyright_router())
    dispatcher.include_router(create_antilink_router())
    dispatcher.include_router(create_raid_router(settings.owner_id))

    # Keep AI moderation opt-in and last in router order so deterministic filters
    # retain priority. Missing credentials never prevent normal bot startup.
    if settings.ai_guard_enabled and settings.nvidia_nim_api_key:
        dispatcher.include_router(create_ai_guard_router(
            settings.owner_id,
            settings.nvidia_nim_api_key,
            settings.nvidia_nim_model,
        ))
        logging.getLogger(__name__).info(
            "NVIDIA NIM AI Guard enabled with model %s.", settings.nvidia_nim_model
        )
    elif settings.ai_guard_enabled:
        logging.getLogger(__name__).warning(
            "AI_GUARD_ENABLED is true but NVIDIA_NIM_API_KEY is missing; AI Guard remains disabled."
        )

    backup_task = (
        asyncio.create_task(automatic_backup_loop(bot, settings.owner_id))
        if settings.owner_id is not None else None
    )
    daily_report_task = (
        asyncio.create_task(daily_security_report_loop(bot, settings.owner_id))
        if settings.owner_id is not None else None
    )
    verification_task = asyncio.create_task(verification_expiry_loop(bot))
    try:
        me = await bot.get_me()
        logging.getLogger(__name__).info(
            "Connected to Telegram as @%s (id=%s)", me.username, me.id
        )
        if settings.owner_id is None:
            logging.getLogger(__name__).warning(
                "OWNER_ID is not configured; owner-only commands are locked."
            )
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
            tasks_concurrency_limit=32,
        )
    finally:
        for task in (backup_task, daily_report_task, verification_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        await bot.session.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stdout)
    try:
        asyncio.run(run())
    except ConfigurationError as exc:
        logging.getLogger(__name__).critical("Configuration error: %s", exc)
        raise SystemExit(2) from exc
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Bot stopped by operator.")


if __name__ == "__main__":
    main()
