"""Story cards: the dark title card that opens an episode and the recap boards between chapters (the creator 2026-10-21:
"the video starts on a dark background with text and a question ... after every chapter a small recap of what is happening
and what to expect, on a dark or coloured background with signs and text"; then "not pure black: a dark background, text,
Python diagrams or caricature heads listing the heroes").

A card is an ordinary picture (``engine: existing``): this module draws it once, free and offline, and the shot plays it with
its camera, beats, bubbles and sound like any other picture. Heads are cut from each hero's approved reference picture
(``p_<hero>``, D-55: never redrawn) round the YuNet face, inside an ink ring; signs are the vendored line icons
(``design/icons.py``). Colours come only from ``design/palette.json``.

    python -m explainer_engine.design.cards <script.json> <pictures dir> [--out dir]   # every card the script names
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from explainer_engine.design import icons as ICONS

ROOT = Path(__file__).resolve().parents[2]
SIZE = (2752, 1536)  # the size of the episode's painted pictures, so the camera treats a card like them
FONT_TITLE = ROOT / "assets" / "fonts" / "Bangers-Regular.ttf"
FONT_TEXT = ROOT / "assets" / "fonts" / "ComicNeue-Bold.ttf"
YUNET = ROOT / "tools" / "yunet" / "face_detection_yunet_2023mar.onnx"
TONES = {"night": ("night", "ink"), "coral": ("answer_coral", "ink"), "teal": ("mechanism_teal", "ink"),
         "blue": ("support_blue", "ink"), "amber": ("uncertain_amber", "ink")}  # tone -> (glow colour, base)


def _hex(token: str) -> tuple[int, int, int]:
    return ICONS._rgb(token)


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def background(tone: str = "night") -> Image.Image:
    """A dark, not black, board: the base ink colour with a soft glow of the tone's colour from the top and paper grain."""
    glow, base = TONES.get(tone, TONES["night"])
    W, H = SIZE
    im = Image.new("RGB", SIZE, _hex(base))
    g = Image.new("L", (W // 8, H // 8), 0)
    gd = ImageDraw.Draw(g)
    gd.ellipse([-W // 32, -H // 6, W // 8 + W // 32, H // 8 * 0.9], fill=110 if tone == "night" else 70)
    g = g.filter(ImageFilter.GaussianBlur(H // 40)).resize(SIZE, Image.BICUBIC)
    im = Image.composite(Image.new("RGB", SIZE, _hex(glow)), im, g)
    grain = Image.effect_noise((W // 2, H // 2), 18).resize(SIZE, Image.BICUBIC)
    return Image.blend(im, Image.merge("RGB", (grain,) * 3), 0.04)


def face_box(picture: Path, prefer_x: float | None = None) -> tuple[float, float, float, float]:
    """(x, y, w, h) of the hero's face in shares of the picture: the YuNet face nearest ``prefer_x`` (else the surest)."""
    from explainer_engine.qa import face_points as FP
    faces = FP.detect(picture, YUNET)
    if not faces:
        raise ValueError(f"no face found in {picture}")
    f = (min(faces, key=lambda q: abs(q["x"] - prefer_x)) if prefer_x is not None else max(faces, key=lambda q: q["score"]))
    return f["x"], f["y"], f["w"], f["h"]


def head(picture: Path, d: int, prefer_x: float | None = None, ring: str = "paper") -> Image.Image:
    """A round head medallion ``d`` px wide: the face and a little hair and collar, in an ink ring on a paper rim."""
    src = Image.open(picture).convert("RGB")
    x, y, w, h = face_box(picture, prefer_x)
    W, H = src.size
    side = max(w * W, h * H) * 1.55
    cx, cy = x * W, y * H + 0.06 * side
    crop = src.crop((int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2))).resize((d, d), Image.LANCZOS)
    k = 3
    mask = Image.new("L", (d * k, d * k), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d * k - 1, d * k - 1], fill=255)
    mask = mask.resize((d, d), Image.LANCZOS)
    out = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    out.paste(crop, (0, 0), mask)
    big = Image.new("RGBA", (d * k, d * k), (0, 0, 0, 0))
    bd = ImageDraw.Draw(big)
    rim = max(3, d // 28) * k
    bd.ellipse([rim // 2, rim // 2, d * k - rim // 2, d * k - rim // 2], outline=_hex(ring) + (255,), width=rim)
    bd.ellipse([0, 0, d * k - 1, d * k - 1], outline=_hex("ink") + (255,), width=max(2, d // 70) * k)
    out.alpha_composite(big.resize((d, d), Image.LANCZOS))
    return out


def _shadow(layer: Image.Image, pos, radius: int = 18, alpha: int = 150) -> Image.Image:
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(layer.getchannel("A").point(lambda v: v * alpha // 255))
    return sh.filter(ImageFilter.GaussianBlur(radius))


def _paste(im: Image.Image, layer: Image.Image, xy) -> None:
    x, y = int(xy[0]), int(xy[1])
    im.alpha_composite(_shadow(layer, xy), (x + 10, y + 16))
    im.alpha_composite(layer, (x, y))


def _text(d: ImageDraw.ImageDraw, xy, text: str, font, fill, anchor="mm", stroke: int = 0) -> None:
    d.text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=_hex("ink"))


def _wrap(text: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if font.getlength(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def title_card(spec: dict, pics: list[Path]) -> Image.Image:
    """The opening card: a big question over a row of the heroes' heads, each with its name under it."""
    W, H = SIZE
    im = background(spec.get("tone", "night")).convert("RGBA")
    d = ImageDraw.Draw(im)
    f = _font(FONT_TITLE, int(H * 0.105))
    lines = _wrap(spec["title"].upper(), f, int(W * 0.84))
    y = H * (0.13 if len(lines) < 3 else 0.1)
    for ln in lines:
        _text(d, (W / 2, y), ln, f, _hex("paper"), stroke=6)
        y += H * 0.115
    heroes = spec["heroes"]
    n = len(heroes)
    rows = 1 if n <= 6 else 2
    per = -(-n // rows)
    dia = int(min(W * 0.86 / per * 0.78, H * (0.175 if rows == 2 else 0.26)))
    fn = _font(FONT_TEXT, int(dia * 0.17))
    for i, hero in enumerate(heroes):
        r, c = divmod(i, per)
        k = min(per, n - r * per)  # heroes in this row, centred
        gap = (W * 0.86 - per * dia) / max(1, per - 1)
        x = W / 2 - (k * dia + (k - 1) * gap) / 2 + c * (dia + gap) + (dia * 0.25 if r % 2 else 0)
        yy = y + H * 0.02 + r * dia * 1.38 + (dia * 0.06 if c % 2 else 0)  # a loose, hand-placed grid
        _paste(im, head(_picture(hero["picture"], pics), dia, hero.get("prefer_x")), (x, yy))
        _text(d, (x + dia / 2, yy + dia * 1.1), hero["name"].upper(), fn, _hex("paper"))
    if spec.get("line"):
        _text(d, (W / 2, H * 0.93), spec["line"].upper(), _font(FONT_TEXT, int(H * 0.04)), _hex("uncertain_amber"))
    return im.convert("RGB")


def recap_card(spec: dict, pics: list[Path]) -> Image.Image:
    """A chapter recap: a title, then one row per hero (head, a sign, a few words), and a NEXT line at the foot."""
    W, H = SIZE
    im = background(spec.get("tone", "night")).convert("RGBA")
    d = ImageDraw.Draw(im)
    _text(d, (W / 2, H * 0.11), spec["title"].upper(), _font(FONT_TITLE, int(H * 0.085)), _hex("paper"), stroke=5)
    rows = spec["rows"]
    cols = 2 if len(rows) > 2 else 1
    per = -(-len(rows) // cols)
    top, bottom = H * 0.21, H * 0.82
    rh = (bottom - top) / per
    dia = int(min(rh * 0.82, H * 0.17))
    fn = _font(FONT_TEXT, int(dia * 0.3))
    colw = W * (0.44 if cols == 2 else 0.6)
    for i, row in enumerate(rows):
        c, r = divmod(i, per)
        x0 = W * (0.06 + c * 0.48) if cols == 2 else W * 0.2
        y0 = top + r * rh + (rh - dia) / 2
        if row.get("picture"):
            _paste(im, head(_picture(row["picture"], pics), dia, row.get("prefer_x")), (x0, y0))
        else:  # a thing, not a hero: its sign takes the head's place
            _paste(im, ICONS.sticker(row["icon"], dia), (x0, y0))
        if row.get("icon") and row.get("picture"):
            sticker = ICONS.sticker(row["icon"], int(dia * 0.62))
            _paste(im, sticker, (x0 + dia * 1.08, y0 + dia * 0.19))
        tx = x0 + dia * (1.8 if row.get("icon") and row.get("picture") else 1.15)
        txt = _wrap(row["text"].upper(), fn, int(colw - (tx - x0)))
        ty = y0 + dia / 2 - (len(txt) - 1) * dia * 0.18
        for ln in txt:
            _text(d, (tx, ty), ln, fn, _hex("paper"), anchor="lm")
            ty += dia * 0.36
    if spec.get("next"):
        fnext = _font(FONT_TITLE, int(H * 0.062))
        label = "NEXT: " + spec["next"].upper()
        tw = fnext.getlength(label)
        pad = H * 0.02
        y = H * 0.905
        d.rounded_rectangle([W / 2 - tw / 2 - 2 * pad, y - H * 0.045, W / 2 + tw / 2 + 2 * pad, y + H * 0.045], radius=int(pad),
                            fill=_hex("answer_coral"), outline=_hex("ink"), width=6)
        _text(d, (W / 2, y), label, fnext, _hex("ink"))
    return im.convert("RGB")


def row_points(spec: dict) -> list[list[float]]:
    """The centre of each recap row's head (shares of the card), so a ring beat can land on the row the narrator names."""
    W, H = SIZE
    rows = spec["rows"]
    cols = 2 if len(rows) > 2 else 1
    per = -(-len(rows) // cols)
    top, bottom = H * 0.21, H * 0.82
    rh = (bottom - top) / per
    dia = int(min(rh * 0.82, H * 0.17))
    out = []
    for i in range(len(rows)):
        c, r = divmod(i, per)
        x0 = W * (0.06 + c * 0.48) if cols == 2 else W * 0.2
        y0 = top + r * rh + (rh - dia) / 2
        out.append([round((x0 + dia / 2) / W, 3), round((y0 + dia / 2) / H, 3)])
    return out


def _picture(pid: str, pics: list[Path]) -> Path:
    for base in pics:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            p = base / f"{pid}{ext}"
            if p.exists():
                return p
    raise FileNotFoundError(f"picture {pid!r} not in {', '.join(map(str, pics))}")


def build(doc: dict, pics: list[Path], out: Path) -> list[Path]:
    """Every card in the script's ``cards`` block, written as ``<out>/<id>.png``."""
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for spec in doc.get("cards", []):
        im = title_card(spec, pics) if spec["kind"] == "title" else recap_card(spec, pics)
        p = out / f"{spec['id']}.png"
        im.save(p, optimize=True)
        made.append(p)
    return made


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.design.cards")
    ap.add_argument("script")
    ap.add_argument("pictures", nargs="+")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    doc = json.loads(Path(a.script).read_text(encoding="utf-8"))
    pics = [Path(p) for p in a.pictures]
    for p in build(doc, pics, Path(a.out) if a.out else pics[0]):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
