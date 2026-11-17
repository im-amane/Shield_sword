"""Owner-only identity check command."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.security.owner import is_owner
from app.handlers.typography import premium_text


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

    return router
