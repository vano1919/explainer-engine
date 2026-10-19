"""One variant collage, approved, before a hero or a world is painted (PV-47, OR-16; creator 2026-10-19). PIL for the sheet.

The creator: "generate the different versions of the characters and of the general setting as ONE big picture; I approve the
environment, the colours, the character, the style of the buildings; do not spend many pictures on it, one collage is enough."

So before a hero (``cast.<id>``) or the episode's world (``look.environment``) is painted for the first time, ONE picture
shows 4-6 variants side by side (``collage_prompt`` asks a provider for it; ``build_sheet`` lays out pictures that already exist,
free). The creator picks a tile; the record names the collage, the tile, the library picture that becomes the reference, who
approved it and when. Every hero drawn in a painted picture (library ``heroes`` of a ``gemini``/``pod_ref`` picture) or with a
face sheet, and the world of any painted picture, needs that record: missing is a FAIL on ``/2`` (paint refuses), a REVIEW on
``/1``. The chosen picture is the reference every later picture and face sheet is painted from (PV-26, VB-09).
"""

from __future__ import annotations

from pathlib import Path

LEGACY = "production_script/1"
PAINTED = ("gemini", "pod_ref")
FIELDS = ("collage", "tile", "picture", "approved_by", "approved_at")
MIN_TILES, MAX_TILES = 4, 6


def collage_prompt(subject: str, variants: list[str]) -> str:
    """One picture with 4-6 labelled variants of a hero or a world (the exploration costs one picture, not six)."""
    if not MIN_TILES <= len(variants) <= MAX_TILES:
        raise ValueError(f"a collage shows {MIN_TILES}-{MAX_TILES} variants, got {len(variants)}")
    tiles = "; ".join(f"tile {i + 1}: {v}" for i, v in enumerate(variants))
    return (f"A design sheet: one picture split into a clean grid of {len(variants)} equal tiles, each a different version "
            f"of {subject}, same framing in every tile so they compare at a glance, a small number in each tile's corner, "
            f"no other text. {tiles}.")


def build_sheet(pictures: list[Path], labels: list[str], out: Path, *, tile=(960, 540), cols: int = 3) -> Path:
    """A free collage of pictures that already exist (reuse before paying)."""
    from PIL import Image, ImageDraw

    w, h = tile
    rows = (len(pictures) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 40)), (15, 15, 15))
    draw = ImageDraw.Draw(sheet)
    for i, (p, lab) in enumerate(zip(pictures, labels)):
        x, y = (i % cols) * w, (i // cols) * (h + 40)
        sheet.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y + 40))
        draw.text((x + 10, y + 10), f"{i + 1} {lab}", fill=(255, 230, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    return out


def needs(doc: dict) -> tuple[set[str], bool]:
    """(heroes that are painted or get a face sheet, whether any picture is painted at all)."""
    default = (doc.get("look") or {}).get("default_engine")
    pics = list(doc.get("library", {}).values())
    for seg in doc.get("segments", []):  # pictures defined inline on a shot
        pics += [s["picture"] for s in seg.get("shots", []) if isinstance(s.get("picture"), dict)]
    heroes, painted = set(), False
    for pic in pics:
        if (pic.get("engine") or default) in PAINTED and not pic.get("file"):
            painted = True
            heroes.update(pic.get("heroes", []))
    for who, c in doc.get("cast", {}).items():
        if c.get("face_sheet"):
            heroes.add(who)
    return heroes, painted


def check(doc: dict, base: Path | None = None) -> list[dict]:
    sev = "REVIEW" if doc.get("schema") == LEGACY else "FAIL"
    out = []
    lib = doc.get("library", {})

    def f(where, detail):
        out.append({"rule": "PV-47", "severity": sev, "where": where, "detail": detail})

    def one(where, rec, what):
        if not rec:
            f(where, f"{what} is painted but has no approved variant collage: paint ONE collage of {MIN_TILES}-{MAX_TILES} "
                     "variants, let the creator pick a tile, record it (OR-16)")
            return
        missing = [k for k in FIELDS if rec.get(k) in (None, "")]
        if missing:
            f(where, f"the reference record lacks {', '.join(missing)}")
        if rec.get("picture") and rec["picture"] not in lib:
            f(where, f"reference picture {rec['picture']!r} is not in the library")
        if base is not None and rec.get("collage") and not (base / rec["collage"]).exists():
            f(where, f"collage {rec['collage']} not found next to the script")

    heroes, painted = needs(doc)
    for who in sorted(heroes):
        one(who, doc.get("cast", {}).get(who, {}).get("reference"), f"hero {who}")
    if painted:
        one("look.environment", (doc.get("look") or {}).get("environment"), "the episode's world")
    return out
