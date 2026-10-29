"""Collage of the P2S test (xworld_v2_p2s.py): one sheet per scene. Row 0 = the master and the model sheets; then one row per
cell (refs, cfg, LoRA weight) with shots 1..4. Questions per row: did the camera move? is it the same place? is it the same
face and clothes as the sheet?

    python xworld_v2_p2s_sheet.py <out dir of xworld_v2_p2s.py> ["title"]     writes <out>/p2s_<scene>.jpg
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 384, 216


def rows_of(todo, scene):
    """[(label, [picture names])] of one scene: the references row first, then the cells in drawing order."""
    mine = [j for j in todo if j["scene"] == scene]
    head = [j["name"] for j in mine if j["kind"] in ("master", "sheet")]
    rows, seen = [("master and model sheets", head)], {}
    for j in mine:
        if j["kind"] in ("master", "sheet"):
            continue
        key = (j["kind"], j["cfg"], j["weight"])
        seen.setdefault(key, []).append(j["name"])
    for (kind, cfg, weight), names in seen.items():
        rows.append((f"{kind}  cfg {cfg}  weight {weight}", names))
    return rows


def sheet(outd, scene, title=""):
    outd = Path(outd)
    todo = json.loads((outd / "jobs.json").read_text(encoding="utf-8"))
    rows = rows_of(todo, scene)
    cols = max(len(r[1]) for r in rows)
    img = Image.new("RGB", (cols * (W + 4), 24 + len(rows) * (H + 28)), "white")
    d = ImageDraw.Draw(img)
    d.text((4, 4), f"{title} {scene}: per row did the camera move? same place? same face and clothes as the sheet? anatomy correct? background correct? anyone duplicated?", fill="black")
    for i, (label, names) in enumerate(rows):
        y = 24 + i * (H + 28)
        d.text((4, y + 2), label, fill="black")
        for k, n in enumerate(names):
            p = outd / f"{n}.png"
            if p.exists():
                img.paste(Image.open(p).convert("RGB").resize((W, H)), (k * (W + 4), y + 18))
    path = outd / f"p2s_{scene}.jpg"
    img.save(path, quality=88)
    return path


def main(argv):
    outd, title = argv[0], (argv[1] if len(argv) > 1 else "")
    for scene in sorted({j["scene"] for j in json.loads((Path(outd) / "jobs.json").read_text(encoding="utf-8"))}):
        print(sheet(outd, scene, title))


if __name__ == "__main__":
    main(sys.argv[1:])
