# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/publish/thumbnail.py`
# Target Module : explainer_engine/publish/thumbnail.py
# Target Classes/Symbols : def prompt(), def check_text(), def check_image(), def compose(), def run()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""``publish thumbnail``: the long video's thumbnail, painted by Gemini's premium image model behind the paid gate (D-57).

Without ``--generate`` it prints the prompt and the price and spends nothing. With ``--generate --approved-by '<who, where>'``
it paints ONE picture (Gemini 3 Pro Image at 2K, the ``premium`` tier of ``imagegen/routing.py``, from the cache when the same
request was paid before; ``--tier draft`` paints a cheap try first, written as ``thumbnail_draft.jpg`` beside the final file), sets the words with our own font (a model's lettering is not trusted), checks the TN rules that a
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


def run(episode: Path, *, generate: bool = False, approved_by: str = "", tier: str = TIER, client=None, log=print) -> int:
    episode = Path(episode)
    pub, _ = load_episode(episode)
    thumb = pub.get("thumbnail") or {}
    model, size = route(tier)
    refs = [episode / r for r in thumb.get("refs") or []]
    missing = [str(r) for r in refs if not r.exists()]
    text_problems = check_text(thumb.get("text") or "")
    try:
        p = prompt(thumb)
    except ValueError as exc:
        log(str(exc))
        return 1
    cost = estimate(model, size, 1, len(refs))
    log(f"model {model} at {size} (tier {tier}), {len(refs)} reference picture(s): {cost:.3f} USD for one picture "
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
    painted = client.generate("thumbnail_raw" if tier == TIER else f"thumbnail_raw_{tier}", p, model=model, size=size, aspect="16:9",
                              refs=[r.read_bytes() for r in refs])
    final = episode / (thumb.get("file") or "publish/thumbnail.jpg")
    if tier != TIER:  # a cheaper try sits beside the final file and never replaces it
        final = final.with_name(f"{final.stem}_{tier}{final.suffix}")
    compose(painted, thumb["text"], final, thumb.get("text_side", "left"))
    problems = check_image(final)
    for t in problems:
        log(f"FAIL   {t}")
    logp = out_dir / "thumbnail_log.json"
    rows = json.loads(logp.read_text(encoding="utf-8")) if logp.exists() else []
    rows.append({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tier": tier, "model": model, "size": size,
                 "usd_estimate": cost, "approved_by": approved_by, "file": str(final.relative_to(episode)), "prompt": p})
    write_json_atomic(logp, rows)
    log(f"thumbnail: {final} (look at it before staging; TN-10 human checks in docs/THUMBNAIL_RULES.md)")
    return 1 if problems else 0
