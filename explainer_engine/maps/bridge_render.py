"""The bridge: large lettering over the frame that repeats the narration's words. Drawn with the maps' ``Canvas`` only
(rect, text, text_width, w, h), so a frame stays a pure function of its spec and its number (CMP-09)."""

from __future__ import annotations

_STYLES = ("card", "outline", "lower_third")


def _text_size(c, style: dict, frame_h: int | None) -> float:
    """The bridge size: a share of the frame height, so the same text looks the same at any resolution."""
    return style["cap_height_pct"] / 100.0 * (frame_h or c.h)


def draw_bridge(c, text: str, style: dict, fill=(255, 255, 255), ink=(0, 0, 0), frame_h: int | None = None) -> None:
    """Draw ``text`` as a bridge: a dark card, an outlined word, or a lower-third bar. The words are centred horizontally."""
    if not text:
        return
    name = style.get("name")
    if name not in _STYLES:
        raise ValueError(f"unknown bridge style: {name!r}")
    size = _text_size(c, style, frame_h)
    x = (c.w - c.text_width(text, size)) / 2.0
    if name == "card":
        y = 0.80 * c.h
        pad = 0.4 * size
        c.rect(x - pad, y - pad, x + c.text_width(text, size) + pad, y + size + pad, fill=ink, radius=pad)
        c.text((x, y), text, size, fill=fill)
    elif name == "outline":
        y = 0.80 * c.h
        c.text((x, y), text, size, fill=fill, stroke=size * 0.08, stroke_fill=ink)
    else:  # lower_third
        y = 0.88 * c.h
        c.rect(0, y - 0.3 * size, c.w, y + 1.3 * size, fill=ink)  # 1.6 * size tall, centred on the words
        c.text((x, y), text, size, fill=fill)


def bridge_text_width(c, text: str, style: dict, frame_h: int | None = None) -> float:
    """The width ``text`` takes at the bridge's size (for placing things clear of it)."""
    return c.text_width(text, _text_size(c, style, frame_h))
