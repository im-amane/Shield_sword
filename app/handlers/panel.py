"""Owner-only operational dashboard."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.security.owner import is_owner
from app.handlers.typography import premium_text


def dashboard_text(bot_username: str | None, bot_id: int, owner_id: int) -> str:
    """Build a concise dashboard view from verified runtime values."""
    username = f"@{bot_username}" if bot_username else "Not available"
    return premium_text((
        "⚙️ <b>Control Center</b>\n\n"
        "Welcome back, Owner! 👑\n\n"
        "Your command center is ready. Manage your bot and monitor its protection systems from here.\n\n"
        "🟢 <b>System status:</b> Online\n"
        f"🤖 <b>Bot:</b> {username}\n"
        f"🆔 <b>Bot ID:</b> <code>{bot_id}</code>\n"
        f"🔐 <b>Owner ID:</b> <code>{owner_id}</code>\n\n"
        "<i>Your community security, one control room. 🚀</i>"
    ))


def dashboard_keyboard() -> InlineKeyboardMarkup:
    """Create dashboard controls."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Refresh", callback_data="owner_panel:refresh"),
                InlineKeyboardButton(text="✖️ Close", callback_data="owner_panel:close"),
            ]
        ]
    )


def create_panel_router(owner_id: int | None) -> Router:
    """Create owner-protected dashboard command and callbacks."""
    router = Router(name="owner_panel")

    async def authorized(user_id: int | None) -> bool:
        return is_owner(user_id, owner_id)

    async def render_panel(message: Message) -> None:
        me = await message.bot.get_me()
        await message.answer(
            dashboard_text(me.username, me.id, owner_id or 0),
            reply_markup=dashboard_keyboard(),
        )

    @router.message(Command("panel"))
    async def panel_command(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not await authorized(user_id):
            await message.answer("🔒 <b>Private Area</b>\n\nThe owner dashboard is only available to the bot owner. 👑")
            return
        await render_panel(message)

    @router.callback_query(F.data.startswith("owner_panel:"))
    async def panel_callback(callback: CallbackQuery) -> None:
        user_id = callback.from_user.id if callback.from_user else None
        if not await authorized(user_id):
            await callback.answer("Access denied.", show_alert=True)
            return

        if callback.data == "owner_panel:close":
            if callback.message:
                await callback.message.delete()
            await callback.answer("Panel closed. Catch you later! 👋")
            return

        if callback.data == "owner_panel:refresh":
            if callback.message:
                me = await callback.bot.get_me()
                await callback.message.edit_text(
                    dashboard_text(me.username, me.id, owner_id or 0),
                    reply_markup=dashboard_keyboard(),
                )
            await callback.answer("Fresh status loaded. ✨")
            return

        await callback.answer("Unknown dashboard action.", show_alert=True)

    return router
