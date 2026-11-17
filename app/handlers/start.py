"""Basic bot health and start command."""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="start")


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    await message.answer(
        "⚔️ <b>Ani World 剣 Management Bot</b>\n\n"
        "Bot online hai. Core connection test successful.\n"
        "Management features abhi development mein hain.",
        parse_mode="HTML",
    )
