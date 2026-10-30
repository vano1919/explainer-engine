"""Character-select screens drawn by our own code (Syndicate Wars): portrait frames, star bars, an OUT stamp and the final
comparison. Layout, icons and colours are ours (neon pink, sunset orange, cyan); nothing is copied from any game's UI
(ES rule ER-05, RK-03). Fonts: assets/fonts (Bangers, Comic Neue, both OFL). Free: no model, no network.

    python examples/syndicate_wars_ep1/select_screen.py <pictures dir>     # writes sc_*.png next to the portraits p_*.png
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from explainer_engine.finish import bubbles as BUB

SIZE = (1920, 1080)
PINK, ORANGE, CYAN = (255, 64, 160), (255, 150, 70), (40, 220, 235)
NAVY, DARK, WHITE, DIM = (14, 10, 36), (30, 20, 60), (250, 245, 255), (95, 85, 130)

# the channel's own rating (opinion, claims C-44..C-47); "after" is the rating after the test (S30)
BOSSES = {
    "capone": {"name": "AL CAPONE", "sub": "Chicago, 1930s", "accent": ORANGE, "stats": [
        ("Brutality", 5), ("Adaptability", 1), ("Tech-Savviness", 1), ("Intimidation", 4), ("Chaos Management", 2)],
        "after": {"Intimidation": 2}},
    "vito": {"name": "VITO CORLEONE", "sub": "film-era Don", "accent": PINK, "stats": [
        ("Brutality", 2), ("Adaptability", 2), ("Tech-Savviness", 1), ("Influence / Networking", 5), ("Strategy", 4)],
        "after": {"Influence / Networking": 3}},
    "mizuno": {"name": "HARUTO MIZUNO", "sub": "invented boss", "accent": CYAN, "stats": [
        ("Brutality", 4), ("Adaptability", 4), ("Tech-Savviness", 4), ("Discipline", 5), ("Chaos Management", 2)],
        "after": {"Discipline": 4}},
    "shelby": {"name": "TOMMY SHELBY", "sub": "Birmingham, 1930s", "accent": (150, 120, 255), "stats": [
        ("Brutality", 3), ("Adaptability", 5), ("Tech-Savviness", 5), ("Intelligence / Strategy", 5), ("Influence", 4)],
        "after": {"Intelligence / Strategy": 4}},
}
ORDER = ["capone", "vito", "mizuno", "shelby"]


def font(size: int, shout: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BUB.SHOUT_FONT if shout else BUB.FONT), size)


def star(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill, outline=None, width=3) -> None:
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill, outline=outline, width=width)


def stars_row(d, x: int, y: int, n: int, accent, r: int = 24, old: int | None = None) -> None:
    for k in range(5):
        cx = x + k * (2 * r + 8) + r
        if k < n:
            star(d, cx, y, r, accent, outline=WHITE, width=2)
        elif old is not None and k < old:  # stars lost in the test: a hollow ghost
            star(d, cx, y, r, None, outline=CYAN, width=3)
        else:
            star(d, cx, y, r, DARK, outline=DIM, width=2)


def background() -> Image.Image:
    im = Image.new("RGB", SIZE, NAVY)
    d = ImageDraw.Draw(im)
    for y in range(SIZE[1]):  # a dark vertical gradient with a warm horizon glow at the bottom
        t = y / SIZE[1]
        d.line([(0, y), (SIZE[0], y)], fill=(int(14 + 70 * t ** 3), int(10 + 20 * t ** 2), int(36 + 40 * t)))
    for x in range(-SIZE[1], SIZE[0], 90):  # faint diagonal lines: collage energy, our own pattern
        d.line([(x, SIZE[1]), (x + SIZE[1], 0)], fill=(24, 18, 56), width=2)
    return im


def portrait(path: Path | None, box: tuple[int, int], accent, grey: bool = False) -> Image.Image:
    """The painted portrait cropped to ``box`` inside a thick accent frame; a flat placeholder when the file is missing."""
    w, h = box
    if path and Path(path).exists():
        src = Image.open(path).convert("RGB")
        im = ImageOps.fit(src, box, Image.LANCZOS, centering=(0.5, 0.35))
    else:
        im = Image.new("RGB", box, DARK)
    if grey:
        im = ImageOps.grayscale(im).convert("RGB")
        im = Image.blend(im, Image.new("RGB", box, (40, 0, 20)), 0.35)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], outline=accent, width=10)
    return im


def stamp(im: Image.Image, text: str = "OUT", angle: float = 14, center: tuple[int, int] | None = None) -> None:
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(int(im.size[1] * 0.2), True)
    w = int(d.textlength(text, font=f))
    cx, cy = center or (im.size[0] // 2, im.size[1] // 2)
    d.rounded_rectangle([cx - w // 2 - 50, cy - 130, cx + w // 2 + 50, cy + 130], 22, outline=(255, 40, 70, 235), width=14)
    d.text((cx, cy), text, font=f, fill=(255, 40, 70, 235), anchor="mm")
    layer = layer.rotate(angle, resample=Image.BICUBIC, center=(cx, cy))
    im.paste(layer, (0, 0), layer)


def card(boss: str, pics: Path, out: bool = False) -> Image.Image:
    b = BOSSES[boss]
    im = background()
    d = ImageDraw.Draw(im)
    acc = b["accent"]
    im.paste(portrait(pics / f"p_{boss}.png", (640, 840), acc, grey=out), (110, 120))
    d.text((820, 130), b["name"], font=font(120, True), fill=WHITE)
    d.text((824, 262), b["sub"], font=font(46), fill=acc)
    d.rounded_rectangle([1500, 150, 1830, 215], 18, fill=PINK)
    d.text((1665, 183), "OUR RATING", font=font(40, True), fill=WHITE, anchor="mm")
    for k, (label, n) in enumerate(b["stats"]):
        y = 400 + k * 118
        d.text((830, y), label, font=font(54), fill=WHITE, anchor="lm")
        stars_row(d, 1420, y, n, acc, 22)
    d.text((830, 1000), "Opinion, not fact: the reasons are in the video.", font=font(34), fill=DIM, anchor="lm")
    if out:
        stamp(im, center=(430, 540))
    return im


def grid(pics: Path, highlight: int | None = None) -> Image.Image:
    im = background()
    d = ImageDraw.Draw(im)
    d.text((960, 90), "CHOOSE YOUR BOSS", font=font(110, True), fill=WHITE, anchor="mm")
    w, gap = 400, 40
    x0 = (SIZE[0] - 4 * w - 3 * gap) // 2
    for k, boss in enumerate(ORDER):
        b = BOSSES[boss]
        x = x0 + k * (w + gap)
        im.paste(portrait(pics / f"p_{boss}.png", (w, 640), b["accent"]), (x, 190))
        d.rounded_rectangle([x, 850, x + w, 960], 14, fill=DARK, outline=b["accent"], width=5)
        d.text((x + w // 2, 905), b["name"], font=font(46, True), fill=WHITE, anchor="mm")
        if highlight == k:
            d.rectangle([x - 14, 176, x + w + 14, 844], outline=CYAN, width=8)
    d.text((960, 1020), "Five stats each. Our rating, an opinion.", font=font(38), fill=ORANGE, anchor="mm")
    return im


def final(pics: Path) -> Image.Image:
    """Four columns: the stars after the test; a hollow cyan star is a star lost in the test."""
    im = background()
    d = ImageDraw.Draw(im)
    d.text((960, 70), "AFTER THE TEST", font=font(100, True), fill=WHITE, anchor="mm")
    w, gap = 420, 30
    x0 = (SIZE[0] - 4 * w - 3 * gap) // 2
    for k, boss in enumerate(ORDER):
        b = BOSSES[boss]
        x = x0 + k * (w + gap)
        im.paste(portrait(pics / f"p_{boss}.png", (w, 260), b["accent"]), (x, 150))
        d.text((x + w // 2, 440), b["name"], font=font(42, True), fill=WHITE, anchor="mm")
        for j, (label, n) in enumerate(b["stats"]):
            y = 520 + j * 118
            d.text((x + 6, y - 40), label, font=font(30), fill=WHITE, anchor="lm")
            new = b["after"].get(label, n)
            stars_row(d, x + 6, y, new, b["accent"], 22, old=n if new != n else None)
    d.text((960, 1040), "Hollow cyan star: lost in the test. Our opinion.", font=font(34), fill=CYAN, anchor="mm")
    return im


def thumbnail(pics: Path) -> Image.Image:
    """1280x720 thumbnail from our own painted portraits: four faces, one question, no logo, no key art, no violence."""
    W, H = 1280, 720
    im = background().resize((W, H))
    d = ImageDraw.Draw(im)
    w, gap = 290, 16
    x0 = (W - 4 * w - 3 * gap) // 2
    for k, boss in enumerate(ORDER):
        b = BOSSES[boss]
        im.paste(portrait(pics / f"p_{boss}.png", (w, 440), b["accent"]), (x0 + k * (w + gap), 250))
        if boss == "capone":  # the first to fall: a hollow red cross, no blood, no weapon
            d.line([(x0 + 20, 270), (x0 + w - 20, 670)], fill=(255, 40, 70), width=14)
            d.line([(x0 + w - 20, 270), (x0 + 20, 670)], fill=(255, 40, 70), width=14)
    d.text((W // 2, 105), "WHO FALLS FIRST?", font=font(150, True), fill=WHITE, anchor="mm", stroke_width=8, stroke_fill=NAVY)
    d.text((W // 2, 205), "4 bosses  |  1 neon city  |  every phone is a witness", font=font(40), fill=CYAN, anchor="mm")
    return im


def make_all(pics: Path) -> list[Path]:
    pics = Path(pics)
    out = []
    jobs = {"sc_all": grid(pics, 0), "sc_final": final(pics)}
    for boss in ORDER:
        jobs[f"sc_{boss}"] = card(boss, pics)
    for boss in ("capone", "vito", "mizuno"):
        jobs[f"sc_{boss}_out"] = card(boss, pics, out=True)
    thumbnail(pics).save(pics / "thumbnail.png")
    out.append(pics / "thumbnail.png")
    for name, im in jobs.items():
        p = pics / f"{name}.png"
        im.save(p)
        out.append(p)
    return out


if __name__ == "__main__":
    for p in make_all(Path(sys.argv[1])):
        print(p)
