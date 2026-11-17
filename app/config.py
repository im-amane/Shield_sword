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

    return Settings(bot_token=token, owner_id=owner_id)
