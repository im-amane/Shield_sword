"""Owner-only identity check command."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.security.owner import is_owner


def create_owner_router(owner_id: int | None) -> Router:
    """Create owner command handlers bound to the configured owner ID."""
    router = Router(name="owner")

    @router.message(Command("owner"))
    async def owner_command(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not is_owner(user_id, owner_id):
            await message.answer("⛔ Nope! Ye command sirf bot owner ke liye hai. 🔒")
            return

        await message.answer(
            "🔐 <b>Access granted!</b>\n"
            "Owner verified. Boss, sab set hai. 😎"
        )

    return router
