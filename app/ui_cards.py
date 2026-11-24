"""Image-card rendering for Sentinel Telegram responses."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from typing import Iterable
from PIL import Image, ImageDraw, ImageFont, ImageOps

_WIDTH = 1100
_FONT_PATHS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf")

def _font(size: int):
    for path in _FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()

def _wrap(draw, value: str, font, max_width: int) -> list[str]:
    words = str(value or "Not available").split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or ["Not available"]

def render_user_profile_card(*, display_name: str, username: str, user_id: int,
    first_name: str, last_name: str, bio: str, current_chat_id: int,
    group_title: str | None, group_id: int | None, avatar: bytes | None = None,
    name_history: Iterable[str] = ()) -> bytes:
    """Render a high-contrast, mobile-readable profile card."""
    rows = [
        ("USER ID", str(user_id)),
        ("CHAT ID", str(current_chat_id)),
        ("USERNAME", username or "Not set"),
        ("FIRST NAME", first_name or "Not available"),
        ("LAST NAME", last_name or "Not set"),
        ("BIO", bio or "Not available"),
    ]
    if group_id is not None:
        rows.append(("GROUP", group_title or "Telegram group"))
    history = list(name_history)
    rows.append(("PREVIOUS OBSERVED NAME", " / ".join(history[:3]) if history else
                 "No earlier name has been observed by Sentinel"))

    width = 1000
    label_font, value_font = _font(30), _font(38)
    title_font, small_font = _font(48), _font(22)
    measure = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    row_heights = [
        max(112, 58 + len(_wrap(measure, value, value_font, 850)) * 48)
        for _, value in rows
    ]
    height = 300 + sum(row_heights) + 80
    image = Image.new("RGB", (width, height), "#080b19")
    draw = ImageDraw.Draw(image)
    for y in range(height):
        blend = y / max(1, height - 1)
        draw.line((0, y, width, y), fill=(int(8 + 10 * blend), int(11 + 4 * blend), int(25 + 30 * blend)))
    draw.rounded_rectangle((22, 22, width-22, height-22), radius=34, outline="#7545c8", width=4)
    draw.rounded_rectangle((48, 48, width-48, 252), radius=28, fill="#17132e", outline="#5835a1", width=2)
    draw.text((82, 72), "SENTINEL  /  USER PROFILE", font=small_font, fill="#c9a7ff")
    draw.text((82, 116), (display_name or "Telegram user")[:24], font=title_font, fill="#ffffff")
    draw.ellipse((760, 72, 940, 252), fill="#29204a", outline="#b58aff", width=5)
    if avatar:
        try:
            photo = ImageOps.fit(Image.open(BytesIO(avatar)).convert("RGB"), (168, 168), centering=(0.5, 0.35))
            mask = Image.new("L", (168, 168), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 167, 167), fill=255)
            image.paste(photo, (766, 78), mask)
            draw.ellipse((760, 72, 940, 252), outline="#b58aff", width=5)
        except (OSError, ValueError):
            pass

    y = 276
    for (label, value), row_height in zip(rows, row_heights):
        draw.rounded_rectangle((48, y, width-48, y+row_height-10), radius=20,
                               fill="#17172d", outline="#30264f", width=2)
        draw.text((78, y+14), label, font=label_font, fill="#c9a7ff")
        for index, line in enumerate(_wrap(draw, value, value_font, 850)):
            draw.text((78, y+52+index*48), line, font=value_font, fill="#ffffff")
        y += row_height
    draw.text((58, height-58), "Telegram-visible profile details · Sentinel", font=small_font, fill="#a99bc4")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()

def render_category_card(category: str, title: str, subtitle: str = "") -> bytes:
    """Render a distinct branded header card for each command category."""
    palette={"help":("#142b46","#65d7e8"),"welcome":("#173b35","#72e0b0"),
      "warning":("#43251f","#ffb36b"),"security":("#202b4b","#9db6ff"),
      "owner":("#30264a","#c7a8ff"),"ai":("#123b42","#70e6dc"),
      "moderation":("#3d2636","#ff9ab8"),"verification":("#233b32","#9be4a7"),
      "system":("#263342","#a9c7e5")}
    background,accent=palette.get(category,palette["system"])
    image=Image.new("RGB",(1100,300),"#08111f")
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((24,24,1076,276),radius=34,fill=background,outline=accent,width=3)
    draw.rounded_rectangle((60,68,78,232),radius=8,fill=accent)
    draw.text((112,70),"SENTINEL  /  ANI WORLD",font=_font(20),fill=accent)
    draw.text((112,112),title[:36],font=_font(48),fill="#f4f7fb")
    if subtitle:
        draw.text((114,190),subtitle[:72],font=_font(24),fill="#b8c8d9")
    output=BytesIO()
    image.save(output,format="PNG",optimize=True)
    return output.getvalue()
