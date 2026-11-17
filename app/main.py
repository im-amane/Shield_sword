"""Application entry point."""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import ConfigurationError, load_settings
from app.handlers.start import router as start_router

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


async def run() -> None:
    settings = load_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(start_router)

    try:
        me = await bot.get_me()
        logging.getLogger(__name__).info(
            "Connected to Telegram as @%s (id=%s)", me.username, me.id
        )
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
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
