"""Premium Unicode typography for user-facing Telegram messages."""
from __future__ import annotations

import re

_BOLD_SERIF = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"
    "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳",
)
_TOKEN = re.compile(r"(<[^>]+>|&[A-Za-z0-9#]+;|/[_A-Za-z][A-Za-z0-9_]*(?:@[A-Za-z0-9_]+)?|@[A-Za-z0-9_]+)")


def premium_text(value: str) -> str:
    """Style prose while preserving HTML markup, entities, and literal bot commands."""
    parts = _TOKEN.split(value)
    output: list[str] = []
    in_code = False
    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            output.append(part)
            tag = part.casefold()
            if tag.startswith("<code") or tag.startswith("<pre"):
                in_code = True
            elif tag.startswith("</code") or tag.startswith("</pre"):
                in_code = False
        elif in_code or part.startswith("/") or part.startswith("@") or (part.startswith("&") and part.endswith(";")):
            output.append(part)
        else:
            output.append(part.translate(_BOLD_SERIF))
    return "".join(output)
