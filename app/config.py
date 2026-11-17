"""Environment-backed application configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    owner_id: int | None
    welcome_chat_ids: tuple[int, ...]


def _parse_chat_ids(raw_value: str) -> tuple[int, ...]:
    """Parse a comma-separated allowlist of Telegram group IDs."""
    if not raw_value.strip():
        return ()

    parsed: list[int] = []
    for item in raw_value.split(","):
        value = item.strip()
        if not value:
            raise ConfigurationError(
                "WELCOME_CHAT_IDS contains an empty entry; use comma-separated numeric chat IDs."
            )
        try:
            chat_id = int(value)
        except ValueError as exc:
            raise ConfigurationError(
                "WELCOME_CHAT_IDS must contain only numeric Telegram chat IDs."
            ) from exc
        if chat_id >= 0:
            raise ConfigurationError(
                "WELCOME_CHAT_IDS must contain negative group or supergroup IDs."
            )
        if chat_id not in parsed:
            parsed.append(chat_id)
    return tuple(parsed)


def load_settings() -> Settings:
    """Load and validate settings without exposing secret values in logs."""
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ConfigurationError("BOT_TOKEN is missing. Set it in the hosting environment.")

    raw_owner_id = os.getenv("OWNER_ID", "").strip()
    owner_id: int | None = None
    if raw_owner_id:
        try:
            owner_id = int(raw_owner_id)
        except ValueError as exc:
            raise ConfigurationError("OWNER_ID must be a numeric Telegram user ID.") from exc
        if owner_id <= 0:
            raise ConfigurationError("OWNER_ID must be a positive Telegram user ID.")

    welcome_chat_ids = _parse_chat_ids(os.getenv("WELCOME_CHAT_IDS", ""))
    return Settings(
        bot_token=token,
        owner_id=owner_id,
        welcome_chat_ids=welcome_chat_ids,
    )
