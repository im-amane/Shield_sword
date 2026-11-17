"""Premium Unicode typography for user-facing Telegram messages."""
from __future__ import annotations

import re

_BOLD_SERIF = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"
    "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳",
)
_TAG = re.compile(r"(<[^>]+>|&[A-Za-z0-9#]+;)")


def premium_text(value: str) -> str:
    """Apply bold-serif Unicode styling while leaving Telegram HTML tags intact."""
    return "".join(
        part if part.startswith("<") and part.endswith(">") else part.translate(_BOLD_SERIF)
        for part in _TAG.split(value)
    )
