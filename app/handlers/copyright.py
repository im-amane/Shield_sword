"""Media policy: never blanket-delete ordinary group or channel media."""
from aiogram import Router


def create_copyright_router() -> Router:
    """Retain the router registration point without destructive media rules.

    AI Guard separately checks text and captions on groups and channels.
    Visual copyright ownership/infringement is not inferred from media type.
    """
    return Router(name="media_policy")
