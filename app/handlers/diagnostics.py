"""Group security diagnostics for administrators."""
from __future__ import annotations

from html import escape

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.typography import premium_text


def permission_lines(member) -> list[str]:
    """Describe the Telegram rights needed by Sentinel's active protections."""
    if member.status == ChatMemberStatus.CREATOR:
        return ["✅ Group owner: full administrator rights"]
    if member.status != ChatMemberStatus.ADMINISTRATOR:
        return ["❌ Bot is not an administrator"]
    checks = (
        ("can_delete_messages", "Delete messages"),
        ("can_restrict_members", "Restrict members"),
    )
    return [
        f'{"✅" if getattr(member, field, False) else "❌"} {label}'
        for field, label in checks
    ]


def format_member_status(status) -> str:
    """Support both aiogram enum values and raw strings returned by Telegram."""
    return escape(str(getattr(status, "value", status)))


def create_diagnostics_router() -> Router:
    router = Router(name="security_diagnostics")

    @router.message(Command("checkpermissions"))
    async def check_permissions(message: Message) -> None:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer(premium_text(
                "🛡️ <b>Group Security Check</b>\n"
                "Run /checkpermissions inside the group you want to inspect."
            ))
            return
        if not message.from_user:
            return
        try:
            actor = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
            if actor.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
                await message.answer(premium_text("🔒 <b>Admin only.</b> Group administrators can run this check."))
                return
            me = await message.bot.get_me()
            bot_member = await message.bot.get_chat_member(message.chat.id, me.id)
        except TelegramAPIError:
            await message.answer(premium_text(
                "⚠️ <b>Permission check incomplete.</b> Telegram could not return member details."
            ))
            return

        lines = permission_lines(bot_member)
        ready = bot_member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)
        if ready and bot_member.status == ChatMemberStatus.ADMINISTRATOR:
            ready = bool(bot_member.can_delete_messages and bot_member.can_restrict_members)

        heading = "🟢 All required permissions are ready." if ready else "🟠 Missing permissions detected."
        await message.answer(premium_text(
            "🛡️ <b>Sentinel · Security Check</b>\n"
            f"<b>{escape(message.chat.title or 'Telegram group')}</b> · <code>{format_member_status(bot_member.status)}</code>\n\n"
            + "\n".join(lines)
            + f"\n\n<b>{heading}</b>"
        ))

    return router
