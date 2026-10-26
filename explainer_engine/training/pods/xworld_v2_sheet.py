"""Contact sheets of one xworld_v2 round test: one sheet per scene, a row per prompt form (P1, P2, P3), shot 0 first in every
row, the round's VL score of each form written beside it. PIL only, so it runs on the pod and locally.

    python xworld_v2_sheet.py <scene dir> <round out dir> <label>   ->  <round dir>/sheet_<scene>.jpg
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__:
    from .xworld_v2_scenes import FORMS, load
else:
    from xworld_v2_scenes import FORMS, load

W, H, PAD, TOP = 384, 216, 6, 34


def build(scene_dir, outd, label):
    from PIL import Image, ImageDraw
    outd = Path(outd)
    summ = json.loads((outd / "summary.json").read_text()) if (outd / "summary.json").exists() else {}
    made = []
    for sc in load(scene_dir):
        ids = [s["id"] for s in sc["shots"]]
        sheet = Image.new("RGB", (PAD + len(ids) * (W + PAD), TOP + len(FORMS) * (H + 20 + PAD)), "white")
        d = ImageDraw.Draw(sheet)
        d.text((PAD, 8), f"{label} - {sc['name']} ({sc['world']})", fill="black")
        for r, form in enumerate(FORMS):
            y = TOP + r * (H + 20 + PAD)
            score = summ.get(f"{form}/{sc['name']}")
            d.text((PAD, y), f"{form}" + (f"  VL {score:.2f}" if score is not None else ""), fill="black")
            for c, sid in enumerate(ids):
                p = outd / (f"{sc['name']}_s0.png" if sid == "s0" else f"{sc['name']}_{form}_{sid}.png")
                if p.exists():
                    with Image.open(p) as im:
                        sheet.paste(im.convert("RGB").resize((W, H)), (PAD + c * (W + PAD), y + 16))
        dst = outd / f"sheet_{sc['name']}.jpg"
        sheet.save(dst, quality=85)
        made.append(dst)
    return made


if __name__ == "__main__":
    print(build(*sys.argv[1:4]))
