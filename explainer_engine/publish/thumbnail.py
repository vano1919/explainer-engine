"""``publish thumbnail``: the long video's thumbnail, painted by Gemini's premium image model behind the paid gate (D-56).

Without ``--generate`` it prints the prompt and the price and spends nothing. With ``--generate --approved-by '<who, where>'``
it paints ONE picture (Gemini 3 Pro Image at 2K, the ``premium`` tier of ``imagegen/routing.py``, from the cache when the same
request was paid before), sets the words with our own font (a model's lettering is not trusted), checks the TN rules that a
machine can check (docs/THUMBNAIL_RULES.md) and writes ``<episode>/publish/thumbnail.jpg`` (1280x720, under 2 MB so
every upload path takes it). The creator's OK is recorded in ``publish/thumbnail_log.json``.

publish.json:
    "thumbnail": {"file": "publish/thumbnail.jpg", "text": "WHO FALLS FIRST?", "concept": "...", "refs": ["pictures/p_x.png"],
                  "text_side": "left"}
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from explainer_engine.core.store import write_json_atomic
from explainer_engine.design import palette
from explainer_engine.imagegen.gemini import estimate
from explainer_engine.imagegen.routing import route
from explainer_engine.publish.plan import load_episode

TIER = "premium"
SIZE = (1280, 720)
MAX_BYTES = 2_000_000  # the mobile upload limit (Help 72431); desktop and the API take 50 MB
MAX_WORDS = 4          # TN-04
FONT = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Bangers-Regular.ttf"
STYLE = ("A YouTube thumbnail in our channel's hand-drawn 2D cartoon style, bold clean ink outlines, flat saturated colour, "
         "strong light and dark contrast, one clear focal subject large in frame, faces big with a readable emotion. ")
RULES = ("Leave the {side} third of the picture as calm dark empty background for a short headline added later. "
         "Keep the lower-right corner free of important detail. No text, no letters, no logos, no watermarks, no "
         "brand marks, no real photographs, no blood, no gore, no weapons pointed at the viewer.")


def prompt(thumb: dict) -> str:
    concept = (thumb.get("concept") or "").strip()
    if not concept:
        raise ValueError("publish.json thumbnail.concept is empty: describe the one promise the picture makes (TN-01)")
    side = "left" if thumb.get("text_side", "left") == "left" else "right"
    return STYLE + concept.rstrip(".") + ". " + RULES.format(side=side)


def check_text(text: str) -> list[str]:
    words = text.split()
    out = []
    if not words:
        out.append("TN-04: no headline; a thumbnail carries a few words that add to the title")
    if len(words) > MAX_WORDS:
        out.append(f"TN-04: {len(words)} words; at most {MAX_WORDS}")
    return out


def check_image(path: Path) -> list[str]:
    from PIL import Image

    out = []
    with Image.open(path) as im:
        w, h = im.size
    if (w, h) != SIZE:
        out.append(f"TN-09: {w}x{h}; the thumbnail is {SIZE[0]}x{SIZE[1]}")
    if Path(path).stat().st_size > MAX_BYTES:
        out.append(f"TN-09: {Path(path).stat().st_size} bytes; at most {MAX_BYTES}")
    return out


def compose(picture: Path, text: str, out: Path, side: str = "left") -> Path:
    """The painted picture cropped to 16:9 at 1280x720 with the headline set in the channel font, ink outline, upper area."""
    from PIL import Image, ImageDraw, ImageFont

    with Image.open(picture) as im:
        im = im.convert("RGB")
        w, h = im.size
        target = SIZE[0] / SIZE[1]
        if w / h > target:
            nw = int(h * target)
            im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = int(w / target)
            im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        im = im.resize(SIZE, Image.LANCZOS)
    draw = ImageDraw.Draw(im)
    tokens = palette.load()["tokens"]  # the headline: paper letters with an ink outline (the paper-on-night text pair)
    fill, stroke = tokens["paper"]["hex"], tokens["ink"]["hex"]
    words = text.upper().split()
    lines = [" ".join(words[i:i + 2]) for i in range(0, len(words), 2)]
    box_w = int(SIZE[0] * 0.42)
    size = 150
    font = ImageFont.truetype(str(FONT), size)
    while size > 40 and max(draw.textlength(l, font=font) for l in lines) > box_w:
        size -= 6
        font = ImageFont.truetype(str(FONT), size)
    x0 = int(SIZE[0] * 0.06) if side == "left" else SIZE[0] - int(SIZE[0] * 0.06) - box_w
    y = int(SIZE[1] * 0.08)
    for line in lines:
        draw.text((x0, y), line, font=font, fill=fill, stroke_width=max(4, size // 14), stroke_fill=stroke)
        y += int(size * 1.02)
    out.parent.mkdir(parents=True, exist_ok=True)
    quality = 92
    while True:
        im.save(out, "JPEG", quality=quality, optimize=True)
        if out.stat().st_size <= MAX_BYTES or quality <= 60:
            return out
        quality -= 8


def run(episode: Path, *, generate: bool = False, approved_by: str = "", client=None, log=print) -> int:
    episode = Path(episode)
    pub, _ = load_episode(episode)
    thumb = pub.get("thumbnail") or {}
    model, size = route(TIER)
    refs = [episode / r for r in thumb.get("refs") or []]
    missing = [str(r) for r in refs if not r.exists()]
    text_problems = check_text(thumb.get("text") or "")
    try:
        p = prompt(thumb)
    except ValueError as exc:
        log(str(exc))
        return 1
    cost = estimate(model, size, 1, len(refs))
    log(f"model {model} at {size} (tier {TIER}), {len(refs)} reference picture(s): {cost:.3f} USD for one picture "
        "(free when the same request is in the cache)")
    log(f"prompt: {p}")
    log(f"headline: {thumb.get('text')!r}")
    for m in missing:
        log(f"FAIL   reference not found: {m}")
    for t in text_problems:
        log(f"FAIL   {t}")
    if not generate:
        log("estimate only: nothing paid. Add --generate --approved-by '<who said OK, where>' after the creator's OK.")
        return 1 if missing or text_problems else 0
    if missing or text_problems:
        return 1
    if not approved_by.strip():
        log("refusing: --approved-by records the creator's OK for this paid picture")
        return 1
    out_dir = episode / "publish"
    if client is None:
        from explainer_engine.imagegen.gemini import GeminiClient
        client = GeminiClient(out_dir / "thumbnail_gemini", cap_usd=max(1.0, cost * 2))
    painted = client.generate("thumbnail_raw", p, model=model, size=size, aspect="16:9",
                              refs=[r.read_bytes() for r in refs])
    final = episode / (thumb.get("file") or "publish/thumbnail.jpg")
    compose(painted, thumb["text"], final, thumb.get("text_side", "left"))
    problems = check_image(final)
    for t in problems:
        log(f"FAIL   {t}")
    logp = out_dir / "thumbnail_log.json"
    rows = json.loads(logp.read_text(encoding="utf-8")) if logp.exists() else []
    rows.append({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": model, "size": size,
                 "usd_estimate": cost, "approved_by": approved_by, "file": str(final.relative_to(episode)), "prompt": p})
    write_json_atomic(logp, rows)
    log(f"thumbnail: {final} (look at it before staging; TN-10 human checks in docs/THUMBNAIL_RULES.md)")
    return 1 if problems else 0
