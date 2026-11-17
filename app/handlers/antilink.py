"""Group anti-link protection with admin controls and per-chat allowlists."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import urlsplit

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

from app.handlers.typography import premium_text
from app.handlers.warnings import WARN_LIMIT, add_warning, reset_warnings
from app.storage import (add_allowed_domain, get_allowed_domains, is_feature_enabled, remove_allowed_domain, set_feature_enabled)

_URL_RE = re.compile(
    r"(?i)(?:https?://|www\.)[^\s<>]+|"
    r"(?<![\w@])(?:t\.me|telegram\.me|telegram\.dog)/[^\s<>]+|"
    r"(?<![\w@])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/[^\s<>]*)?"
)
_TG_HOSTS = {"t.me", "www.t.me", "telegram.me", "www.telegram.me", "telegram.dog"}


def normalize_domain(value: str) -> str:
    """Normalize a domain or URL to a lowercase hostname."""
    raw = value.strip().lower().rstrip(".,;:!?)]}")
    if not raw:
        raise ValueError("Enter a domain such as example.com.")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlsplit(raw)
    host = (parsed.hostname or "").rstrip(".")
    if not host or "." not in host or any(ch.isspace() for ch in host):
        raise ValueError("Enter a valid domain such as example.com.")
    if host.startswith("www."):
        host = host[4:]
    return host


def extract_links(message: Message) -> list[str]:
    """Return URLs found in text/caption and Telegram URL entities."""
    value = message.text or message.caption or ""
    links = [match.group(0).rstrip(".,;:!?)]}") for match in _URL_RE.finditer(value)]
    entities = list(message.entities or []) + list(message.caption_entities or [])
    for entity in entities:
        if entity.type == "text_link" and entity.url:
            links.append(entity.url)
    return list(dict.fromkeys(links))


def is_allowed_link(url: str, allowed: set[str]) -> bool:
    """Telegram invite links are never allowlisted; other domains match exact/subdomains."""
    try:
        raw = url if "://" in url else "https://" + url
        host = (urlsplit(raw).hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    if host in _TG_HOSTS:
        return False
    return any(host == domain or host.endswith("." + domain) for domain in allowed)


def create_antilink_router() -> Router:
    router = Router(name="anti_link")

    async def require_admin(message: Message) -> bool:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer(premium_text("⚠️ <b>Group Only</b>\n\nUse this command inside a group."))
            return False
        if not message.from_user:
            return False
        try:
            actor = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
            bot_user = await message.bot.get_me()
            bot_member = await message.bot.get_chat_member(message.chat.id, bot_user.id)
        except TelegramAPIError:
            await message.answer(premium_text("❌ <b>Permission Check Failed</b>\n\nPlease try again."))
            return False
        if actor.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            await message.answer(premium_text("🔒 <b>Admin Only</b>\n\nOnly group admins can change anti-link settings."))
            return False
        if actor.status == ChatMemberStatus.ADMINISTRATOR and not getattr(actor, "can_delete_messages", False):
            await message.answer(premium_text("🔒 <b>Missing Admin Right</b>\n\nYou need Delete Messages permission."))
            return False
        if bot_member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR) or not getattr(bot_member, "can_delete_messages", False):
            await message.answer(premium_text("⚙️ <b>Bot Permission Needed</b>\n\nPromote Ani World with Delete Messages permission."))
            return False
        return True

    @router.message(Command("antilink"))
    async def antilink_command(message: Message) -> None:
        if not await require_admin(message):
            return
        args = (message.text or "").split(maxsplit=1)
        action = args[1].strip().lower() if len(args) > 1 else "status"
        chat_id = message.chat.id
        if action == "on":
            set_feature_enabled('antilink', chat_id, True)
            response = "✅ <b>Anti-Link Enabled</b>\n\nLinks from members will be removed. Admins are exempt."
        elif action == "off":
            set_feature_enabled('antilink', chat_id, False)
            response = "⏸️ <b>Anti-Link Disabled</b>\n\nMembers can share links again."
        elif action in {"status", "help"}:
            state = "ON" if is_feature_enabled("antilink", chat_id) else "OFF"
            domains = sorted(get_allowed_domains(chat_id))
            allow_text = ", ".join(escape(item) for item in domains) if domains else "None"
            response = (
                f"🛡️ <b>Anti-Link Status: {state}</b>\n\n"
                "Commands:\n"
                "• <code>/antilink on</code> - enable\n"
                "• <code>/antilink off</code> - disable\n"
                "• <code>/allowdomain example.com</code> - trust a domain\n"
                "• <code>/removedomain example.com</code> - remove trusted domain\n\n"
                f"🌐 <b>Trusted domains:</b> {allow_text}\n"
                "Telegram invite links are always blocked while protection is on."
            )
        else:
            response = "📝 <b>Usage</b>\n\n<code>/antilink on</code>, <code>/antilink off</code> or <code>/antilink</code>"
        await message.answer(premium_text(response))

    @router.message(Command("allowdomain"))
    async def allow_domain_command(message: Message) -> None:
        if not await require_admin(message):
            return
        args = (message.text or "").split(maxsplit=1)
        try:
            if len(args) < 2:
                raise ValueError("Usage: /allowdomain example.com")
            domain = normalize_domain(args[1])
            if domain in _TG_HOSTS or domain.endswith("t.me"):
                raise ValueError("Telegram invite domains cannot be trusted.")
            add_allowed_domain(message.chat.id, domain)
        except ValueError as exc:
            await message.answer(premium_text(f"⚠️ <b>Invalid Domain</b>\n\n{escape(str(exc))}"))
            return
        await message.answer(premium_text(f"✅ <b>Domain Trusted</b>\n\n<code>{escape(domain)}</code> and its subdomains are allowed."))

    @router.message(Command("removedomain"))
    async def remove_domain_command(message: Message) -> None:
        if not await require_admin(message):
            return
        args = (message.text or "").split(maxsplit=1)
        try:
            if len(args) < 2:
                raise ValueError("Usage: /removedomain example.com")
            domain = normalize_domain(args[1])
        except ValueError as exc:
            await message.answer(premium_text(f"⚠️ <b>Invalid Domain</b>\n\n{escape(str(exc))}"))
            return
        remove_allowed_domain(message.chat.id, domain)
        await message.answer(premium_text(f"✅ <b>Domain Removed</b>\n\n<code>{escape(domain)}</code> is no longer trusted."))

    @router.message(
        F.chat.type.in_({"group", "supergroup"})
        & ((F.text.regexp(_URL_RE)) | (F.caption.regexp(_URL_RE)) | (F.entities.func(lambda entities: any(entity.type in {"url", "text_link"} for entity in (entities or [])))) | (F.caption_entities.func(lambda entities: any(entity.type in {"url", "text_link"} for entity in (entities or [])))))
        & ((F.text == None) | ~F.text.startswith("/"))
    )
    async def inspect_message(message: Message) -> None:
        if not is_feature_enabled('antilink', message.chat.id) or not message.from_user:
            return
        user = message.from_user
        if user.is_bot:
            return
        try:
            member = await message.bot.get_chat_member(message.chat.id, user.id)
        except TelegramAPIError:
            return
        if member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            return

        links = extract_links(message)
        blocked = [url for url in links if not is_allowed_link(url, get_allowed_domains(message.chat.id))]
        if not blocked:
            return

        try:
            await message.delete()
        except TelegramAPIError:
            # If deletion failed, don't falsely claim the link was removed or issue a warning.
            return

        count = add_warning(message.chat.id, user.id)
        if count >= WARN_LIMIT:
            try:
                await message.bot.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now(timezone.utc) + timedelta(minutes=10),
                )
            except TelegramAPIError:
                await message.answer(premium_text(
                    f"⚠️ <b>Link Removed</b>\n\n"
                    f"👤 {escape(user.full_name)}\n"
                    f"Warning {count}/{WARN_LIMIT}. I could not apply the 10-minute mute; check Ban Users permission."
                ))
                return
            reset_warnings(message.chat.id, user.id)
            await message.answer(premium_text(
                f"🔇 <b>Link Removed · Member Muted</b>\n\n"
                f"👤 {escape(user.full_name)}\n"
                f"⚠️ Warning limit reached ({WARN_LIMIT}/{WARN_LIMIT}).\n"
                "⏳ Muted for 10 minutes."
            ))
            return

        await message.answer(premium_text(
            f"⚠️ <b>Link Removed</b>\n\n"
            f"👤 {escape(user.full_name)}\n"
            f"📊 Warning: {count}/{WARN_LIMIT}\n"
            "External links are not allowed in this group."
        ))

    return router
