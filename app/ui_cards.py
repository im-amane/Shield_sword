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
    """Render Telegram-visible profile fields and observed name history."""
    rows = [("USERNAME", username or "Not set"), ("TELEGRAM ID", str(user_id)),
        ("PRIVATE CHAT ID", str(user_id)),
        ("FIRST NAME", first_name or "Not available"), ("LAST NAME", last_name or "Not set"),
        ("BIO", bio or "Not available"), ("CURRENT CHAT ID", str(current_chat_id))]
    if group_id is not None:
        rows.extend((("GROUP", group_title or "Telegram group"), ("GROUP ID", str(group_id))))
    history = list(name_history)
    rows.append(("PREVIOUS OBSERVED NAME", " / ".join(history[:3]) if history else
                 "No earlier name has been observed by Sentinel"))
    label_font, value_font = _font(20), _font(25)
    title_font, small_font = _font(42), _font(18)
    measure = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    heights = [max(58, len(_wrap(measure, value, value_font, 700)) * 34 + 22)
               for _, value in rows]
    height = 240 + sum(heights) + 65
    image = Image.new("RGB", (_WIDTH, height), "#08111f")
    draw = ImageDraw.Draw(image)
    for y in range(height):
        blend = y / max(1, height - 1)
        draw.line((0, y, _WIDTH, y), fill=(int(8+5*blend), int(17+9*blend), int(31+18*blend)))
    draw.rounded_rectangle((24,24,_WIDTH-24,height-24), radius=34, outline="#2d4967", width=3)
    draw.rounded_rectangle((52,52,_WIDTH-52,190), radius=26, fill="#10243a")
    draw.text((82,76), "SENTINEL  /  USER PROFILE", font=small_font, fill="#65d7e8")
    draw.text((82,111), (display_name or "Telegram user")[:34], font=title_font, fill="#f4f7fb")
    draw.ellipse((850,62,1010,222), fill="#203b56", outline="#65d7e8", width=5)
    if avatar:
        try:
            photo = ImageOps.fit(Image.open(BytesIO(avatar)).convert("RGB"), (148,148), centering=(0.5,0.35))
            mask = Image.new("L", (148,148), 0)
            ImageDraw.Draw(mask).ellipse((0,0,147,147), fill=255)
            image.paste(photo, (856,68), mask)
            draw.ellipse((850,62,1010,222), outline="#65d7e8", width=5)
        except (OSError, ValueError):
            pass
    y = 220
    for (label,value), row_height in zip(rows,heights):
        draw.rounded_rectangle((52,y,_WIDTH-52,y+row_height-8), radius=16, fill="#102033")
        draw.text((78,y+12), label, font=label_font, fill="#65d7e8")
        for index,line in enumerate(_wrap(draw,value,value_font,700)):
            draw.text((360,y+8+index*34),line,font=value_font,fill="#f4f7fb")
        y += row_height
    draw.text((60,height-62),"Only Telegram-visible public profile details are shown.",
              font=small_font,fill="#91a8bf")
    output=BytesIO()
    image.save(output,format="PNG",optimize=True)
    return output.getvalue()
