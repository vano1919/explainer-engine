"""Contact sheets of one xworld_v2 round test: one sheet per scene, a row per seed and prompt form, shot 0 first in every
row, the round's VL score of each form written beside it. PIL only, so it runs on the pod and locally.

    python xworld_v2_sheet.py <scene dir> <round out dir> <label> [round]   ->  <round dir>/sheet_<scene>.jpg
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__:
    from .xworld_v2_scenes import FORMS, MODES, ROUND_TESTS, SEEDS, load
else:
    from xworld_v2_scenes import FORMS, MODES, ROUND_TESTS, SEEDS, load

W, H, PAD, TOP = 384, 216, 6, 34


def rows_of(scene, tests=None):
    """[(seed, form)] a scene's sheet shows: every seed x form, or what a training round drew (ROUND_TESTS)."""
    if tests is None:
        return [(seed, form) for seed in SEEDS for form in FORMS]
    return [(seed, f) for f, only, sds in tests if only is None or scene in only for seed in sds]


def build(scene_dir, outd, label, tests=None):
    from PIL import Image, ImageDraw
    outd = Path(outd)
    summ = json.loads((outd / "summary.json").read_text()) if (outd / "summary.json").exists() else {}
    made = []
    for sc in load(scene_dir):
        ids = [s["id"] for s in sc["shots"]]
        rows = rows_of(sc["name"], tests)
        sheet = Image.new("RGB", (PAD + len(ids) * (W + PAD), TOP + len(rows) * (H + 20 + PAD)), "white")
        d = ImageDraw.Draw(sheet)
        d.text((PAD, 8), f"{label} - {sc['name']} ({sc['world']}); per row: did the camera move? is it the same place?", fill="black")
        for r, (seed, form) in enumerate(rows):
            y = TOP + r * (H + 20 + PAD)
            score = summ.get(f"{form}/{sc['name']}")
            d.text((PAD, y), f"seed {seed} {form}" + (f"  VL {score:.2f}" if score is not None else ""), fill="black")
            for c, sid in enumerate(ids):
                p = outd / (f"{sc['name']}_{seed}_s0.png" if sid == "s0" else f"{sc['name']}_{seed}_{form}_{sid}.png")
                if p.exists():
                    with Image.open(p) as im:
                        sheet.paste(im.convert("RGB").resize((W, H)), (PAD + c * (W + PAD), y + 16))
        dst = outd / f"sheet_{sc['name']}.jpg"
        sheet.save(dst, quality=85)
        made.append(dst)
    return made


if __name__ == "__main__":
    print(build(*sys.argv[1:4], tests=MODES.get(sys.argv[4]) if len(sys.argv) > 4 else None))
