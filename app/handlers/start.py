"""Basic bot health and start command."""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="start")


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    await message.answer(
        "⚔️ <b>Ani World 剣 Management Bot</b>\n\n"
        "Yo! 👋 Main online hoon, group ki security ka dhyaan rakh raha hoon. 🛡️\n"
        "Admins, owner controls ke liye /panel use karo. Baaki sab, chill and enjoy! ✨",
        parse_mode="HTML",
    )
