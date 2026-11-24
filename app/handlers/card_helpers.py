"""Shared delivery helper for category-specific Sentinel image cards."""
from __future__ import annotations
import inspect
from aiogram.types import BufferedInputFile, Message
from app.ui_cards import render_category_card


async def send_category_card(message: Message, category: str, title: str,
                             subtitle: str = "") -> None:
    image = render_category_card(category, title, subtitle)
    result = message.answer_photo(
        BufferedInputFile(image, filename=f"sentinel-{category}-card.png"),
        caption=f"🛡️ <b>Sentinel · {title}</b>",
    )
    if inspect.isawaitable(result):
        await result
