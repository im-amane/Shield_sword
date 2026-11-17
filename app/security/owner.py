"""Owner authorization helpers.

Authorization fails closed when OWNER_ID is not configured.
"""
from __future__ import annotations


def is_owner(user_id: int | None, owner_id: int | None) -> bool:
    """Return True only when both IDs are valid and match exactly."""
    if user_id is None or owner_id is None:
        return False
    if user_id <= 0 or owner_id <= 0:
        return False
    return user_id == owner_id
