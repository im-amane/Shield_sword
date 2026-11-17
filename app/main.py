"""Application entry point."""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile
from datetime import datetime, timezone

from app.config import ConfigurationError, load_settings
from app.handlers.owner import create_owner_router
from app.handlers.moderation import create_moderation_router
from app.handlers.antispam import create_antispam_router
from app.handlers.panel import create_panel_router
from app.handlers.raid_protection import create_raid_router
from app.handlers.start import router as start_router
from app.handlers.welcome import create_welcome_router
from app.handlers.verification import create_verification_router
from app.handlers.warnings import create_warning_router
from app.handlers.antilink import create_antilink_router
from app.handlers.badwords import create_badwords_router
from app.handlers.copyright import create_copyright_router
from app.handlers.utility import create_utility_router
from app.handlers.diagnostics import create_diagnostics_router
from app.handlers.security_status import create_security_status_router
from app.storage import create_database_backup, init_storage
from app.handlers.typography import premium_text

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
BACKUP_INTERVAL_SECONDS = 24 * 60 * 60


async def automatic_backup_loop(bot: Bot, owner_id: int) -> None:
    """Send a validated off-volume database snapshot to the owner every 24 hours."""
    logger = logging.getLogger(__name__)
    # Create the first off-volume copy shortly after startup, then repeat daily.
    await asyncio.sleep(60)
    while True:
        try:
            snapshot = create_database_backup()
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await bot.send_document(
                chat_id=owner_id,
                document=BufferedInputFile(
                    snapshot, filename=f"aniworld-security-backup-{stamp}.sqlite3"
                ),
                caption=premium_text(
                    "🛡️ <b>Automatic Database Backup</b>\\n\\n"
                    "A verified backup snapshot is attached. Keep it private and safe. 🔐"
                ),
            )
            logger.info("Automatic database backup delivered to owner (%s bytes).", len(snapshot))
            await asyncio.sleep(BACKUP_INTERVAL_SECONDS)
        except TelegramAPIError:
            logger.exception("Automatic database backup could not be delivered to owner; retrying in one hour.")
            await asyncio.sleep(60 * 60)
        except Exception:
            logger.exception("Automatic database backup failed; retrying in one hour.")
            await asyncio.sleep(60 * 60)


async def run() -> None:
    init_storage()
    settings = load_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, protect_content=True),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(start_router)
    dispatcher.include_router(create_utility_router())
    dispatcher.include_router(create_diagnostics_router())
    dispatcher.include_router(create_security_status_router())
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
    # Anti-spam is deliberately last: its broad group-message filter must not
    # swallow updates before the more specific link/content protection routers.
    dispatcher.include_router(create_antispam_router(settings.owner_id))

    backup_task = (
        asyncio.create_task(automatic_backup_loop(bot, settings.owner_id))
        if settings.owner_id is not None else None
    )
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
        if backup_task is not None:
            backup_task.cancel()
            try:
                await backup_task
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
